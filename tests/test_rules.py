import pytest

from app.rules import MOVES, WINNER_BOT, WINNER_DRAW, WINNER_PLAYER, get_winner, validate_move


class TestValidateMove:
    def test_valid_moves(self):
        for move in MOVES:
            assert validate_move(move) is True, f"{move} should be valid"

    def test_invalid_strings(self):
        assert validate_move("banana") is False
        assert validate_move("") is False
        assert validate_move("ROCK") is False
        assert validate_move("rock ") is False

    def test_non_string_inputs(self):
        assert validate_move(None) is False
        assert validate_move(123) is False
        assert validate_move(0) is False
        assert validate_move([]) is False


class TestGetWinner:
    def test_rock_vs_rock(self):
        assert get_winner("rock", "rock") == WINNER_DRAW

    def test_rock_vs_paper(self):
        assert get_winner("rock", "paper") == WINNER_BOT

    def test_rock_vs_scissors(self):
        assert get_winner("rock", "scissors") == WINNER_PLAYER

    def test_paper_vs_rock(self):
        assert get_winner("paper", "rock") == WINNER_PLAYER

    def test_paper_vs_paper(self):
        assert get_winner("paper", "paper") == WINNER_DRAW

    def test_paper_vs_scissors(self):
        assert get_winner("paper", "scissors") == WINNER_BOT

    def test_scissors_vs_rock(self):
        assert get_winner("scissors", "rock") == WINNER_BOT

    def test_scissors_vs_paper(self):
        assert get_winner("scissors", "paper") == WINNER_PLAYER

    def test_scissors_vs_scissors(self):
        assert get_winner("scissors", "scissors") == WINNER_DRAW
