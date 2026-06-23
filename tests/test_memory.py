import pytest

from app.bot import adaptive_bot_move
from app.memory import MIN_HISTORY_FOR_ADAPTIVE, GameMemory
from app.rules import MOVES, WINNER_BOT, WINNER_DRAW, WINNER_PLAYER


class TestGameMemoryCounts:
    def test_initial_counts_are_zero(self):
        mem = GameMemory()
        assert mem.total_rounds == 0
        assert all(c == 0 for c in mem.player_move_counts.values())
        assert all(c == 0 for c in mem.bot_move_counts.values())

    def test_record_round_increments_counts(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        assert mem.total_rounds == 1
        assert mem.player_move_counts["rock"] == 1
        assert mem.bot_move_counts["scissors"] == 1

    def test_record_round_increments_draw_counts(self):
        mem = GameMemory()
        mem.record_round("rock", "rock", WINNER_DRAW)
        assert mem.total_rounds == 1
        assert mem.player_move_counts["rock"] == 1
        assert mem.bot_move_counts["rock"] == 1

    def test_record_round_increments_loss_counts(self):
        mem = GameMemory()
        mem.record_round("scissors", "rock", WINNER_BOT)
        assert mem.total_rounds == 1
        assert mem.player_move_counts["scissors"] == 1
        assert mem.bot_move_counts["rock"] == 1

    def test_record_round_invalid_player_move_raises(self):
        mem = GameMemory()
        with pytest.raises(ValueError, match="Invalid move"):
            mem.record_round("invalid", "rock", WINNER_PLAYER)

    def test_record_round_invalid_bot_move_raises(self):
        mem = GameMemory()
        with pytest.raises(ValueError, match="Invalid move"):
            mem.record_round("rock", "invalid", WINNER_PLAYER)

    def test_record_round_invalid_winner_raises(self):
        mem = GameMemory()
        with pytest.raises(ValueError, match="Invalid winner"):
            mem.record_round("rock", "scissors", "invalid")

    def test_multiple_rounds_increment_correctly(self):
        mem = GameMemory()
        rounds = [("rock", "scissors", WINNER_PLAYER),
                  ("paper", "rock", WINNER_PLAYER),
                  ("scissors", "paper", WINNER_PLAYER)]
        for p, b, w in rounds:
            mem.record_round(p, b, w)
        assert mem.total_rounds == 3
        assert mem.player_move_counts["rock"] == 1
        assert mem.player_move_counts["paper"] == 1
        assert mem.player_move_counts["scissors"] == 1

    def test_player_wins_increment_streak(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        assert mem.player_streak == 1
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        assert mem.player_streak == 2

    def test_player_loss_resets_streak(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("rock", "paper", WINNER_BOT)
        assert mem.player_streak == 0

    def test_draw_resets_streak(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("rock", "rock", WINNER_DRAW)
        assert mem.player_streak == 0

    def test_consecutive_losses_dont_affect_streak(self):
        mem = GameMemory()
        mem.record_round("scissors", "rock", WINNER_BOT)
        assert mem.player_streak == 0
        mem.record_round("paper", "scissors", WINNER_BOT)
        assert mem.player_streak == 0

    def test_last_10_rounds_limited(self):
        mem = GameMemory()
        for _ in range(15):
            mem.record_round("rock", "scissors", WINNER_PLAYER)
        assert len(mem.last_10_rounds) == 10
        assert mem.total_rounds == 15


class TestPrediction:
    def test_no_history_returns_none(self):
        mem = GameMemory()
        assert mem.predict_player_next_move() is None

    def test_predicts_most_frequent_move(self):
        mem = GameMemory()
        for _ in range(5):
            mem.record_round("rock", "scissors", WINNER_PLAYER)
        for _ in range(2):
            mem.record_round("paper", "rock", WINNER_BOT)
        assert mem.predict_player_next_move() == "rock"

    def test_prediction_after_single_move(self):
        mem = GameMemory()
        mem.record_round("paper", "rock", WINNER_BOT)
        assert mem.predict_player_next_move() == "paper"

    def test_tied_frequencies_returns_one_of_tied(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("paper", "rock", WINNER_BOT)
        result = mem.predict_player_next_move()
        assert result in ("rock", "paper")

    def test_all_moves_equal_frequency(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("paper", "rock", WINNER_BOT)
        mem.record_round("scissors", "paper", WINNER_BOT)
        result = mem.predict_player_next_move()
        assert result in MOVES

    def test_prediction_not_affected_by_outcome(self):
        mem = GameMemory()
        for _ in range(3):
            mem.record_round("scissors", "rock", WINNER_BOT)
        assert mem.predict_player_next_move() == "scissors"

    def test_prediction_after_reset_returns_none(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.reset()
        assert mem.predict_player_next_move() is None


class TestStats:
    def test_empty_stats_favorite_move_is_none(self):
        mem = GameMemory()
        stats = mem.get_stats()
        assert stats["favorite_move"] is None

    def test_empty_stats_win_rate_zero(self):
        mem = GameMemory()
        stats = mem.get_stats()
        assert stats["win_rate"] == 0.0
        assert stats["total_rounds"] == 0
        assert stats["streak"] == 0

    def test_stats_with_rounds(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("paper", "rock", WINNER_PLAYER)
        stats = mem.get_stats()
        assert stats["total_rounds"] == 2
        assert stats["wins"] == 2
        assert stats["losses"] == 0
        assert stats["draws"] == 0
        assert stats["win_rate"] == 1.0
        assert stats["favorite_move"] in MOVES
        assert stats["streak"] == 2

    def test_stats_with_mixed_outcomes(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("paper", "scissors", WINNER_BOT)
        mem.record_round("rock", "rock", WINNER_DRAW)
        stats = mem.get_stats()
        assert stats["wins"] == 1
        assert stats["losses"] == 1
        assert stats["draws"] == 1
        assert stats["win_rate"] == pytest.approx(1 / 3, rel=1e-3)
        assert stats["streak"] == 0

    def test_stats_after_reset(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.reset()
        stats = mem.get_stats()
        assert stats["favorite_move"] is None
        assert stats["total_rounds"] == 0
        assert stats["win_rate"] == 0.0


class TestAdaptiveMove:
    def test_no_history_returns_none(self):
        mem = GameMemory()
        assert mem.get_adaptive_move() is None

    def test_below_min_history_returns_none(self):
        mem = GameMemory()
        for _ in range(MIN_HISTORY_FOR_ADAPTIVE - 1):
            mem.record_round("rock", "scissors", WINNER_PLAYER)
        assert mem.get_adaptive_move() is None

    def test_at_min_history_returns_move(self):
        mem = GameMemory()
        for _ in range(MIN_HISTORY_FOR_ADAPTIVE):
            mem.record_round("rock", "scissors", WINNER_PLAYER)
        move = mem.get_adaptive_move()
        assert move in MOVES

    def test_counters_predicted_move(self):
        mem = GameMemory()
        for _ in range(MIN_HISTORY_FOR_ADAPTIVE):
            mem.record_round("rock", "scissors", WINNER_PLAYER)
        assert mem.get_adaptive_move() == "paper"

    def test_counters_scissors_with_rock(self):
        mem = GameMemory()
        for _ in range(MIN_HISTORY_FOR_ADAPTIVE):
            mem.record_round("scissors", "paper", WINNER_PLAYER)
        assert mem.get_adaptive_move() == "rock"

    def test_counters_paper_with_scissors(self):
        mem = GameMemory()
        for _ in range(MIN_HISTORY_FOR_ADAPTIVE):
            mem.record_round("paper", "rock", WINNER_PLAYER)
        assert mem.get_adaptive_move() == "scissors"

    def test_counters_after_clear_majority(self):
        mem = GameMemory()
        for _ in range(10):
            mem.record_round("rock", "scissors", WINNER_PLAYER)
        for _ in range(2):
            mem.record_round("paper", "rock", WINNER_BOT)
        assert mem.get_adaptive_move() == "paper"

    def test_get_adaptive_move_after_reset(self):
        mem = GameMemory()
        for _ in range(MIN_HISTORY_FOR_ADAPTIVE):
            mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.reset()
        assert mem.get_adaptive_move() is None

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
            mem.record_round("rock", "scissors", WINNER_PLAYER)
        move = adaptive_bot_move(mem)
        assert move == "paper"


class TestReset:
    def test_reset_clears_all_state(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("paper", "rock", WINNER_PLAYER)
        mem.reset()
        assert mem.total_rounds == 0
        assert all(c == 0 for c in mem.player_move_counts.values())
        assert all(c == 0 for c in mem.bot_move_counts.values())
        assert mem.wins == 0
        assert mem.losses == 0
        assert mem.draws == 0
        assert mem.player_streak == 0
        assert len(mem.last_10_rounds) == 0

    def test_reset_twice_is_idempotent(self):
        mem = GameMemory()
        mem.reset()
        mem.reset()
        assert mem.total_rounds == 0


class TestFullAdaptiveFlow:
    def test_record_then_predict_then_counter(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("rock", "paper", WINNER_BOT)
        mem.record_round("rock", "rock", WINNER_DRAW)
        predicted = mem.predict_player_next_move()
        assert predicted == "rock"
        counter = mem.get_adaptive_move()
        assert counter == "paper"

    def test_flow_different_move(self):
        mem = GameMemory()
        mem.record_round("paper", "rock", WINNER_PLAYER)
        mem.record_round("paper", "scissors", WINNER_BOT)
        mem.record_round("paper", "paper", WINNER_DRAW)
        predicted = mem.predict_player_next_move()
        assert predicted == "paper"
        counter = mem.get_adaptive_move()
        assert counter == "scissors"
