from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.bot import random_bot_move
from app.memory import GameMemory
from app.rules import MOVES, get_winner, validate_move
from app.schemas import PlayRequest, PlayResponse

memory = GameMemory()
app = FastAPI(title="Rock Paper Scissors API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/play", response_model=PlayResponse)
def play(req: PlayRequest):
    result = play_round(req.player_move)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    memory.record_round(
        result["player_move"],
        result["bot_move"],
        result["winner"],
    )

    return PlayResponse(
        player_move=result["player_move"],
        bot_move=result["bot_move"],
        winner=result["winner"],
        score={
            "wins": memory.wins,
            "losses": memory.losses,
            "draws": memory.draws,
        },
    )


@app.get("/history")
def history():
    return {
        "all_rounds": memory.all_rounds,
        "latest_10": list(memory.last_10_rounds),
        "stats": memory.get_stats(),
    }


@app.post("/reset")
def reset():
    memory.reset()
    return {"status": "ok"}


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
