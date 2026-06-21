import pytest

from app.bot import adaptive_bot_move, random_bot_move
from app.memory import MIN_HISTORY_FOR_ADAPTIVE, GameMemory
from app.rules import MOVES


class TestGameMemoryCounts:
    def test_initial_counts_are_zero(self):
        mem = GameMemory()
        assert mem.total_rounds == 0
        assert all(c == 0 for c in mem.player_move_counts.values())
        assert all(c == 0 for c in mem.bot_move_counts.values())

    def test_record_round_increments_counts(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", "player")
        assert mem.total_rounds == 1
        assert mem.player_move_counts["rock"] == 1
        assert mem.bot_move_counts["scissors"] == 1

    def test_multiple_rounds_increment_correctly(self):
        mem = GameMemory()
        rounds = [("rock", "scissors", "player"),
                  ("paper", "rock", "player"),
                  ("scissors", "paper", "player")]
        for p, b, w in rounds:
            mem.record_round(p, b, w)
        assert mem.total_rounds == 3
        assert mem.player_move_counts["rock"] == 1
        assert mem.player_move_counts["paper"] == 1
        assert mem.player_move_counts["scissors"] == 1

    def test_player_wins_increment_streak(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", "player")
        assert mem.player_streak == 1
        mem.record_round("rock", "scissors", "player")
        assert mem.player_streak == 2

    def test_player_loss_resets_streak(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", "player")
        mem.record_round("rock", "paper", "bot")
        assert mem.player_streak == 0

    def test_draw_resets_streak(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", "player")
        mem.record_round("rock", "rock", "draw")
        assert mem.player_streak == 0

    def test_last_10_rounds_limited(self):
        mem = GameMemory()
        for i in range(15):
            mem.record_round("rock", "scissors", "player")
        assert len(mem.last_10_rounds) == 10
        assert mem.total_rounds == 15


class TestPrediction:
    def test_no_history_returns_none(self):
        mem = GameMemory()
        assert mem.predict_player_next_move() is None

    def test_predicts_most_frequent_move(self):
        mem = GameMemory()
        for _ in range(5):
            mem.record_round("rock", "scissors", "player")
        for _ in range(2):
            mem.record_round("paper", "rock", "bot")
        assert mem.predict_player_next_move() == "rock"

    def test_prediction_after_single_move(self):
        mem = GameMemory()
        mem.record_round("paper", "rock", "bot")
        assert mem.predict_player_next_move() == "paper"


class TestAdaptiveMove:
    def test_no_history_returns_none(self):
        mem = GameMemory()
        assert mem.get_adaptive_move() is None

    def test_below_min_history_returns_none(self):
        mem = GameMemory()
        for _ in range(MIN_HISTORY_FOR_ADAPTIVE - 1):
            mem.record_round("rock", "scissors", "player")
        assert mem.get_adaptive_move() is None

    def test_at_min_history_returns_move(self):
        mem = GameMemory()
        for _ in range(MIN_HISTORY_FOR_ADAPTIVE):
            mem.record_round("rock", "scissors", "player")
        move = mem.get_adaptive_move()
        assert move in MOVES

    def test_counters_predicted_move(self):
        mem = GameMemory()
        for _ in range(MIN_HISTORY_FOR_ADAPTIVE):
            mem.record_round("rock", "scissors", "player")
        assert mem.get_adaptive_move() == "paper"

    def test_adaptive_bot_falls_back_to_random_when_empty(self, monkeypatch):
        mem = GameMemory()
        called_random = False

        def mock_random():
            nonlocal called_random
            called_random = True
            return "rock"

        monkeypatch.setattr("app.bot.random_bot_move", mock_random)
        move = adaptive_bot_move(mem)
        assert called_random is True
        assert move in MOVES

    def test_adaptive_bot_uses_prediction_when_enough_history(self):
        mem = GameMemory()
        for _ in range(MIN_HISTORY_FOR_ADAPTIVE):
            mem.record_round("rock", "scissors", "player")
        move = adaptive_bot_move(mem)
        assert move == "paper"
