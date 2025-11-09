from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database

from .config import get_settings
from .security import hash_password, verify_password


class UserService:
    """Encapsulate user management operations."""

    def __init__(self, db: Database):
        self.users: Collection = db["users"]
        self.users.create_index("username", unique=True)
        self.settings = get_settings()
        self.root = self.settings.sftp_root.resolve()

    def _sanitize_home_dir(self, home_dir: Optional[str], fallback: str) -> str:
        value = (home_dir or fallback).strip().replace("\\", "/")
        parts = [segment for segment in value.split('/') if segment not in ("", ".", "..")]
        return '/'.join(parts) or fallback

    def _ensure_home_directory(self, home_dir: str) -> None:
        target = (self.root / Path(home_dir)).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:  # noqa: BLE001
            raise ValueError("Home directory must be within SFTP root") from exc
        target.mkdir(parents=True, exist_ok=True)

    def ensure_default_admin(self) -> None:
        """Create the default admin user if it does not exist."""
        username = self.settings.admin_default_username
        if self.users.find_one({"username": username}):
            return
        home_dir = self._sanitize_home_dir(username, username)
        self._ensure_home_directory(home_dir)
        password_hash = hash_password(self.settings.admin_default_password)
        self.users.insert_one(
            {
                "username": username,
                "password_hash": password_hash,
                "role": "admin",
                "is_active": True,
                "home_dir": home_dir,
                "created_at": datetime.utcnow(),
                "last_login": None,
            }
        )

    def get_by_username(self, username: str) -> Optional[Dict]:
        return self.users.find_one({"username": username})

    def get_by_id(self, user_id: str) -> Optional[Dict]:
        try:
            return self.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        user = self.get_by_username(username)
        if not user or not user.get("is_active", True):
            return None
        if not verify_password(password, user.get("password_hash", "")):
            return None
        self.users.update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.utcnow()}})
        return user

    def list_users(self) -> List[Dict]:
        return list(self.users.find())

    def create_user(self, username: str, password: str, role: str, home_dir: Optional[str], is_active: bool) -> Dict:
        sanitized_home = self._sanitize_home_dir(home_dir, username)
        self._ensure_home_directory(sanitized_home)
        document = {
            "username": username,
            "password_hash": hash_password(password),
            "role": role,
            "is_active": is_active,
            "home_dir": sanitized_home,
            "created_at": datetime.utcnow(),
            "last_login": None,
        }
        result = self.users.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update_user(self, user_id: str, password: Optional[str], is_active: Optional[bool], home_dir: Optional[str]) -> Optional[Dict]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        update: Dict[str, object] = {}
        if password:
            update["password_hash"] = hash_password(password)
        if is_active is not None:
            update["is_active"] = is_active
        if home_dir:
            sanitized = self._sanitize_home_dir(home_dir, user.get("home_dir") or user.get("username") or "")
            self._ensure_home_directory(sanitized)
            update["home_dir"] = sanitized
        if not update:
            return user
        self.users.update_one({"_id": ObjectId(user_id)}, {"$set": update})
        user.update(update)
        return user


class ConnectionService:
    """Persist connection telemetry for auditing and analytics."""

    def __init__(self, db: Database):
        self.connections: Collection = db["connections"]
        self.transfers: Collection = db["transfers"]
        self.connections.create_index([("user_id", 1), ("active", 1)])
        self.transfers.create_index([("connection_id", 1), ("timestamp", 1)])

    def start_connection(self, user: Dict, client_id: str, remote_ip: str) -> ObjectId:
        document = {
            "user_id": str(user["_id"]),
            "username": user["username"],
            "client_id": client_id,
            "remote_ip": remote_ip,
            "started_at": datetime.utcnow(),
            "active": True,
            "bytes_uploaded": 0,
            "bytes_downloaded": 0,
        }
        result = self.connections.insert_one(document)
        return result.inserted_id

    def end_connection(self, connection_id: ObjectId, bytes_uploaded: int, bytes_downloaded: int, transfers: List[Dict]) -> None:
        update = {
            "$set": {
                "ended_at": datetime.utcnow(),
                "active": False,
                "bytes_uploaded": bytes_uploaded,
                "bytes_downloaded": bytes_downloaded,
            }
        }
        self.connections.update_one({"_id": connection_id}, update)
        if transfers:
            for transfer in transfers:
                transfer["connection_id"] = str(connection_id)
                transfer.setdefault("timestamp", datetime.utcnow())
            self.transfers.insert_many(transfers)

    def record_transfer(self, connection_id: ObjectId, username: str, path: str, direction: str, size: int) -> None:
        document = {
            "connection_id": str(connection_id),
            "username": username,
            "path": path,
            "direction": direction,
            "size": size,
            "timestamp": datetime.utcnow(),
        }
        self.transfers.insert_one(document)
        if direction == "upload":
            self.connections.update_one({"_id": connection_id}, {"$inc": {"bytes_uploaded": size}})
        else:
            self.connections.update_one({"_id": connection_id}, {"$inc": {"bytes_downloaded": size}})

    def list_connections(self, user_id: Optional[str] = None) -> List[Dict]:
        filter_query: Dict[str, object] = {}
        if user_id:
            filter_query["user_id"] = user_id
        return list(self.connections.find(filter_query).sort("started_at", -1))

    def summaries(self) -> Dict[str, object]:
        pipeline = [
            {
                "$group": {
                    "_id": "$username",
                    "total_upload": {"$sum": "$bytes_uploaded"},
                    "total_download": {"$sum": "$bytes_downloaded"},
                    "session_count": {"$sum": 1},
                }
            }
        ]
        summary = list(self.connections.aggregate(pipeline))
        transfer_counts = {
            item["_id"]: item["count"]
            for item in self.transfers.aggregate([
                {"$group": {"_id": "$username", "count": {"$sum": 1}}}
            ])
        }
        for item in summary:
            item["transfer_count"] = transfer_counts.get(item.get("_id"), 0)
        return {
            "total_connections": self.connections.count_documents({}),
            "active_connections": self.connections.count_documents({"active": True}),
            "total_upload": sum(item.get("total_upload", 0) for item in summary),
            "total_download": sum(item.get("total_download", 0) for item in summary),
            "transfers": summary,
        }
