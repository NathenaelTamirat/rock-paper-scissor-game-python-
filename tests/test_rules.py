from app.rules import (
    MOVES,
    WINNER_BOT,
    WINNER_DRAW,
    WINNER_PLAYER,
    get_winner,
    validate_move,
)


class TestMoveConstants:
    def test_moves_is_tuple(self):
        assert isinstance(MOVES, tuple)

    def test_moves_contains_three_options(self):
        assert len(MOVES) == 3

    def test_moves_contents(self):
        assert MOVES == ("rock", "paper", "scissors")

    def test_moves_are_lowercase(self):
        for move in MOVES:
            assert move == move.lower()

    def test_moves_have_no_duplicates(self):
        assert len(set(MOVES)) == len(MOVES)


class TestWinnerConstants:
    def test_winner_player_string(self):
        assert WINNER_PLAYER == "player"

    def test_winner_bot_string(self):
        assert WINNER_BOT == "bot"

    def test_winner_draw_string(self):
        assert WINNER_DRAW == "draw"

    def test_all_winners_are_distinct(self):
        winners = {WINNER_PLAYER, WINNER_BOT, WINNER_DRAW}
        assert len(winners) == 3


class TestValidateMove:
    def test_valid_moves(self):
        for move in MOVES:
            assert validate_move(move) is True

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

    def test_numbers_as_strings(self):
        assert validate_move("1") is False
        assert validate_move("123") is False

    def test_special_characters(self):
        assert validate_move("rock!") is False
        assert validate_move("@#$") is False
        assert validate_move("  ") is False

    def test_partial_valid_strings(self):
        assert validate_move("roc") is False
        assert validate_move("paper ") is False
        assert validate_move("scissor") is False

    def test_case_sensitivity(self):
        assert validate_move("ROCK") is False
        assert validate_move("Paper") is False
        assert validate_move("SCISSORS") is False

    def test_whitespace_surrounding(self):
        assert validate_move(" rock") is False
        assert validate_move("rock\n") is False
        assert validate_move("\trock") is False


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

    def test_symmetry_player_wins(self):
        assert get_winner("rock", "scissors") == WINNER_PLAYER
        assert get_winner("scissors", "rock") == WINNER_BOT

    def test_symmetry_bot_wins(self):
        assert get_winner("paper", "scissors") == WINNER_BOT
        assert get_winner("scissors", "paper") == WINNER_PLAYER

    def test_return_type_is_string(self):
        result = get_winner("rock", "scissors")
        assert isinstance(result, str)

    def test_winner_is_one_of_expected_values(self):
        for player in MOVES:
            for bot in MOVES:
                result = get_winner(player, bot)
                assert result in (WINNER_PLAYER, WINNER_BOT, WINNER_DRAW)
