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
COMBINED_PROMPT_TEMPLATE = """
You are a helpful and empathetic customer support agent for a SaaS billing and
subscription management platform used by thousands of small businesses.

Your responsibilities:
- Answer billing questions (invoices, charges, payment methods, pricing tiers)
- Handle refund requests (explain the 14-day money-back policy, initiate credits)
- Resolve account access issues (password resets, MFA, locked accounts)
- Assist with subscription changes (upgrades, downgrades, cancellations)
- Answer general product and feature questions

Tone guidelines:
- Be friendly, concise, and professional
- Acknowledge the customer's frustration when appropriate
- Always give a clear next step or resolution
- Keep replies under 120 words

Categories:
  Billing        – Questions about invoices, charges, payment methods, pricing, or subscription fees.
  Refund         – Requests to return a product, get money back, dispute a charge, or process a credit.
  Account Access – Issues logging in, resetting passwords, locked accounts, or MFA problems.
  Cancellation   – Requests to cancel a subscription, downgrade a plan, or close an account.
  General Inquiry– Anything that does not fit the above.

For the customer message below, respond with a JSON object with two keys:
  "reply"    – your support response (string, under 120 words)
  "category" – the single best-matching category from the list above (exact string)

Customer: {user_message}
""".strip()


def generate_chat_and_classify(user_message: str) -> tuple[str, str, int]:
    """Single Gemini call: returns (reply, category, elapsed_ms)."""
    prompt = COMBINED_PROMPT_TEMPLATE.format(user_message=user_message)
    t0 = time.time()
    try:
        resp = gemini.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": {
                    "type": "object",
                    "properties": {
                        "reply": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": CATEGORIES,
                        },
                    },
                    "required": ["reply", "category"],
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
    category = data.get("category", "General Inquiry")
    if category not in CATEGORIES:
        category = "General Inquiry"
    return reply, category, elapsed_ms


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str


class TraceCreate(BaseModel):
    user_message: str
    bot_response: str
    response_time_ms: int
    category: Optional[str] = None

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/chat")
def chat(req: ChatRequest):
    """Generate a chatbot response and classify the conversation in one LLM call."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    reply, category, response_time_ms = generate_chat_and_classify(req.message)
    return {"response": reply, "category": category, "response_time_ms": response_time_ms}


@app.post("/traces", status_code=201)
def create_trace(req: TraceCreate):
    """Persist a trace with its pre-computed category."""
    category = req.category if req.category in CATEGORIES else "General Inquiry"
    trace = {
        "id": str(uuid.uuid4()),
        "user_message": req.user_message,
        "bot_response": req.bot_response,
        "category": category,
        "timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "response_time_ms": req.response_time_ms,
    }
    conn = get_db()
    conn.execute(
        "INSERT INTO traces VALUES (:id, :user_message, :bot_response, :category, :timestamp, :response_time_ms)",
        trace,
    )
    conn.commit()
    conn.close()
    return trace


@app.get("/traces")
def get_traces(category: Optional[str] = Query(default=None)):
    """Return all traces, most recent first. Optionally filter by category."""
    conn = get_db()
    if category:
        rows = conn.execute(
            "SELECT * FROM traces WHERE category = ? ORDER BY timestamp DESC",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM traces ORDER BY timestamp DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/analytics")
def get_analytics():
    """Return aggregate statistics across all stored traces."""
    conn = get_db()
    total: int = conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
    avg_rt: float = (
        conn.execute("SELECT AVG(response_time_ms) FROM traces").fetchone()[0] or 0.0
    )
    cat_rows = conn.execute(
        "SELECT category, COUNT(*) AS cnt FROM traces GROUP BY category"
    ).fetchall()
    conn.close()

    breakdown = {cat: {"count": 0, "percentage": 0.0} for cat in CATEGORIES}
    for row in cat_rows:
        cat, cnt = row["category"], row["cnt"]
        breakdown[cat] = {
            "count": cnt,
            "percentage": round((cnt / total * 100) if total > 0 else 0.0, 1),
        }

    return {
        "total_traces": total,
        "average_response_time_ms": round(avg_rt),
        "category_breakdown": breakdown,
    }
