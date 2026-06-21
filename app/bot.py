import random

from app.rules import MOVES


def random_bot_move() -> str:
    return random.choice(MOVES)
