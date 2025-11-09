from pymongo import MongoClient

from .config import get_settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Return a singleton MongoClient instance."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = MongoClient(settings.mongodb_uri, tz_aware=True)
    return _client


def get_database():
    """Return the configured MongoDB database handle."""
    client = get_client()
    settings = get_settings()
    return client[settings.mongodb_db]
