from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from typing import Optional

from app.bot import persona_bot_move
from app.database import Database
from app.memory import GameMemory
from app.rules import MOVES, get_winner, validate_move
from app.schemas import (
    AnalyticsMovesResponse,
    AnalyticsSummaryResponse,
    AnalyticsTimelineResponse,
    CreateRoomResponse,
    JoinRoomResponse,
    LoginRequest,
    LoginResponse,
    MatchmakingJoinRequest,
    MatchmakingJoinResponse,
    MatchmakingLeaveResponse,
    MatchmakingStatusResponse,
    PlayRequest,
    PlayResponse,
    ProfileResponse,
    RegisterRequest,
    RegisterResponse,
    RoomPlayRequest,
    RoomPlayResponse,
    RoomStateResponse,
    TournamentCreateRequest,
    TournamentCreateResponse,
    TournamentJoinResponse,
    TournamentStateResponse,
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


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


def play_round(player_move: str, persona: str = "classic") -> dict:
    normalized = player_move.strip().lower()

    if not validate_move(normalized):
        return {"error": f"Invalid move. Choose from {', '.join(MOVES)}."}

    bot_move = persona_bot_move(memory, persona)
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
    result = play_round(req.player_move, persona=req.persona)

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


@app.post("/logout")
def logout(authorization: str = Header(default="")):
    if authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):].strip()
        db.delete_session(token)
    return {"status": "ok"}


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


@app.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
def analytics_summary(authorization: str = Header(default="")):
    user_id = _resolve_user(authorization)
    if user_id is None:
        if memory.total_rounds == 0:
            return AnalyticsSummaryResponse(
                total_rounds=0, wins=0, losses=0, draws=0,
                win_rate=0.0, favorite_move=None, streak=0,
            )
        mem = memory.get_stats()
        return AnalyticsSummaryResponse(**mem)
    return AnalyticsSummaryResponse(**db.get_analytics_summary(user_id))


@app.get("/analytics/moves", response_model=AnalyticsMovesResponse)
def analytics_moves(authorization: str = Header(default="")):
    user_id = _resolve_user(authorization)
    if user_id is None:
        dist = [
            {"move": m, "count": memory.player_move_counts[m]}
            for m in MOVES
        ]
        return AnalyticsMovesResponse(distribution=dist)
    return AnalyticsMovesResponse(
        distribution=db.get_analytics_move_distribution(user_id),
    )


@app.get("/analytics/timeline", response_model=AnalyticsTimelineResponse)
def analytics_timeline(
    days: int = Query(default=7, ge=1, le=365),
    authorization: str = Header(default=""),
):
    user_id = _resolve_user(authorization)
    if user_id is None:
        return AnalyticsTimelineResponse(timeline=[])
    return AnalyticsTimelineResponse(
        timeline=db.get_analytics_timeline(user_id, days),
    )


@app.post("/rooms", response_model=CreateRoomResponse)
def create_room(authorization: str = Header(default="")):
    user_id = _resolve_user(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    room = db.create_room(user_id)
    return CreateRoomResponse(
        room_code=room["room_code"],
        player_a_id=room["player_a_id"],
        player_a_username=room["player_a_username"],
        status=room["status"],
    )


@app.post("/rooms/{room_code}/join", response_model=JoinRoomResponse)
def join_room(room_code: str, authorization: str = Header(default="")):
    user_id = _resolve_user(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        room = db.join_room(room_code.upper(), user_id)
    except ValueError as e:
        msg = str(e)
        status = 404 if msg == "Room not found" else 400
        raise HTTPException(status_code=status, detail=msg)
    return JoinRoomResponse(
        room_code=room["room_code"],
        player_a_id=room["player_a_id"],
        player_a_username=room["player_a_username"],
        player_b_id=room["player_b_id"],
        player_b_username=room["player_b_username"],
        status=room["status"],
    )


@app.post("/rooms/{room_code}/play", response_model=RoomPlayResponse)
def room_play(
    room_code: str,
    req: RoomPlayRequest,
    authorization: str = Header(default=""),
):
    user_id = _resolve_user(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    move = req.move.strip().lower()
    if not validate_move(move):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid move. Choose from {', '.join(MOVES)}.",
        )

    try:
        room = db.submit_room_move(room_code.upper(), user_id, move)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    is_a = room["player_a_id"] == user_id
    your_move = room["move_a"] if is_a else room["move_b"]
    opponent_move = None
    winner = None
    if room["status"] == "complete":
        opponent_move = room["move_b"] if is_a else room["move_a"]
        winner = room["winner"]

    return RoomPlayResponse(
        room_code=room["room_code"],
        status=room["status"],
        your_move=your_move,
        opponent_move=opponent_move,
        winner=winner,
    )


@app.get("/rooms/{room_code}", response_model=RoomStateResponse)
def room_state(room_code: str):
    room = db.get_room(room_code.upper())
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found.")

    return RoomStateResponse(
        room_code=room["room_code"],
        player_a_id=room["player_a_id"],
        player_a_username=room["player_a_username"],
        player_b_id=room["player_b_id"],
        player_b_username=room["player_b_username"],
        move_a_submitted=room["move_a"] is not None,
        move_b_submitted=room["move_b"] is not None,
        winner=room["winner"] if room["status"] == "complete" else None,
        status=room["status"],
    )


@app.post("/matchmaking/join", response_model=MatchmakingJoinResponse)
def matchmaking_join(
    req: MatchmakingJoinRequest,
    authorization: str = Header(default=""),
):
    user_id = _resolve_user(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    db.join_queue(user_id, req.preferred_mode)
    db.process_queue()
    pos = db.get_queue_position(user_id)

    if pos is not None:
        return MatchmakingJoinResponse(status="searching", position=pos)

    return MatchmakingJoinResponse(status="matched")


@app.post("/matchmaking/leave", response_model=MatchmakingLeaveResponse)
def matchmaking_leave(authorization: str = Header(default="")):
    user_id = _resolve_user(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    db.leave_queue(user_id)
    return MatchmakingLeaveResponse(status="ok")


@app.get("/tournaments")
def list_tournaments():
    return {"tournaments": db.list_open_tournaments()}


@app.post("/tournaments", response_model=TournamentCreateResponse)
def create_tournament(
    req: TournamentCreateRequest,
    authorization: str = Header(default=""),
):
    user_id = _resolve_user(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    t = db.create_tournament(req.name, user_id, req.max_players)
    return TournamentCreateResponse(
        code=t["code"], name=t["name"], status=t["status"],
        players=t["players"],
    )


@app.post("/tournaments/{code}/join", response_model=TournamentJoinResponse)
def join_tournament(
    code: str,
    authorization: str = Header(default=""),
):
    user_id = _resolve_user(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        t = db.join_tournament(code.upper(), user_id)
    except ValueError as e:
        msg = str(e)
        status_code = 404 if msg == "Tournament not found" else 400
        raise HTTPException(status_code=status_code, detail=msg)
    return TournamentJoinResponse(
        code=t["code"], name=t["name"], status=t["status"],
        players=t["players"],
    )


@app.post("/tournaments/{code}/run", response_model=TournamentStateResponse)
def run_tournament(
    code: str,
    authorization: str = Header(default=""),
):
    user_id = _resolve_user(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        t = db.run_tournament(code.upper())
    except ValueError as e:
        msg = str(e)
        status_code = 404 if msg == "Tournament not found" else 400
        raise HTTPException(status_code=status_code, detail=msg)
    return TournamentStateResponse(
        code=t["code"], name=t["name"], status=t["status"],
        players=t["players"], matches=t["matches"],
        winner_id=t["winner_id"], winner_username=t["winner_username"],
    )


@app.get("/tournaments/{code}", response_model=TournamentStateResponse)
def tournament_state(code: str):
    t = db.get_tournament(code.upper())
    if t is None:
        raise HTTPException(status_code=404, detail="Tournament not found.")
    return TournamentStateResponse(
        code=t["code"], name=t["name"], status=t["status"],
        players=t["players"], matches=t["matches"],
        winner_id=t["winner_id"], winner_username=t["winner_username"],
    )


@app.get("/matchmaking/status/{user_id}", response_model=MatchmakingStatusResponse)
def matchmaking_status(user_id: int, authorization: str = Header(default="")):
    caller_id = _resolve_user(authorization)
    if caller_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    pos = db.get_queue_position(user_id)
    if pos is not None:
        return MatchmakingStatusResponse(status="searching", position=pos)

    room = db.get_user_active_room(user_id)
    if room is not None:
        return MatchmakingStatusResponse(
            status="matched", room_code=room["room_code"],
        )

    return MatchmakingStatusResponse(status="idle")


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
