import random

from app.rules import MOVES


def random_bot_move() -> str:
    return random.choice(MOVES)


def adaptive_bot_move(memory) -> str:
    move = memory.get_adaptive_move()
    if move is not None:
        return move
    return random_bot_move()
