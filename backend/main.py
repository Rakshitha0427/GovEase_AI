import json
import logging
import os
import re
from pathlib import Path
from typing import Literal, Optional

import pymupdf
from dotenv import dotenv_values, load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT.parent / ".env"
load_dotenv(ENV_FILE)
# A blank inherited process variable prevents python-dotenv's default loader from
# filling it. In that case, use only the project file's Mongo URI; non-empty
# environment configuration continues to take precedence.
if not os.getenv("MONGODB_URI", "").strip():
    file_mongo_uri = dotenv_values(ENV_FILE).get("MONGODB_URI")
    if file_mongo_uri and file_mongo_uri.strip():
        os.environ["MONGODB_URI"] = file_mongo_uri.strip()

from backend.auth import get_optional_user, router as auth_router
from backend.database import get_database
from backend.history import ensure_conversation_owner, persist_chat, router as history_router

logger = logging.getLogger(__name__)
SCHEMES = json.loads((ROOT / "schemes.json").read_text(encoding="utf-8"))
MAX_UPLOAD = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
LOCAL_FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
CONFIGURED_FRONTEND_ORIGINS = [origin.strip().rstrip("/") for origin in os.getenv("FRONTEND_ORIGINS", "").split(",") if origin.strip()]
if "*" in CONFIGURED_FRONTEND_ORIGINS:
    raise RuntimeError("FRONTEND_ORIGINS must list explicit origins when credentials are enabled.")
if APP_ENV == "production" and not CONFIGURED_FRONTEND_ORIGINS:
    raise RuntimeError("Set FRONTEND_ORIGINS to the deployed frontend origin in production.")
ALLOWED_ORIGINS = CONFIGURED_FRONTEND_ORIGINS if APP_ENV == "production" else list(dict.fromkeys(LOCAL_FRONTEND_ORIGINS + CONFIGURED_FRONTEND_ORIGINS))
app = FastAPI(title="GovEase AI API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
app.state.database_provider = get_database
app.include_router(auth_router)
app.include_router(history_router)


@app.middleware("http")
async def enforce_browser_write_origin(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin.strip().rstrip("/") not in ALLOWED_ORIGINS:
            return JSONResponse(status_code=403, content={"detail": "Request origin is not allowed."})
    return await call_next(request)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=6000)
    language: str = Field(default="English", min_length=1, max_length=40)
    history: list[dict] = Field(default_factory=list, max_length=20)
    document: Optional[dict] = None
    conversation_id: Optional[str] = Field(default=None, max_length=24)


class Source(BaseModel):
    title: str
    authority: str
    url: str = Field(pattern=r"^https://")
    verified: str


class ChatResponse(BaseModel):
    answer: str = Field(min_length=1)
    sources: list[Source]
    mode: Literal["gemini", "demo"]
    conversation_id: Optional[str] = None


def find_schemes(query: str):
    words = set(re.findall(r"[a-z0-9]+", query.lower()))
    aliases = {"scholarship": {"education", "student", "college", "scholarship"}, "farmer": {"agriculture", "farmer", "kisan"}, "housing": {"housing", "house", "home"}, "business": {"business", "entrepreneur", "loan", "startup"}}
    for key, values in aliases.items():
        if key in query.lower():
            words |= values
    matches = []
    for s in SCHEMES:
        text = " ".join([s["name"], s["description"], s["category"]]).lower()
        score = sum(1 for w in words if len(w) > 3 and w in text)
        if score:
            matches.append((score, s))
    return [s for _, s in sorted(matches, key=lambda item: item[0], reverse=True)[:4]]


def format_schemes(items):
    if not items:
        return "I couldn't find a matching scheme in the demo catalog. Try sharing your state, occupation, or the type of support you need."
    lines = ["Here are some possible matches from the demo catalog. Please confirm current details with each official source:\n"]
    for s in items:
        lines.append(f"### {s['name']}\n**Authority:** {s['authority']}\n\n{s['description']}\n\n**Benefits:** {s['benefits']}\n\n**Eligibility to check:** " + "; ".join(x["label"] for x in s["eligibility"]) + f"\n\n[Official information]({s['url']}) · Source: {s['source']} · {s['verified']}\n")
    return "\n".join(lines)


def demo_answer(message: str, language: str, doc=None):
    low = message.lower()
    if doc:
        return f"I extracted {doc.get('pages', 0)} page(s) from **{doc.get('filename', 'your document')}**.\n\n{doc.get('text', '')[:5000]}\n\nThis summary is based only on the uploaded file. Please check the original document for complete details."
    if any(word in low for word in ("eligible", "qualify", "qualification")):
        items = find_schemes(message)
        if not items:
            return "Which scheme would you like to check? Share its name, and I’ll compare the published criteria with only the details needed. This is informational, not an approval decision."
        s = items[0]
        return f"## Eligibility check: {s['name']}\n\nI can compare your situation with the published criteria, but I need a little more information first:\n\n" + "\n".join(f"- {x['label']}?" for x in s["eligibility"]) + f"\n\nI’ll use only the information you choose to share. Final eligibility is decided by the relevant authority. [Official source]({s['url']})"
    if any(word in low for word in ("how do i apply", "how to apply", "application", "apply for", "documents needed")):
        items = find_schemes(message)
        if items:
            s = items[0]
            return f"## How to get started: {s['name']}\n\n**Documents to prepare**\n" + "\n".join(f"- {x}" for x in s["documents"]) + "\n\n**Steps**\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(s["steps"], 1)) + f"\n\n[Official information]({s['url']})\n\nRequirements can change; confirm them with the issuing authority before applying."
    if any(word in low for word in ("scheme", "scholarship", "farmer", "kisan", "housing", "loan", "entrepreneur", "student")):
        return format_schemes(find_schemes(message))
    return f"I can help find government schemes, explain eligibility, outline application steps, or summarize a PDF. Tell me your state and what kind of support you're looking for.\n\n*Demo mode is active; add a Gemini API key to enable AI-generated responses.*"


async def gemini_answer(request: ChatRequest):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return demo_answer(request.message, request.language, request.document)
    try:
        from google import genai

        client = genai.Client(api_key=key)
        sources = "\n".join(f"{s['name']}: {s['description']} Official source: {s['url']} Eligibility: {json.dumps(s['eligibility'])}" for s in SCHEMES)
        history = "\n".join(f"{x.get('role','user')}: {x.get('content','')}" for x in request.history[-8:])
        prompt = f"You are GovEase AI, a careful Indian government-services assistant. Reply in {request.language}. Use simple language. Never invent schemes, dates, fees, or official links. Use only the catalog below for scheme facts and say when it lacks information. Distinguish uncertainty; eligibility is informational and never approval. Do not reveal internal agents. For non-government general questions, answer normally.\n\nLOCAL SCHEME CATALOG (demo, may be incomplete):\n{sources}\n\nCONVERSATION:\n{history}\n\nUSER: {request.message}\n\nUPLOADED DOCUMENT EXCERPT (if any):\n{(request.document or {}).get('text','')[:10000]}"
        model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
        result = client.models.generate_content(model=model, contents=prompt)
    except Exception as exc:
        # Keep provider details and request data out of logs and client responses.
        logger.error("Gemini request failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Gemini is temporarily unavailable. Please try again.") from None

    answer = getattr(result, "text", None)
    if not isinstance(answer, str) or not answer.strip():
        logger.error("Gemini returned an empty or invalid response")
        raise HTTPException(status_code=502, detail="Gemini returned an empty response. Please try again.")
    return answer.strip()


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "gemini" if os.getenv("GEMINI_API_KEY", "").strip() else "demo", "catalog_size": len(SCHEMES)}


@app.get("/api/schemes")
def schemes(q: str = ""):
    return find_schemes(q) if q else SCHEMES


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, user: Optional[dict] = Depends(get_optional_user)):
    db = None
    if user:
        db = request.app.state.database_provider()
        if req.conversation_id:
            ensure_conversation_owner(db, req.conversation_id, user)
    answer = await gemini_answer(req)
    sources = [{"title": s["name"], "authority": s["authority"], "url": s["url"], "verified": s["verified"]} for s in find_schemes(req.message)]
    conversation_id = None
    if user:
        conversation_id = persist_chat(db, user, req.conversation_id, req.message, answer, sources, (req.document or {}).get("filename"))
    return {"answer": answer, "sources": sources, "mode": "gemini" if os.getenv("GEMINI_API_KEY", "").strip() else "demo", "conversation_id": conversation_id}


@app.post("/api/documents")
async def upload_document(file: UploadFile = File(...)):
    if file.content_type != "application/pdf" and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Please upload a PDF file.")
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail=f"PDF must be smaller than {MAX_UPLOAD // (1024 * 1024)} MB.")
    try:
        pdf = pymupdf.open(stream=content, filetype="pdf")
        pages = [{"page": i + 1, "text": page.get_text()} for i, page in enumerate(pdf)]
        text = "\n".join(f"[Page {p['page']}] {p['text']}" for p in pages).strip()
        count = len(pages)
        pdf.close()
    except Exception:
        raise HTTPException(status_code=400, detail="This PDF could not be read. It may be damaged or password protected.")
    if not text:
        raise HTTPException(status_code=422, detail="No selectable text was found. Scanned PDFs need OCR, which is not enabled in this MVP.")
    return {"filename": file.filename, "pages": count, "text": text[:30000], "page_count": count, "note": "Text extracted locally; uploaded file is not stored."}
