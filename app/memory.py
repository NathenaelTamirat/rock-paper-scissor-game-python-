import random
from collections import deque
from typing import Optional

from app.rules import (
    COUNTER,
    MOVES,
    WINNER_BOT,
    WINNER_DRAW,
    WINNER_PLAYER,
)

MIN_HISTORY_FOR_ADAPTIVE = 3


class GameMemory:
    def __init__(self) -> None:
        self.total_rounds: int = 0
        self.wins: int = 0
        self.losses: int = 0
        self.draws: int = 0
        self.player_move_counts: dict[str, int] = {m: 0 for m in MOVES}
        self.bot_move_counts: dict[str, int] = {m: 0 for m in MOVES}
        self.player_streak: int = 0
        self.all_rounds: list[dict] = []
        self.last_10_rounds: deque[dict] = deque(maxlen=10)

    def record_round(
        self, player_move: str, bot_move: str, winner: str
    ) -> None:
        self.total_rounds += 1
        self.player_move_counts[player_move] += 1
        self.bot_move_counts[bot_move] += 1

        if winner == WINNER_PLAYER:
            self.wins += 1
            self.player_streak += 1
        elif winner == WINNER_BOT:
            self.losses += 1
            self.player_streak = 0
        else:
            self.draws += 1
            self.player_streak = 0

        round_data = {
            "player_move": player_move,
            "bot_move": bot_move,
            "winner": winner,
        }
        self.all_rounds.append(round_data)
        self.last_10_rounds.append(round_data)

    def predict_player_next_move(self) -> Optional[str]:
        if self.total_rounds == 0:
            return None

        max_count = max(self.player_move_counts.values())
        tied_moves = [
            m for m, c in self.player_move_counts.items() if c == max_count
        ]
        return random.choice(tied_moves)

    def get_stats(self) -> dict:
        win_rate = 0.0
        if self.total_rounds > 0:
            win_rate = round(self.wins / self.total_rounds, 4)

        favorite_move = "none"
        if self.total_rounds > 0:
            max_count = max(self.player_move_counts.values())
            tied = [m for m, c in self.player_move_counts.items()
                    if c == max_count]
            favorite_move = random.choice(tied)

        return {
            "total_rounds": self.total_rounds,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "win_rate": win_rate,
            "favorite_move": favorite_move,
            "streak": self.player_streak,
        }

    def reset(self) -> None:
        self.__init__()

    def get_adaptive_move(self) -> Optional[str]:
        if self.total_rounds < MIN_HISTORY_FOR_ADAPTIVE:
            return None

        predicted = self.predict_player_next_move()
        if predicted is None:
            return None
        return COUNTER[predicted]
