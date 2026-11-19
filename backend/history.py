from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from pymongo.database import Database
from pymongo.errors import PyMongoError

from backend.auth import require_user
from backend.database import get_database

router = APIRouter(prefix="/api/conversations", tags=["conversation history"])


class RenameConversation(BaseModel):
    title: str = Field(min_length=1, max_length=100)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty.")
        return value


def _id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return ObjectId(value)


def _owned_conversation(db: Database, conversation_id: str, user: dict) -> dict:
    try:
        conversation = db.conversations.find_one({"_id": _id(conversation_id), "user_id": user["_id"]})
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Conversation storage is temporarily unavailable.") from None
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


def ensure_conversation_owner(db: Database, conversation_id: str, user: dict) -> dict:
    return _owned_conversation(db, conversation_id, user)


def persist_chat(db: Database, user: dict, conversation_id: Optional[str], user_text: str, assistant_text: str, sources: list[dict], attachment_name: Optional[str] = None) -> str:
    now = datetime.now(timezone.utc)
    if conversation_id:
        conversation = _owned_conversation(db, conversation_id, user)
        oid = conversation["_id"]
        db.conversations.update_one({"_id": oid, "user_id": user["_id"]}, {"$set": {"updated_at": now}})
    else:
        title = " ".join(user_text.split())[:78] or "New conversation"
        result = db.conversations.insert_one({"user_id": user["_id"], "title": title, "created_at": now, "updated_at": now})
        oid = result.inserted_id
    user_message = {"user_id": user["_id"], "conversation_id": oid, "role": "user", "content": user_text, "created_at": now}
    if attachment_name:
        user_message["attachment_name"] = attachment_name
    assistant_message = {"user_id": user["_id"], "conversation_id": oid, "role": "assistant", "content": assistant_text, "sources": sources, "created_at": now}
    db.messages.insert_many([user_message, assistant_message])
    return str(oid)


@router.get("")
def list_conversations(user: dict = Depends(require_user), db: Database = Depends(get_database)):
    try:
        items = db.conversations.find({"user_id": user["_id"]}).sort("updated_at", -1).limit(100)
        return [{"id": str(item["_id"]), "title": item["title"], "updated_at": item["updated_at"].isoformat()} for item in items]
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Conversation storage is temporarily unavailable.") from None


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, user: dict = Depends(require_user), db: Database = Depends(get_database)):
    conversation = _owned_conversation(db, conversation_id, user)
    try:
        items = db.messages.find({"conversation_id": conversation["_id"], "user_id": user["_id"]}).sort("created_at", 1)
        messages = []
        for item in items:
            message = {"id": str(item["_id"]), "role": item["role"], "content": item["content"], "created_at": item["created_at"].isoformat()}
            if item.get("sources"):
                message["sources"] = item["sources"]
            if item.get("attachment_name"):
                message["file"] = item["attachment_name"]
            messages.append(message)
        return {"id": str(conversation["_id"]), "title": conversation["title"], "messages": messages}
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Conversation storage is temporarily unavailable.") from None


@router.patch("/{conversation_id}")
def rename_conversation(conversation_id: str, payload: RenameConversation, user: dict = Depends(require_user), db: Database = Depends(get_database)):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be empty.")
    conversation = _owned_conversation(db, conversation_id, user)
    try:
        db.conversations.update_one({"_id": conversation["_id"], "user_id": user["_id"]}, {"$set": {"title": title, "updated_at": datetime.now(timezone.utc)}})
        return {"id": str(conversation["_id"]), "title": title}
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Conversation storage is temporarily unavailable.") from None


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, user: dict = Depends(require_user), db: Database = Depends(get_database)):
    conversation = _owned_conversation(db, conversation_id, user)
    try:
        db.messages.delete_many({"conversation_id": conversation["_id"], "user_id": user["_id"]})
        db.conversations.delete_one({"_id": conversation["_id"], "user_id": user["_id"]})
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Conversation storage is temporarily unavailable.") from None
