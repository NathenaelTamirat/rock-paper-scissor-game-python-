import random
from typing import Optional

from app.rules import COUNTER, MOVES, random_move, get_counter_move

MIN_PLAYERS = 4
ROUND_NAMES = {1: "Semifinal", 2: "Final"}


def get_seeded_players(players: list) -> list:
    return sorted(players, key=lambda p: p["seed"])


def get_round_name(round_num: int) -> str:
    return ROUND_NAMES.get(round_num, f"Round {round_num}")


def create_round_pairings(seeded: list) -> list[tuple]:
    n = len(seeded)
    pairings = []
    for i in range(n // 2):
        pairings.append((seeded[i], seeded[n - 1 - i]))
    return pairings


def simulate_match(
    player_a_id: int,
    player_b_id: int,
    best_of: int = 3,
) -> dict:
    score_a, score_b = 0, 0
    rounds_played = 0

    for _ in range(best_of):
        if score_a > best_of // 2 or score_b > best_of // 2:
            break
        move_a = random_move()
        move_b = random_move()
        rounds_played += 1

        from app.rules import get_winner
        result = get_winner(move_a, move_b)
        if result == "player":
            score_a += 1
        elif result == "bot":
            score_b += 1

    winner_id = player_a_id if score_a > score_b else player_b_id

    return {
        "score_a": score_a,
        "score_b": score_b,
        "winner_id": winner_id,
        "rounds_played": rounds_played,
    }


def build_bracket(players: list) -> list[dict]:
    seeded = get_seeded_players(players)
    pairings = create_round_pairings(seeded)
    bracket = []

    for idx, (p_a, p_b) in enumerate(pairings):
        bracket.append({
            "round": 1,
            "match_index": idx,
            "player_a_id": p_a["user_id"],
            "player_b_id": p_b["user_id"],
            "score_a": 0,
            "score_b": 0,
            "winner_id": None,
            "status": "pending",
        })
    return bracket


def run_bracket(players: list) -> list[dict]:
    seeded = get_seeded_players(players)
    pairings = create_round_pairings(seeded)
    matches = []
    finalists = []

    for idx, (p_a, p_b) in enumerate(pairings):
        result = simulate_match(p_a["user_id"], p_b["user_id"])
        matches.append({
            "round": 1,
            "match_index": idx,
            "player_a_id": p_a["user_id"],
            "player_b_id": p_b["user_id"],
            "score_a": result["score_a"],
            "score_b": result["score_b"],
            "winner_id": result["winner_id"],
            "status": "complete",
        })
        finalists.append(result["winner_id"])

    result = simulate_match(finalists[0], finalists[1])
    matches.append({
        "round": 2,
        "match_index": 0,
        "player_a_id": finalists[0],
        "player_b_id": finalists[1],
        "score_a": result["score_a"],
        "score_b": result["score_b"],
        "winner_id": result["winner_id"],
        "status": "complete",
    })

    return matches
