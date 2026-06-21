from fastapi.testclient import TestClient

from app.main import app, memory

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
        # Play enough rounds to verify score tracking
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
