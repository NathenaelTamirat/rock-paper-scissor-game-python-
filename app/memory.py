import random
from collections import deque
from typing import Optional

from app.rules import MOVES, WINNER_PLAYER, WINNER_DRAW

_COUNTER = {
    "rock": "paper",
    "paper": "scissors",
    "scissors": "rock",
}

MIN_HISTORY_FOR_ADAPTIVE = 3


class GameMemory:
    def __init__(self) -> None:
        self.total_rounds: int = 0
        self.player_move_counts: dict[str, int] = {m: 0 for m in MOVES}
        self.bot_move_counts: dict[str, int] = {m: 0 for m in MOVES}
        self.player_streak: int = 0
        self.last_10_rounds: deque[dict] = deque(maxlen=10)

    def record_round(
        self, player_move: str, bot_move: str, winner: str
    ) -> None:
        self.total_rounds += 1
        self.player_move_counts[player_move] += 1
        self.bot_move_counts[bot_move] += 1

        if winner == WINNER_PLAYER:
            self.player_streak += 1
        else:
            self.player_streak = 0

        self.last_10_rounds.append({
            "player_move": player_move,
            "bot_move": bot_move,
            "winner": winner,
        })

    def predict_player_next_move(self) -> Optional[str]:
        if self.total_rounds == 0:
            return None

        max_count = max(self.player_move_counts.values())
        tied_moves = [
            m for m, c in self.player_move_counts.items() if c == max_count
        ]
        return random.choice(tied_moves)

    def get_adaptive_move(self) -> Optional[str]:
        if self.total_rounds < MIN_HISTORY_FOR_ADAPTIVE:
            return None

        predicted = self.predict_player_next_move()
        if predicted is None:
            return None
        return _COUNTER[predicted]
