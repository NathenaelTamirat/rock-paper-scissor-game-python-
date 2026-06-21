import os
import tempfile

from fastapi.testclient import TestClient

os.environ["RPS_DB_PATH"] = tempfile.mktemp(suffix=".db")

from app.main import app, memory, db

client = TestClient(app)


class TestHealth:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPlay:
    def setup_method(self):
        memory.reset()

    def test_valid_move_returns_play_response(self):
        response = client.post("/play", json={"player_move": "rock"})
        assert response.status_code == 200
        data = response.json()
        assert "player_move" in data
        assert "bot_move" in data
        assert "winner" in data
        assert "score" in data
        assert data["player_move"] == "rock"
        assert data["bot_move"] in ("rock", "paper", "scissors")
        assert data["winner"] in ("player", "bot", "draw")

    def test_invalid_move_returns_400(self):
        response = client.post("/play", json={"player_move": "banana"})
        assert response.status_code == 400

    def test_empty_move_returns_400(self):
        response = client.post("/play", json={"player_move": ""})
        assert response.status_code == 400

    def test_uppercase_move_accepted(self):
        response = client.post("/play", json={"player_move": "ROCK"})
        assert response.status_code == 200
        assert response.json()["player_move"] == "rock"

    def test_score_tracks_wins_and_losses(self):
        memory.reset()
        for _ in range(5):
            client.post("/play", json={"player_move": "rock"})
        data = client.post("/play", json={"player_move": "rock"}).json()
        score = data["score"]
        assert score["wins"] + score["losses"] + score["draws"] == 6


class TestHistory:
    def setup_method(self):
        memory.reset()

    def test_history_empty_initially(self):
        response = client.get("/history")
        assert response.status_code == 200
        data = response.json()
        assert data["all_rounds"] == []
        assert data["latest_10"] == []
        assert data["stats"]["total_rounds"] == 0

    def test_history_after_play(self):
        client.post("/play", json={"player_move": "rock"})
        response = client.get("/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["all_rounds"]) == 1
        assert len(data["latest_10"]) == 1
        assert data["stats"]["total_rounds"] == 1

    def test_history_limited_to_10_latest(self):
        for _ in range(15):
            client.post("/play", json={"player_move": "rock"})
        response = client.get("/history")
        data = response.json()
        assert len(data["all_rounds"]) == 15
        assert len(data["latest_10"]) == 10


class TestReset:
    def setup_method(self):
        memory.reset()

    def test_reset_clears_memory(self):
        client.post("/play", json={"player_move": "rock"})
        assert memory.total_rounds == 1
        response = client.post("/reset")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert memory.total_rounds == 0


class TestAuth:
    USERNAME = "testuser"
    PASSWORD = "secret123"

    def setup_method(self):
        # Remove test user if exists
        existing = db.get_user_by_username(self.USERNAME)
        if existing:
            db.conn.execute("DELETE FROM sessions WHERE user_id = ?",
                            (existing["id"],))
            db.conn.execute("DELETE FROM rounds WHERE user_id = ?",
                            (existing["id"],))
            db.conn.execute("DELETE FROM stats WHERE user_id = ?",
                            (existing["id"],))
            db.conn.execute("DELETE FROM users WHERE id = ?",
                            (existing["id"],))
            db.conn.commit()

    def _register(self):
        return client.post("/register", json={
            "username": self.USERNAME,
            "password": self.PASSWORD,
        })

    def _login(self):
        return client.post("/login", json={
            "username": self.USERNAME,
            "password": self.PASSWORD,
        })

    def test_register_creates_user(self):
        response = self._register()
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == self.USERNAME
        assert "user_id" in data

    def test_duplicate_username_returns_409(self):
        self._register()
        response = self._register()
        assert response.status_code == 409
        assert "Username already taken" in response.text

    def test_login_returns_token(self):
        self._register()
        response = self._login()
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] > 0
        assert len(data["token"]) > 0

    def test_login_wrong_password_returns_401(self):
        self._register()
        response = client.post("/login", json={
            "username": self.USERNAME,
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user_returns_401(self):
        response = client.post("/login", json={
            "username": "nobody",
            "password": "password",
        })
        assert response.status_code == 401

    def test_profile_returns_user_data(self):
        reg = self._register()
        user_id = reg.json()["user_id"]

        # Play a round with auth
        login = self._login()
        token = login.json()["token"]
        client.post("/play", json={"player_move": "rock"},
                     headers={"Authorization": f"Bearer {token}"})

        response = client.get(f"/profile/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == self.USERNAME
        assert data["user_id"] == user_id
        assert "created_at" in data
        assert "stats" in data
        assert "recent_rounds" in data
        assert len(data["recent_rounds"]) == 1

    def test_profile_not_found_returns_404(self):
        response = client.get("/profile/999999")
        assert response.status_code == 404

    def test_play_with_auth_saves_to_db(self):
        self._register()
        login = self._login()
        token = login.json()["token"]

        for _ in range(3):
            client.post("/play", json={"player_move": "rock"},
                         headers={"Authorization": f"Bearer {token}"})

        user_id = login.json()["user_id"]
        rounds = db.get_user_rounds(user_id)
        assert len(rounds) == 3

    def test_play_with_invalid_token_ignored(self):
        self._register()
        response = client.post("/play", json={"player_move": "rock"},
                                headers={"Authorization": "Bearer invalidtoken"})
        assert response.status_code == 200


class TestLeaderboard:
    def setup_method(self):
        for uid in [u["id"] for u in db.conn.execute(
                "SELECT id FROM users").fetchall()]:
            db.conn.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))
            db.conn.execute("DELETE FROM rounds WHERE user_id = ?", (uid,))
            db.conn.execute("DELETE FROM stats WHERE user_id = ?", (uid,))
            db.conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        db.conn.commit()

    def _make_user(self, username, wins=0, losses=0, draws=0, streak=0):
        uid = db.create_user(username, "pass")
        if uid == -1:
            uid = db.get_user_by_username(username)["id"]
        db.conn.execute(
            "UPDATE stats SET wins=?, losses=?, draws=?, streak=? WHERE user_id=?",
            (wins, losses, draws, streak, uid),
        )
        db.conn.commit()
        return uid

    def test_empty_leaderboard(self):
        response = client.get("/leaderboard")
        assert response.status_code == 200
        assert response.json()["leaderboard"] == []

    def test_leaderboard_ordering_by_wins(self):
        self._make_user("alice", wins=10, losses=2)
        self._make_user("bob", wins=5, losses=1)
        response = client.get("/leaderboard")
        entries = response.json()["leaderboard"]
        assert entries[0]["username"] == "alice"
        assert entries[1]["username"] == "bob"

    def test_leaderboard_tie_broken_by_win_rate(self):
        self._make_user("alice", wins=10, losses=10)  # 50%
        self._make_user("bob", wins=10, losses=0)     # 100%
        response = client.get("/leaderboard")
        entries = response.json()["leaderboard"]
        assert entries[0]["username"] == "bob"
        assert entries[1]["username"] == "alice"

    def test_leaderboard_tie_broken_by_streak(self):
        self._make_user("alice", wins=10, losses=0, streak=3)
        self._make_user("bob", wins=10, losses=0, streak=7)
        response = client.get("/leaderboard")
        entries = response.json()["leaderboard"]
        assert entries[0]["username"] == "bob"
        assert entries[1]["username"] == "alice"

    def test_leaderboard_respects_limit(self):
        for i in range(5):
            self._make_user(f"user{i}", wins=i)
        response = client.get("/leaderboard?limit=3")
        entries = response.json()["leaderboard"]
        assert len(entries) == 3

    def test_leaderboard_excludes_users_with_no_activity(self):
        self._make_user("active", wins=5)
        self._make_user("inactive", wins=0, losses=0, draws=0)
        response = client.get("/leaderboard")
        entries = response.json()["leaderboard"]
        usernames = [e["username"] for e in entries]
        assert "active" in usernames
        assert "inactive" in usernames  # still listed, 0 is valid
