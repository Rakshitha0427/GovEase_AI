import os
from threading import Lock

from fastapi import HTTPException
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

_client = None
_client_uri = None
_database = None
_indexed_database_ids: set[int] = set()
_lock = Lock()


def ensure_indexes(database: Database) -> None:
    database.users.create_index([("email_normalized", ASCENDING)], unique=True)
    database.sessions.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    database.conversations.create_index([("user_id", ASCENDING), ("updated_at", DESCENDING)])
    database.messages.create_index([("user_id", ASCENDING), ("conversation_id", ASCENDING), ("created_at", ASCENDING)])


def get_database() -> Database:
    """Return the configured MongoDB database, creating indexes on first use."""
    global _client, _client_uri, _database
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        raise HTTPException(status_code=503, detail="Account storage is not configured. Set MONGODB_URI in the backend environment.")

    database_name = os.getenv("MONGODB_DATABASE", "govease").strip() or "govease"
    try:
        with _lock:
            if _client is None or _client_uri != uri:
                if _client is not None:
                    _client.close()
                _client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000, tz_aware=True)
                _client_uri = uri
                _database = None
            if _database is None or _database.name != database_name:
                _database = _client[database_name]
            database = _database
            if id(database) not in _indexed_database_ids:
                ensure_indexes(database)
                _indexed_database_ids.add(id(database))
        return database
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Account storage is temporarily unavailable.") from None


def close_database() -> None:
    global _client, _client_uri, _database
    with _lock:
        if _client is not None:
            _client.close()
        _client = None
        _client_uri = None
        _database = None
        _indexed_database_ids.clear()
