from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str = Field(..., alias="access_token")
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = Field("user", pattern="^(admin|user)$")
    home_dir: Optional[str] = None
    is_active: bool = True


class UserUpdate(BaseModel):
    password: Optional[str] = None
    is_active: Optional[bool] = None
    home_dir: Optional[str] = None


class UserResponse(BaseModel):
    id: str = Field(..., alias="_id")
    username: str
    role: str
    home_dir: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        populate_by_name = True


class ConnectionResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    username: str
    client_id: str
    remote_ip: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    bytes_uploaded: int = 0
    bytes_downloaded: int = 0
    active: bool = True

    class Config:
        populate_by_name = True


class TransferRecord(BaseModel):
    id: str = Field(..., alias="_id")
    connection_id: str
    username: str
    path: str
    direction: str
    size: int
    timestamp: datetime

    class Config:
        populate_by_name = True


class AnalyticsResponse(BaseModel):
    username: str
    total_upload: int
    total_download: int
    transfer_count: int


class ConnectionsSummary(BaseModel):
    total_connections: int
    active_connections: int
    total_upload: int
    total_download: int
    transfers: List[AnalyticsResponse]
