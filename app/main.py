from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from typing import Optional

from app.bot import random_bot_move
from app.database import Database
from app.memory import GameMemory
from app.rules import MOVES, get_winner, validate_move
from app.schemas import (
    LoginRequest,
    LoginResponse,
    PlayRequest,
    PlayResponse,
    ProfileResponse,
    RegisterRequest,
    RegisterResponse,
)

memory = GameMemory()
db = Database()
app = FastAPI(title="Rock Paper Scissors API")

app.mount("/static", StaticFiles(directory="static"), name="static")

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


def _resolve_user(authorization: str = "") -> Optional[int]:
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[len("Bearer "):].strip()
    return db.get_session_user_id(token)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/play", response_model=PlayResponse)
def play(
    req: PlayRequest,
    authorization: str = Header(default=""),
):
    result = play_round(req.player_move)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    memory.record_round(
        result["player_move"],
        result["bot_move"],
        result["winner"],
    )

    user_id = _resolve_user(authorization)
    if user_id is not None:
        db.record_round(
            user_id,
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


@app.post("/register", response_model=RegisterResponse)
def register(req: RegisterRequest):
    username = req.username.strip()
    if not username or len(username) < 2:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 2 characters.",
        )
    if len(req.password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 4 characters.",
        )

    user_id = db.create_user(username, req.password)
    if user_id == -1:
        raise HTTPException(
            status_code=409,
            detail="Username already taken.",
        )
    return RegisterResponse(user_id=user_id, username=username)


@app.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    user = db.verify_login(req.username.strip(), req.password)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )
    token = db.create_session(user["id"])
    return LoginResponse(user_id=user["id"], token=token)


@app.get("/profile/{user_id}", response_model=ProfileResponse)
def profile(user_id: int):
    user = db.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    stats = db.get_user_stats(user_id) or {}
    recent = db.get_user_rounds(user_id, limit=10)

    return ProfileResponse(
        user_id=user["id"],
        username=user["username"],
        created_at=user["created_at"],
        stats=stats,
        recent_rounds=recent,
    )


@app.get("/leaderboard")
def leaderboard(limit: int = Query(default=10, ge=1, le=100)):
    return {"leaderboard": db.get_leaderboard(limit=limit)}


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
