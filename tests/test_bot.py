import pytest

from app.bot import random_bot_move, persona_bot_move
from app.main import play_round
from app.memory import GameMemory
from app.rules import MOVES

_COUNTER = {
    "rock": "paper",
    "paper": "scissors",
    "scissors": "rock",
}


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

    def test_valid_with_all_personas(self):
        for persona in ("classic", "aggressive", "defensive", "random"):
            result = play_round("rock", persona=persona)
            assert "error" not in result
            assert result["bot_move"] in MOVES


class TestPersona:
    def test_persona_bot_move_returns_valid_move(self):
        mem = GameMemory()
        for persona in ("classic", "aggressive", "defensive", "random"):
            for _ in range(100):
                move = persona_bot_move(mem, persona)
                assert move in MOVES, f"{persona} produced invalid move: {move}"

    def test_unknown_persona_falls_back_to_classic(self):
        mem = GameMemory()
        for _ in range(100):
            move = persona_bot_move(mem, "nonexistent")
            assert move in MOVES

    def test_random_persona_ignores_memory(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", "player")
        mem.record_round("rock", "scissors", "player")
        mem.record_round("rock", "scissors", "player")
        seen = set()
        for _ in range(500):
            seen.add(persona_bot_move(mem, "random"))
        assert len(seen) == 3

    def test_aggressive_counters_player_move(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", "player")
        seen = set()
        for _ in range(200):
            move = persona_bot_move(mem, "aggressive")
            seen.add(move)
        assert "paper" in seen

    def test_defensive_blocks_last_player_move(self):
        mem = GameMemory()
        mem.record_round("rock", "paper", "bot")
        for _ in range(50):
            move = persona_bot_move(mem, "defensive")
            assert move == "paper"

    def test_defensive_repeats_winning_move(self):
        mem = GameMemory()
        mem.record_round("rock", "paper", "bot")
        for _ in range(50):
            assert persona_bot_move(mem, "defensive") == "paper"

    def test_classic_uses_adaptive_strategy(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", "player")
        mem.record_round("rock", "scissors", "player")
        mem.record_round("rock", "scissors", "player")
        for _ in range(200):
            move = persona_bot_move(mem, "classic")
            assert move in MOVES
