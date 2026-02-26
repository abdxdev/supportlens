import json
import os
import sqlite3
import time
import uuid
import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import errors as genai_errors

load_dotenv()

# ---------------------------------------------------------------------------
# App & CORS
# ---------------------------------------------------------------------------
app = FastAPI(title="SupportLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set")

gemini = genai.Client(api_key=GEMINI_API_KEY)

CATEGORIES = ["Billing", "Refund", "Account Access", "Cancellation", "General Inquiry"]

# ---------------------------------------------------------------------------
# SQLite database
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "supportlens.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS traces (
            id                TEXT    PRIMARY KEY,
            user_message      TEXT    NOT NULL,
            bot_response      TEXT    NOT NULL,
            category          TEXT    NOT NULL,
            timestamp         TEXT    NOT NULL,
            response_time_ms  INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()

# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "PROMPT.md")
COMBINED_PROMPT_TEMPLATE = open(_PROMPT_PATH).read().strip()


def generate_chat_and_classify(user_message: str) -> tuple[str, list[str], int]:
    prompt = COMBINED_PROMPT_TEMPLATE.replace("{user_message}", user_message)
    t0 = time.time()
    try:
        resp = gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": {
                    "type": "object",
                    "properties": {
                        "reply": {"type": "string"},
                        "categories": {
                            "type": "array",
                            "items": {"type": "string", "enum": CATEGORIES},
                            "minItems": 1,
                            "maxItems": 2,
                        },
                    },
                    "required": ["reply", "categories"],
                },
            },
        )
    except genai_errors.ClientError as e:
        if e.code == 429:
            raise HTTPException(
                status_code=429,
                detail="Gemini API rate limit reached. Please wait a moment and try again.",
            )
        raise HTTPException(status_code=502, detail=f"Gemini API error: {e}")
    elapsed_ms = int((time.time() - t0) * 1000)
    data = json.loads(resp.text)
    reply = data.get("reply", "").strip()
    raw = data.get("categories", ["General Inquiry"])
    cats = list(dict.fromkeys(c for c in raw if c in CATEGORIES))[:2] or ["General Inquiry"]
    return reply, cats, elapsed_ms


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str


class TraceCreate(BaseModel):
    user_message: str
    bot_response: str
    response_time_ms: int
    categories: list[str] = ["General Inquiry"]

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    reply, categories, response_time_ms = generate_chat_and_classify(req.message)
    return {"response": reply, "categories": categories, "response_time_ms": response_time_ms}


@app.post("/traces", status_code=201)
def create_trace(req: TraceCreate):
    cats = list(dict.fromkeys(c for c in req.categories if c in CATEGORIES))[:2] or ["General Inquiry"]
    trace = {
        "id": str(uuid.uuid4()),
        "user_message": req.user_message,
        "bot_response": req.bot_response,
        "categories": cats,
        "timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "response_time_ms": req.response_time_ms,
    }
    conn = get_db()
    conn.execute(
        "INSERT INTO traces VALUES (:id, :user_message, :bot_response, :category, :timestamp, :response_time_ms)",
        {**trace, "category": json.dumps(cats)},
    )
    conn.commit()
    conn.close()
    return trace


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["categories"] = json.loads(d.pop("category"))
    return d


@app.get("/traces")
def get_traces(category: Optional[str] = Query(default=None)):
    conn = get_db()
    if category:
        rows = conn.execute(
            'SELECT * FROM traces WHERE category LIKE ? ORDER BY timestamp DESC',
            (f'%"{category}"%',),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM traces ORDER BY timestamp DESC").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


@app.get("/analytics")
def get_analytics():
    conn = get_db()
    total: int = conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
    avg_rt: float = (
        conn.execute("SELECT AVG(response_time_ms) FROM traces").fetchone()[0] or 0.0
    )
    cat_col_rows = conn.execute("SELECT category FROM traces").fetchall()
    conn.close()

    counts: dict[str, int] = {cat: 0 for cat in CATEGORIES}
    for row in cat_col_rows:
        for cat in json.loads(row["category"]):
            if cat in counts:
                counts[cat] += 1

    total_hits = sum(counts.values()) or 1  # denominator for percentage
    breakdown = {
        cat: {
            "count": counts[cat],
            "percentage": round(counts[cat] / total_hits * 100, 1),
        }
        for cat in CATEGORIES
    }

    return {
        "total_traces": total,
        "average_response_time_ms": round(avg_rt),
        "category_breakdown": breakdown,
    }
