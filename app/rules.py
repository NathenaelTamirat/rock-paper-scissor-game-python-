MOVES = ("rock", "paper", "scissors")

WINNER_PLAYER = "player"
WINNER_BOT = "bot"
WINNER_DRAW = "draw"

_WIN_AGAINST = {
    "rock": "scissors",
    "paper": "rock",
    "scissors": "paper",
}


def validate_move(move: str) -> bool:
    return move in MOVES


def get_winner(player_move: str, bot_move: str) -> str:
    if player_move == bot_move:
        return WINNER_DRAW
    if _WIN_AGAINST[player_move] == bot_move:
        return WINNER_PLAYER
    return WINNER_BOT
