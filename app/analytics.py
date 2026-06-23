from typing import Optional


def compute_win_rate(wins: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(wins / total, 4)


def compute_streak_update(current_streak: int, won: bool) -> int:
    if won:
        return current_streak + 1
    return 0


def pick_favorite_move(move_counts: dict) -> Optional[str]:
    if not move_counts or all(c == 0 for c in move_counts.values()):
        return None
    max_count = max(move_counts.values())
    tied = [m for m, c in move_counts.items() if c == max_count]
    import random
    return random.choice(tied)
