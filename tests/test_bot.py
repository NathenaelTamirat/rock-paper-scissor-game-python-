import pytest

from app.bot import random_bot_move
from app.main import play_round
from app.rules import MOVES


class TestRandomBotMove:
    def test_returns_valid_move(self):
        for _ in range(100):
            move = random_bot_move()
            assert move in MOVES, f"{move} is not a valid move"

    def test_can_return_each_move(self):
        seen = set()
        for _ in range(1000):
            seen.add(random_bot_move())
        assert seen == set(MOVES), "Bot should eventually produce all moves"


class TestPlayRound:
    REQUIRED_KEYS = {"player_move", "bot_move", "winner"}

    def test_valid_move_returns_all_keys(self):
        for move in MOVES:
            result = play_round(move)
            for key in self.REQUIRED_KEYS:
                assert key in result, f"Missing key: {key}"

    def test_valid_move_returns_correct_player_move(self):
        for move in MOVES:
            result = play_round(move)
            assert result["player_move"] == move

    def test_valid_move_returns_valid_bot_move(self):
        for move in MOVES:
            result = play_round(move)
            assert result["bot_move"] in MOVES

    def test_valid_move_returns_valid_winner(self):
        for move in MOVES:
            result = play_round(move)
            assert result["winner"] in ("player", "bot", "draw")

    def test_invalid_move_returns_error(self):
        result = play_round("banana")
        assert "error" in result

    def test_empty_string_returns_error(self):
        result = play_round("")
        assert "error" in result

    def test_whitespace_string_returns_error(self):
        result = play_round("   ")
        assert "error" in result

    def test_uppercase_is_valid(self):
        for move in MOVES:
            upper = move.upper()
            result = play_round(upper)
            assert "error" not in result

    def test_mixed_case_is_valid(self):
        result = play_round("Rock")
        assert "error" not in result
