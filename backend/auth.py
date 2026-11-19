import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

from backend.database import get_database
from backend.security import hash_password, hash_session_token, new_session_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["account"])
SESSION_COOKIE = "govease_session"
SESSION_DAYS = 7
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$")


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enter your name.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address.")
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address.")
        return value


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=5, max_length=254)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enter your name.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address.")
        return value


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: str


def public_user(user: dict) -> UserResponse:
    return UserResponse(id=str(user["_id"]), name=user["name"], email=user["email_normalized"], created_at=user["created_at"].isoformat())


def _cookie_secure() -> bool:
    configured_secure = os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes"}
    return configured_secure or _cookie_samesite() == "none"


def _cookie_samesite() -> str:
    configured = os.getenv("SESSION_COOKIE_SAMESITE", "lax").strip().lower()
    return configured if configured in {"lax", "strict", "none"} else "lax"


def set_session_cookie(response: Response, db: Database, user_id: ObjectId) -> None:
    token = new_session_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    db.sessions.insert_one({"_id": hash_session_token(token), "user_id": user_id, "expires_at": expires, "created_at": datetime.now(timezone.utc)})
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_DAYS * 24 * 60 * 60, httponly=True, secure=_cookie_secure(), samesite=_cookie_samesite(), path="/")


def resolve_session(db: Database, token: str) -> Optional[dict]:
    session = db.sessions.find_one({"_id": hash_session_token(token), "expires_at": {"$gt": datetime.now(timezone.utc)}})
    if not session:
        return None
    return db.users.find_one({"_id": session["user_id"]})


def get_optional_user(request: Request) -> Optional[dict]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    database_provider = getattr(request.app.state, "database_provider", get_database)
    db = database_provider()
    try:
        return resolve_session(db, token)
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Account storage is temporarily unavailable.") from None


def require_user(user: Optional[dict] = Depends(get_optional_user)) -> dict:
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return user


def _finish_login(response: Response, db: Database, user: dict) -> UserResponse:
    set_session_cookie(response, db, user["_id"])
    return public_user(user)


@router.post("/signup", response_model=UserResponse, status_code=201)
def signup(payload: SignupRequest, response: Response, db: Database = Depends(get_database)):
    now = datetime.now(timezone.utc)
    user = {"name": payload.name, "email_normalized": payload.email, "password_hash": hash_password(payload.password), "created_at": now, "updated_at": now}
    try:
        result = db.users.insert_one(user)
        user["_id"] = result.inserted_id
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from None
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Account storage is temporarily unavailable.") from None
    return _finish_login(response, db, user)


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Database = Depends(get_database)):
    try:
        user = db.users.find_one({"email_normalized": payload.email})
        if not user or not verify_password(payload.password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Email or password is incorrect.")
        return _finish_login(response, db, user)
    except HTTPException:
        raise
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Account storage is temporarily unavailable.") from None


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        try:
            db = request.app.state.database_provider()
            db.sessions.delete_one({"_id": hash_session_token(token)})
        except (HTTPException, PyMongoError):
            # Clear the browser cookie even if the database is temporarily unavailable.
            pass
    response.delete_cookie(SESSION_COOKIE, httponly=True, secure=_cookie_secure(), samesite=_cookie_samesite(), path="/")


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(require_user)):
    return public_user(user)


@router.patch("/profile", response_model=UserResponse)
def update_profile(payload: ProfileUpdate, response: Response, user: dict = Depends(require_user), db: Database = Depends(get_database)):
    try:
        updated = db.users.find_one_and_update(
            {"_id": user["_id"]},
            {"$set": {"name": payload.name, "email_normalized": payload.email, "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from None
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Account storage is temporarily unavailable.") from None
    if not updated:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return public_user(updated)
