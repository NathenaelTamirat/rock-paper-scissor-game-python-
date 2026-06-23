import random
from typing import Optional

MOVES = ("rock", "paper", "scissors")

WINNER_PLAYER = "player"
WINNER_BOT = "bot"
WINNER_DRAW = "draw"

_BEATS = {
    "rock": "scissors",
    "paper": "rock",
    "scissors": "paper",
}

COUNTER = {
    "rock": "paper",
    "paper": "scissors",
    "scissors": "rock",
}


def validate_move(move: str) -> bool:
    return move in MOVES


def get_winner(player_move: str, bot_move: str) -> str:
    if player_move == bot_move:
        return WINNER_DRAW
    if _BEATS[player_move] == bot_move:
        return WINNER_PLAYER
    return WINNER_BOT


def get_counter_move(move: str) -> Optional[str]:
    return COUNTER.get(move)


def random_move() -> str:
    return random.choice(MOVES)
