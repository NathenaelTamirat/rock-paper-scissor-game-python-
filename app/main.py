from app.bot import random_bot_move
from app.rules import MOVES, get_winner, validate_move


def play_round(player_move: str) -> dict:
    normalized = player_move.strip().lower()

    if not validate_move(normalized):
        return {"error": f"Invalid move. Choose from {', '.join(MOVES)}."}

    bot_move = random_bot_move()
    winner = get_winner(normalized, bot_move)

    return {
        "player_move": normalized,
        "bot_move": bot_move,
        "winner": winner,
    }


def main() -> None:
    print("=== Rock Paper Scissors ===")
    print("Options: rock, paper, scissors")
    print("Type 'quit' to exit.\n")

    while True:
        player_move = input("Your move: ").strip().lower()

        if player_move == "quit":
            print("Goodbye!")
            break

        result = play_round(player_move)

        if "error" in result:
            print(result["error"])
            continue

        print(f"  Bot chose: {result['bot_move']}")
        print(f"  Winner: {result['winner']}\n")


if __name__ == "__main__":
    main()
