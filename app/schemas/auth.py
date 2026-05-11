from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 86400

class FCMTokenRequest(BaseModel):
    fcm_token: str
    device_id: str
    platform: str = "android"

class LogoutRequest(BaseModel):
    device_id: str