from typing import Optional

from pydantic import BaseModel


class PlayRequest(BaseModel):
    player_move: str


class PlayResponse(BaseModel):
    player_move: str
    bot_move: str
    winner: str
    score: dict


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterResponse(BaseModel):
    user_id: int
    username: str


class LoginResponse(BaseModel):
    user_id: int
    token: str


class ProfileResponse(BaseModel):
    user_id: int
    username: str
    created_at: str
    stats: dict
    recent_rounds: list


class StatsResponse(BaseModel):
    total_rounds: int
    wins: int
    losses: int
    draws: int
    win_rate: float
    favorite_move: str
    streak: int


class CreateRoomResponse(BaseModel):
    room_code: str
    player_a_id: int
    player_a_username: str
    status: str


class JoinRoomResponse(BaseModel):
    room_code: str
    player_a_id: int
    player_a_username: str
    player_b_id: int
    player_b_username: str
    status: str


class RoomPlayRequest(BaseModel):
    move: str


class RoomPlayResponse(BaseModel):
    room_code: str
    status: str
    your_move: str
    opponent_move: Optional[str] = None
    winner: Optional[str] = None


class RoomStateResponse(BaseModel):
    room_code: str
    player_a_id: int
    player_a_username: str
    player_b_id: Optional[int] = None
    player_b_username: Optional[str] = None
    move_a_submitted: bool
    move_b_submitted: bool
    winner: Optional[str] = None
    status: str


class MatchmakingJoinRequest(BaseModel):
    preferred_mode: str = "classic"


class MatchmakingJoinResponse(BaseModel):
    status: str
    position: Optional[int] = None


class MatchmakingLeaveResponse(BaseModel):
    status: str


class MatchmakingStatusResponse(BaseModel):
    status: str
    position: Optional[int] = None
    room_code: Optional[str] = None


class TournamentCreateRequest(BaseModel):
    name: str
    max_players: int = 4


class TournamentCreateResponse(BaseModel):
    code: str
    name: str
    status: str
    players: list


class TournamentJoinResponse(BaseModel):
    code: str
    name: str
    status: str
    players: list


class TournamentMatchInfo(BaseModel):
    round: int
    match_index: int
    player_a_id: Optional[int] = None
    player_a_username: Optional[str] = None
    player_b_id: Optional[int] = None
    player_b_username: Optional[str] = None
    score_a: int
    score_b: int
    winner_id: Optional[int] = None
    winner_username: Optional[str] = None
    status: str


class TournamentStateResponse(BaseModel):
    code: str
    name: str
    status: str
    players: list
    matches: list
    winner_id: Optional[int] = None
    winner_username: Optional[str] = None
