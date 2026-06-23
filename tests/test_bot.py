from app.bot import persona_bot_move, random_bot_move
from app.main import play_round
from app.memory import GameMemory
from app.rules import (
    COUNTER,
    MOVES,
    WINNER_BOT,
    WINNER_DRAW,
    WINNER_PLAYER,
)


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
            assert result["winner"] in (WINNER_PLAYER, WINNER_BOT, WINNER_DRAW)

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
                assert move in MOVES

    def test_unknown_persona_falls_back_to_classic(self):
        mem = GameMemory()
        for _ in range(100):
            move = persona_bot_move(mem, "nonexistent")
            assert move in MOVES

    def test_empty_string_persona_falls_back_to_classic(self):
        mem = GameMemory()
        for _ in range(100):
            move = persona_bot_move(mem, "")
            assert move in MOVES

    def test_random_persona_ignores_memory(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        seen = set()
        for _ in range(500):
            seen.add(persona_bot_move(mem, "random"))
        assert len(seen) == 3

    def test_aggressive_counters_player_move(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        seen = set()
        for _ in range(200):
            move = persona_bot_move(mem, "aggressive")
            seen.add(move)
        assert "paper" in seen

    def test_aggressive_with_no_history_returns_random(self):
        mem = GameMemory()
        seen = set()
        for _ in range(200):
            move = persona_bot_move(mem, "aggressive")
            seen.add(move)
        assert len(seen) == 3

    def test_defensive_counters_when_player_won(self):
        mem = GameMemory()
        mem.record_round("paper", "rock", WINNER_PLAYER)
        for _ in range(50):
            move = persona_bot_move(mem, "defensive")
            assert move == "scissors"

    def test_defensive_repeats_winning_move_when_bot_won(self):
        mem = GameMemory()
        mem.record_round("rock", "paper", WINNER_BOT)
        for _ in range(50):
            move = persona_bot_move(mem, "defensive")
            assert move == "paper"

    def test_defensive_falls_back_to_random_on_draw(self):
        mem = GameMemory()
        mem.record_round("rock", "rock", WINNER_DRAW)
        seen = set()
        for _ in range(200):
            move = persona_bot_move(mem, "defensive")
            seen.add(move)
        assert len(seen) == 3

    def test_defensive_with_no_history_returns_random(self):
        mem = GameMemory()
        seen = set()
        for _ in range(200):
            move = persona_bot_move(mem, "defensive")
            seen.add(move)
        assert len(seen) == 3

    def test_classic_uses_adaptive_strategy(self):
        mem = GameMemory()
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        mem.record_round("rock", "scissors", WINNER_PLAYER)
        for _ in range(200):
            move = persona_bot_move(mem, "classic")
            assert move in MOVES

    def test_classic_returns_counter_move_with_enough_history(self):
        mem = GameMemory()
        for _ in range(3):
            mem.record_round("rock", "scissors", WINNER_PLAYER)
        for _ in range(50):
            move = persona_bot_move(mem, "classic")
            assert move == "paper"

    def test_persona_bot_move_unknown_falls_back_to_classic(self):
        mem = GameMemory()
        for _ in range(100):
            move = persona_bot_move(mem, "alien")
            assert move in MOVES

    def test_aggressive_counters_each_possible_move(self):
        for player_move in MOVES:
            mem = GameMemory()
            mem.record_round(player_move, "scissors", WINNER_PLAYER)
            expected = COUNTER[player_move]
            for _ in range(30):
                move = persona_bot_move(mem, "aggressive")
                assert move == expected

    def test_persona_bot_move_raises_no_errors_with_all_personas(self):
        for persona in ("classic", "aggressive", "defensive", "random"):
            mem = GameMemory()
            for move in MOVES:
                mem.record_round(move, move, WINNER_DRAW)
                result = persona_bot_move(mem, persona)
                assert result in MOVES
