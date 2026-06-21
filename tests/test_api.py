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
