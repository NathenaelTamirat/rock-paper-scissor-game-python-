from app.rules import COUNTER, random_move


def random_bot_move() -> str:
    return random_move()


def adaptive_bot_move(memory) -> str:
    move = memory.get_adaptive_move()
    if move is not None:
        return move
    return random_bot_move()


def _aggressive_move(memory) -> str:
    if memory.total_rounds == 0:
        return random_bot_move()
    predicted = memory.predict_player_next_move()
    if predicted is None:
        return random_bot_move()
    return COUNTER[predicted]


def _defensive_move(memory) -> str:
    if memory.total_rounds == 0 or not memory.all_rounds:
        return random_bot_move()
    last = memory.all_rounds[-1]
    if last["winner"] == "player":
        return COUNTER[last["player_move"]]
    if last["winner"] == "bot":
        return last["bot_move"]
    return random_bot_move()


PERSONA_STRATEGIES = {
    "classic": adaptive_bot_move,
    "aggressive": _aggressive_move,
    "defensive": _defensive_move,
    "random": lambda memory: random_bot_move(),
}


def persona_bot_move(memory, persona: str) -> str:
    strategy = PERSONA_STRATEGIES.get(persona, adaptive_bot_move)
    return strategy(memory)
