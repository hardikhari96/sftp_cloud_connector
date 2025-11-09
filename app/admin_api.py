from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .db import get_database
from .schemas import (
    AnalyticsResponse,
    ConnectionResponse,
    ConnectionsSummary,
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from .security import create_access_token, decode_access_token
from .services import ConnectionService, UserService

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="SFTP Cloud Connector Admin API", version="1.0.0")
security = HTTPBearer()
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

db = get_database()
user_service = UserService(db)
connection_service = ConnectionService(db)
user_service.ensure_default_admin()


@app.get("/", response_class=HTMLResponse)
def admin_console(request: Request) -> HTMLResponse:
    from .config import get_settings  # local import to avoid circular dependency at startup

    settings = get_settings()
    host = request.url.hostname or (request.client.host if request.client else "localhost")
    connection_details = {
        "host": host,
        "port": 2222,
        "default_username": settings.admin_default_username,
        "default_password": settings.admin_default_password,
    }
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "connection_details": connection_details,
        },
    )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    user_id = payload.get("user_id")
    user = user_service.get_by_id(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or missing")
    return user


def require_admin(user: Dict = Depends(get_current_user)) -> Dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    user = user_service.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"user_id": str(user["_id"]), "role": user["role"], "username": user["username"]})
    return TokenResponse(access_token=token)


@app.get("/users", response_model=List[UserResponse])
def list_users(_: Dict = Depends(require_admin)) -> List[UserResponse]:
    users = user_service.list_users()
    for user in users:
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
    return users


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, admin: Dict = Depends(require_admin)) -> UserResponse:
    del admin  # admin context not used directly
    if user_service.get_by_username(payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    try:
        document = user_service.create_user(payload.username, payload.password, payload.role, payload.home_dir, payload.is_active)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    document["_id"] = str(document["_id"])
    document.pop("password_hash", None)
    return document


@app.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: str, payload: UserUpdate, admin: Dict = Depends(require_admin)) -> UserResponse:
    # Prevent admin from deactivating themselves
    if str(admin["_id"]) == user_id and payload.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account")
    
    try:
        user = user_service.update_user(user_id, payload.password, payload.is_active, payload.home_dir, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user["_id"] = str(user["_id"])
    user.pop("password_hash", None)
    return user


@app.get("/connections", response_model=List[ConnectionResponse])
def list_connections(user_id: Optional[str] = None, limit: int = 100, _: Dict = Depends(require_admin)) -> List[ConnectionResponse]:
    connections = connection_service.list_connections(user_id, limit)
    for conn in connections:
        conn["_id"] = str(conn["_id"])
    return connections


@app.get("/analytics", response_model=ConnectionsSummary)
def analytics(current_user: Dict = Depends(get_current_user)) -> ConnectionsSummary:
    # Admin users see all analytics, regular users see only their own
    user_id_filter = None if current_user.get("role") == "admin" else str(current_user["_id"])
    summary = connection_service.summaries(user_id_filter)
    transfers = [
        AnalyticsResponse(
            username=item.get("_id", "unknown"),
            total_upload=item.get("total_upload", 0),
            total_download=item.get("total_download", 0),
            transfer_count=item.get("transfer_count", 0),
        )
        for item in summary.get("transfers", [])
    ]
    return ConnectionsSummary(
        total_connections=summary.get("total_connections", 0),
        active_connections=summary.get("active_connections", 0),
        total_upload=summary.get("total_upload", 0),
        total_download=summary.get("total_download", 0),
        transfers=transfers,
    )


@app.get("/me/connections", response_model=List[ConnectionResponse])
def list_my_connections(current_user: Dict = Depends(get_current_user)) -> List[ConnectionResponse]:
    connections = connection_service.list_connections(str(current_user["_id"]))
    for conn in connections:
        conn["_id"] = str(conn["_id"])
    return connections


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, admin: Dict = Depends(require_admin)) -> None:
    # Prevent admin from deleting themselves
    if str(admin["_id"]) == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")
    
    if not user_service.delete_user(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@app.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: Dict = Depends(get_current_user)) -> UserResponse:
    current_user["_id"] = str(current_user["_id"])
    current_user.pop("password_hash", None)
    return current_user
