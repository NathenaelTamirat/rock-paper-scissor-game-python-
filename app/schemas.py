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
