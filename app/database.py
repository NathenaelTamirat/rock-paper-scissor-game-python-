import hashlib
import os
import secrets
import sqlite3
import string
from typing import Optional

DB_PATH = os.environ.get("RPS_DB_PATH", "rps.db")


class Database:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_db()

    def _init_db(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                token TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                player_move TEXT NOT NULL,
                bot_move TEXT NOT NULL,
                winner TEXT NOT NULL,
                played_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_code TEXT UNIQUE NOT NULL,
                player_a_id INTEGER NOT NULL REFERENCES users(id),
                player_b_id INTEGER REFERENCES users(id),
                move_a TEXT,
                move_b TEXT,
                winner TEXT,
                status TEXT DEFAULT 'waiting',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS matchmaking_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                preferred_mode TEXT DEFAULT 'classic',
                enqueued_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                max_players INTEGER DEFAULT 4,
                status TEXT DEFAULT 'waiting',
                winner_id INTEGER REFERENCES users(id),
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tournament_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                seed INTEGER,
                UNIQUE(tournament_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS tournament_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id),
                round INTEGER NOT NULL,
                match_index INTEGER NOT NULL,
                player_a_id INTEGER REFERENCES users(id),
                player_b_id INTEGER REFERENCES users(id),
                score_a INTEGER DEFAULT 0,
                score_b INTEGER DEFAULT 0,
                winner_id INTEGER REFERENCES users(id),
                status TEXT DEFAULT 'pending'
            );
        """)
        self.conn.commit()
        # Migration: add streak column if missing on existing databases
        try:
            self.conn.execute("ALTER TABLE stats ADD COLUMN streak INTEGER DEFAULT 0")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

    # --- Password hashing (PBKDF2-HMAC-SHA256, built-in) ---

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, 600000,
        )
        return salt.hex() + ":" + key.hex()

    @staticmethod
    def _verify_password(password: str, stored: str) -> bool:
        salt_hex, key_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, 600000,
        )
        return secrets.compare_digest(key.hex(), key_hex)

    # --- Users ---

    def create_user(self, username: str, password: str) -> int:
        pw_hash = self._hash_password(password)
        try:
            cur = self.conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, pw_hash),
            )
            self.conn.commit()
            user_id = cur.lastrowid
            self.conn.execute(
                "INSERT INTO stats (user_id) VALUES (?)", (user_id,),
            )
            self.conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return -1

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_user_by_username(self, username: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def verify_login(self, username: str, password: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            return None
        if not self._verify_password(password, row["password_hash"]):
            return None
        return {"id": row["id"], "username": row["username"]}

    # --- Sessions ---

    def create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        self.conn.execute(
            "INSERT INTO sessions (user_id, token) VALUES (?, ?)",
            (user_id, token),
        )
        self.conn.commit()
        return token

    def delete_session(self, token: str) -> None:
        if token:
            self.conn.execute(
                "DELETE FROM sessions WHERE token = ?", (token,),
            )
            self.conn.commit()

    def get_session_user_id(self, token: str) -> Optional[int]:
        if not token:
            return None
        row = self.conn.execute(
            "SELECT user_id FROM sessions WHERE token = ?", (token,),
        ).fetchone()
        if row is None:
            return None
        return row["user_id"]

    # --- Rounds ---

    def record_round(
        self, user_id: int, player_move: str, bot_move: str, winner: str,
    ) -> None:
        self.conn.execute(
            "INSERT INTO rounds (user_id, player_move, bot_move, winner) "
            "VALUES (?, ?, ?, ?)",
            (user_id, player_move, bot_move, winner),
        )
        if winner == "player":
            self.conn.execute(
                "UPDATE stats SET wins = wins + 1, streak = streak + 1 "
                "WHERE user_id = ?", (user_id,),
            )
        elif winner == "bot":
            self.conn.execute(
                "UPDATE stats SET losses = losses + 1, streak = 0 "
                "WHERE user_id = ?", (user_id,),
            )
        else:
            self.conn.execute(
                "UPDATE stats SET draws = draws + 1, streak = 0 "
                "WHERE user_id = ?", (user_id,),
            )
        self.conn.commit()

    def get_user_rounds(self, user_id: int, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT player_move, bot_move, winner, played_at "
            "FROM rounds WHERE user_id = ? "
            "ORDER BY played_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Stats ---

    def get_user_stats(self, user_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT wins, losses, draws, streak FROM stats WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        stats = dict(row)
        total = stats["wins"] + stats["losses"] + stats["draws"]
        stats["total_rounds"] = total
        stats["win_rate"] = (
            round(stats["wins"] / total, 4) if total > 0 else 0.0
        )
        fav = self.conn.execute(
            "SELECT player_move, COUNT(*) AS cnt FROM rounds "
            "WHERE user_id = ? "
            "GROUP BY player_move ORDER BY cnt DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        stats["favorite_move"] = fav["player_move"] if fav else None
        return stats

    def get_leaderboard(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute("""
            SELECT u.id, u.username,
                   s.wins, s.losses, s.draws,
                   (s.wins + s.losses + s.draws) AS total_rounds,
                   CASE WHEN (s.wins + s.losses + s.draws) > 0
                        THEN ROUND(CAST(s.wins AS REAL) /
                             (s.wins + s.losses + s.draws), 4)
                        ELSE 0.0 END AS win_rate,
                   s.streak
            FROM users u
            JOIN stats s ON s.user_id = u.id
            ORDER BY s.wins DESC, win_rate DESC, s.streak DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    # --- Analytics ---

    def get_analytics_summary(self, user_id: int) -> dict:
        return self.get_user_stats(user_id) or {
            "total_rounds": 0, "wins": 0, "losses": 0, "draws": 0,
            "win_rate": 0.0, "favorite_move": None, "streak": 0,
        }

    def get_analytics_move_distribution(self, user_id: int) -> list[dict]:
        from app.rules import MOVES
        rows = self.conn.execute(
            "SELECT player_move, COUNT(*) AS count FROM rounds "
            "WHERE user_id = ? GROUP BY player_move ORDER BY count DESC",
            (user_id,),
        ).fetchall()
        result = {m: 0 for m in MOVES}
        for r in rows:
            result[r["player_move"]] = r["count"]
        return [{"move": m, "count": c} for m, c in result.items()]

    def get_analytics_timeline(
        self, user_id: int, days: int = 7,
    ) -> list[dict]:
        rows = self.conn.execute("""
            SELECT DATE(played_at) AS day,
                   COUNT(*) AS games,
                   SUM(CASE WHEN winner = 'player' THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN winner = 'bot' THEN 1 ELSE 0 END) AS losses,
                   SUM(CASE WHEN winner = 'draw' THEN 1 ELSE 0 END) AS draws
            FROM rounds
            WHERE user_id = ?
              AND played_at >= DATE('now', ?)
            GROUP BY DATE(played_at)
            ORDER BY day ASC
        """, (user_id, f"-{days} days")).fetchall()
        return [dict(r) for r in rows]

    # --- Rooms (Multiplayer) ---

    @staticmethod
    def _generate_room_code() -> str:
        return ''.join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(6)
        )

    def create_room(self, user_id: int) -> dict:
        for _ in range(10):
            code = self._generate_room_code()
            try:
                self.conn.execute(
                    "INSERT INTO rooms (room_code, player_a_id, status) "
                    "VALUES (?, ?, 'waiting')",
                    (code, user_id),
                )
                self.conn.commit()
                return self.get_room(code)
            except sqlite3.IntegrityError:
                continue
        raise RuntimeError("Failed to generate unique room code")

    def get_room(self, room_code: str) -> Optional[dict]:
        row = self.conn.execute("""
            SELECT r.id, r.room_code, r.player_a_id, r.player_b_id,
                   r.move_a, r.move_b, r.winner, r.status, r.created_at,
                   a.username AS player_a_username,
                   b.username AS player_b_username
            FROM rooms r
            JOIN users a ON a.id = r.player_a_id
            LEFT JOIN users b ON b.id = r.player_b_id
            WHERE r.room_code = ?
        """, (room_code,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def join_room(self, room_code: str, user_id: int) -> dict:
        room = self.get_room(room_code)
        if room is None:
            raise ValueError("Room not found")
        if room["status"] != "waiting":
            raise ValueError("Room is not accepting players")
        if room["player_a_id"] == user_id:
            raise ValueError("Cannot join your own room")
        self.conn.execute(
            "UPDATE rooms SET player_b_id = ?, status = 'playing' "
            "WHERE room_code = ?",
            (user_id, room_code),
        )
        self.conn.commit()
        return self.get_room(room_code)

    def submit_room_move(self, room_code: str, user_id: int, move: str) -> dict:
        room = self.get_room(room_code)
        if room is None:
            raise ValueError("Room not found")
        if room["status"] != "playing":
            raise ValueError("Game is not in progress")

        if room["player_a_id"] == user_id:
            if room["move_a"] is not None:
                raise ValueError("You already submitted your move")
            col = "move_a"
        elif room["player_b_id"] == user_id:
            if room["move_b"] is not None:
                raise ValueError("You already submitted your move")
            col = "move_b"
        else:
            raise ValueError("You are not a player in this room")

        self.conn.execute(
            f"UPDATE rooms SET {col} = ? WHERE room_code = ?",
            (move, room_code),
        )
        self.conn.commit()

        room = self.get_room(room_code)

        if room["move_a"] is not None and room["move_b"] is not None:
            from app.rules import get_winner
            raw = get_winner(room["move_a"], room["move_b"])
            if raw == "player":
                winner = "player_a"
            elif raw == "bot":
                winner = "player_b"
            else:
                winner = "draw"
            self.conn.execute(
                "UPDATE rooms SET winner = ?, status = 'complete' "
                "WHERE room_code = ?",
                (winner, room_code),
            )
            self.conn.commit()

        return self.get_room(room_code)

    # --- Matchmaking ---

    def join_queue(self, user_id: int, preferred_mode: str = "classic") -> dict:
        existing = self.conn.execute(
            "SELECT * FROM matchmaking_queue WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if existing is not None:
            return dict(existing)

        self.conn.execute(
            "INSERT INTO matchmaking_queue (user_id, preferred_mode) VALUES (?, ?)",
            (user_id, preferred_mode),
        )
        self.conn.commit()

        entry = self.conn.execute(
            "SELECT * FROM matchmaking_queue WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return dict(entry)

    def leave_queue(self, user_id: int) -> None:
        self.conn.execute(
            "DELETE FROM matchmaking_queue WHERE user_id = ?",
            (user_id,),
        )
        self.conn.commit()

    def get_queue_position(self, user_id: int) -> Optional[int]:
        all_entries = self.conn.execute(
            "SELECT id, user_id, enqueued_at FROM matchmaking_queue "
            "ORDER BY enqueued_at ASC"
        ).fetchall()
        for i, row in enumerate(all_entries):
            if row["user_id"] == user_id:
                return i + 1
        return None

    def is_user_in_queue(self, user_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM matchmaking_queue WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row is not None

    def get_user_active_room(self, user_id: int) -> Optional[dict]:
        row = self.conn.execute("""
            SELECT room_code FROM rooms
            WHERE (player_a_id = ? OR player_b_id = ?)
              AND status != 'complete'
            ORDER BY created_at DESC LIMIT 1
        """, (user_id, user_id)).fetchone()
        if row is None:
            return None
        return self.get_room(row["room_code"])

    def process_queue(self) -> Optional[str]:
        rows = self.conn.execute(
            "SELECT user_id FROM matchmaking_queue "
            "ORDER BY enqueued_at ASC LIMIT 2"
        ).fetchall()

        if len(rows) < 2:
            return None

        user_a_id = rows[0]["user_id"]
        user_b_id = rows[1]["user_id"]

        room = self.create_room(user_a_id)
        self.join_room(room["room_code"], user_b_id)

        self.conn.execute(
            "DELETE FROM matchmaking_queue WHERE user_id IN (?, ?)",
            (user_a_id, user_b_id),
        )
        self.conn.commit()

        return room["room_code"]

    # --- Tournaments ---

    @staticmethod
    def _generate_tournament_code() -> str:
        return ''.join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(6)
        )

    def create_tournament(self, name: str, user_id: int, max_players: int = 4) -> dict:
        for _ in range(10):
            code = self._generate_tournament_code()
            try:
                cur = self.conn.execute(
                    "INSERT INTO tournaments (code, name, max_players, status) "
                    "VALUES (?, ?, ?, 'waiting')",
                    (code, name, max_players),
                )
                tid = cur.lastrowid
                self.conn.execute(
                    "INSERT INTO tournament_players (tournament_id, user_id, seed) "
                    "VALUES (?, ?, 1)",
                    (tid, user_id),
                )
                self.conn.commit()
                return self.get_tournament(code)
            except sqlite3.IntegrityError:
                continue
        raise RuntimeError("Failed to generate unique tournament code")

    def list_open_tournaments(self) -> list[dict]:
        rows = self.conn.execute("""
            SELECT t.code, t.name, t.status, t.max_players,
                   (SELECT COUNT(*) FROM tournament_players tp
                    WHERE tp.tournament_id = t.id) AS player_count
            FROM tournaments t
            WHERE t.status = 'waiting'
            ORDER BY t.id DESC
            LIMIT 20
        """).fetchall()
        return [dict(r) for r in rows]

    def get_tournament(self, code: str) -> Optional[dict]:
        row = self.conn.execute("""
            SELECT t.*, u.username AS winner_username
            FROM tournaments t
            LEFT JOIN users u ON u.id = t.winner_id
            WHERE t.code = ?
        """, (code,)).fetchone()
        if row is None:
            return None
        t = dict(row)

        players = self.conn.execute("""
            SELECT tp.seed, tp.user_id, u.username
            FROM tournament_players tp
            JOIN users u ON u.id = tp.user_id
            WHERE tp.tournament_id = ?
            ORDER BY tp.seed ASC
        """, (t["id"],)).fetchall()
        t["players"] = [dict(p) for p in players]

        matches = self.conn.execute("""
            SELECT tm.round, tm.match_index,
                   tm.player_a_id, a.username AS player_a_username,
                   tm.player_b_id, b.username AS player_b_username,
                   tm.score_a, tm.score_b, tm.winner_id, tm.status,
                   w.username AS winner_username
            FROM tournament_matches tm
            LEFT JOIN users a ON a.id = tm.player_a_id
            LEFT JOIN users b ON b.id = tm.player_b_id
            LEFT JOIN users w ON w.id = tm.winner_id
            WHERE tm.tournament_id = ?
            ORDER BY tm.round ASC, tm.match_index ASC
        """, (t["id"],)).fetchall()
        t["matches"] = [dict(m) for m in matches]

        return t

    def join_tournament(self, code: str, user_id: int) -> dict:
        t = self.get_tournament(code)
        if t is None:
            raise ValueError("Tournament not found")
        if t["status"] != "waiting":
            raise ValueError("Tournament is not accepting players")

        existing = self.conn.execute(
            "SELECT 1 FROM tournament_players "
            "WHERE tournament_id = ? AND user_id = ?",
            (t["id"], user_id),
        ).fetchone()
        if existing is not None:
            return t

        count = self.conn.execute(
            "SELECT COUNT(*) AS cnt FROM tournament_players "
            "WHERE tournament_id = ?",
            (t["id"],),
        ).fetchone()["cnt"]
        if count >= t["max_players"]:
            raise ValueError("Tournament is full")

        next_seed = count + 1
        self.conn.execute(
            "INSERT INTO tournament_players (tournament_id, user_id, seed) "
            "VALUES (?, ?, ?)",
            (t["id"], user_id, next_seed),
        )
        self.conn.commit()
        return self.get_tournament(code)

    def run_tournament(self, code: str) -> dict:
        t = self.get_tournament(code)
        if t is None:
            raise ValueError("Tournament not found")
        if t["status"] != "waiting":
            raise ValueError("Tournament already started")

        players = t["players"]
        if len(players) < 4:
            raise ValueError(
                f"Need 4 players, got {len(players)}"
            )

        self.conn.execute(
            "UPDATE tournaments SET status = 'active' WHERE id = ?",
            (t["id"],),
        )
        self.conn.commit()

        from app.tournament import run_bracket
        matches = run_bracket(players)

        for m in matches:
            self.conn.execute(
                "INSERT INTO tournament_matches "
                "(tournament_id, round, match_index, player_a_id, player_b_id, "
                " score_a, score_b, winner_id, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'complete')",
                (t["id"], m["round"], m["match_index"],
                 m["player_a_id"], m["player_b_id"],
                 m["score_a"], m["score_b"], m["winner_id"]),
            )

        champion_id = matches[-1]["winner_id"]
        self.conn.execute(
            "UPDATE tournaments SET status = 'complete', winner_id = ? WHERE id = ?",
            (champion_id, t["id"]),
        )
        self.conn.commit()

        return self.get_tournament(code)
