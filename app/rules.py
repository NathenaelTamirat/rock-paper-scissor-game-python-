import random
from typing import Optional

MOVES = ("rock", "paper", "scissors")

WINNER_PLAYER = "player"
WINNER_BOT = "bot"
WINNER_DRAW = "draw"

_WIN_AGAINST = {
    "rock": "scissors",
    "paper": "rock",
    "scissors": "paper",
}

COUNTER = {
    "rock": "paper",
    "paper": "scissors",
    "scissors": "rock",
}

LOSER = {
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


def get_counter_move(move: str) -> Optional[str]:
    return COUNTER.get(move)


def get_loser_move(move: str) -> Optional[str]:
    return LOSER.get(move)


def random_move() -> str:
    return random.choice(MOVES)


def determine_series_winner(
    score_a: int,
    score_b: int,
    player_a_id: int,
    player_b_id: int,
    best_of: int = 3,
) -> Optional[int]:
    if score_a > best_of // 2:
        return player_a_id
    if score_b > best_of // 2:
        return player_b_id
    return None
