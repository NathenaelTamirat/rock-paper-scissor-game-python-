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
                cur = self.conn.execute(
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
