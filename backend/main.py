import json
import os
import time
import uuid
import datetime
from typing import Optional
from contextlib import asynccontextmanager

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from logger import logger

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://supportlens:supportlens@localhost:5432/supportlens",
)

CATEGORIES = [
    "Billing",
    "Refund",
    "Account Access",
    "Cancellation",
    "General Inquiry",
    "Error",
]

gemini = None
genai_errors = None

if GEMINI_API_KEY:
    try:
        from google import genai
        from google.genai import errors as _genai_errors

        gemini = genai.Client(api_key=GEMINI_API_KEY)
        genai_errors = _genai_errors
        logger.info("Gemini client initialised", extra={"event": "llm_init"})
    except Exception as exc:
        logger.warning("Failed to init Gemini: %s", exc, extra={"event": "llm_init", "error": str(exc)})
else:
    logger.info("No GEMINI_API_KEY - LLM disabled", extra={"event": "llm_init"})


def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db(max_retries: int = 30, delay: float = 1.0) -> None:
    for attempt in range(1, max_retries + 1):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    id                BIGSERIAL PRIMARY KEY,
                    user_message      TEXT      NOT NULL,
                    bot_response      TEXT      NOT NULL,
                    category          TEXT      NOT NULL,
                    timestamp         TEXT      NOT NULL,
                    response_time_ms  INTEGER   NOT NULL
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
            logger.info("DB ready (attempt %d)", attempt)
            return
        except psycopg2.OperationalError as exc:
            if attempt == max_retries:
                logger.error("DB unreachable after %d attempts: %s", max_retries, exc, extra={"event": "db_init", "error": str(exc)})
                raise
            time.sleep(delay)


def seed_if_empty() -> None:
    from seed_data import TRACES

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM traces")
    count = cur.fetchone()[0]
    if count >= len(TRACES):
        logger.info("Seed skipped (%d traces exist)", count)
        cur.close()
        conn.close()
        return

    import random

    now = datetime.datetime.utcnow()
    for t in TRACES:
        offset_hours = random.randint(0, 30 * 24)
        ts = (now - datetime.timedelta(hours=offset_hours)).isoformat(timespec="seconds") + "Z"
        cur.execute(
            """INSERT INTO traces
                   (user_message, bot_response, category, timestamp, response_time_ms)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                t["user_message"],
                t["bot_response"],
                json.dumps(t["categories"]),
                ts,
                t["response_time_ms"],
            ),
        )
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Seeded %d traces", len(TRACES))



_start_time: float = time.time()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_if_empty()
    yield


app = FastAPI(title="SupportLens API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    request_id = str(uuid.uuid4())
    start = time.time()
    response: Response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    logger.info(
        "%s %s %d %dms",
        request.method, request.url.path, response.status_code, duration_ms,
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response


_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "PROMPT.md")
COMBINED_PROMPT_TEMPLATE = open(_PROMPT_PATH).read().strip()

FALLBACK_REPLY = "I'm sorry, the AI assistant is temporarily unavailable."


def generate_chat_and_classify(user_message: str) -> tuple[str, list[str], int, bool]:
    if gemini is None:
        logger.warning("LLM unavailable, using fallback", extra={"event": "llm_fallback"})
        return FALLBACK_REPLY, ["Error"], 0, True

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
    except Exception as exc:
        elapsed_ms = int((time.time() - t0) * 1000)
        logger.error(
            "LLM failed (%dms): %s", elapsed_ms, exc,
            extra={"event": "llm_error", "error": str(exc), "duration_ms": elapsed_ms},
        )
        return FALLBACK_REPLY, ["Error"], elapsed_ms, True

    elapsed_ms = int((time.time() - t0) * 1000)
    data = json.loads(resp.text)
    reply = data.get("reply", "").strip()
    raw = data.get("categories", ["General Inquiry"])
    cats = list(dict.fromkeys(c for c in raw if c in CATEGORIES))[:2] or ["General Inquiry"]

    logger.info(
        "LLM ok %dms cats=%s", elapsed_ms, cats,
        extra={"event": "llm_call", "duration_ms": elapsed_ms},
    )
    return reply, cats, elapsed_ms, False


class ChatRequest(BaseModel):
    message: str


class TraceCreate(BaseModel):
    user_message: str
    bot_response: str
    response_time_ms: int
    categories: list[str] = ["General Inquiry"]


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Service is unhealthy - chat is temporarily unavailable.",
        )

    reply, categories, response_time_ms, is_fallback = generate_chat_and_classify(req.message)

    # Auto-save every interaction as a trace
    ts = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO traces
                   (user_message, bot_response, category, timestamp, response_time_ms)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id""",
            (req.message, reply, json.dumps(categories), ts, response_time_ms),
        )
        trace_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        logger.error("Auto-save trace failed: %s", exc, extra={"event": "db_error", "error": str(exc)})
        trace_id = None

    return {
        "response": reply,
        "categories": categories,
        "response_time_ms": response_time_ms,
        "is_fallback": is_fallback,
        "trace_id": trace_id,
    }


@app.post("/traces", status_code=201)
def create_trace(req: TraceCreate):
    cats = list(dict.fromkeys(c for c in req.categories if c in CATEGORIES))[:2] or ["General Inquiry"]
    trace = {
        "user_message": req.user_message,
        "bot_response": req.bot_response,
        "categories": cats,
        "timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "response_time_ms": req.response_time_ms,
    }
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO traces
                   (user_message, bot_response, category, timestamp, response_time_ms)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id""",
            (
                trace["user_message"],
                trace["bot_response"],
                json.dumps(cats),
                trace["timestamp"],
                trace["response_time_ms"],
            ),
        )
        trace["id"] = cur.fetchone()[0]
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("Insert failed: %s", exc, extra={"event": "db_error", "error": str(exc)})
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cur.close()
        conn.close()
    return trace


def _row_to_dict(row: dict) -> dict:
    d = dict(row)
    d["categories"] = json.loads(d.pop("category"))
    return d


@app.get("/traces")
def get_traces(category: Optional[str] = Query(default=None)):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if category:
            cur.execute(
                "SELECT * FROM traces WHERE category LIKE %s ORDER BY timestamp DESC",
                (f'%"{category}"%',),
            )
        else:
            cur.execute("SELECT * FROM traces ORDER BY timestamp DESC")
        rows = cur.fetchall()
    except Exception as exc:
        logger.error("Fetch traces failed: %s", exc, extra={"event": "db_error", "error": str(exc)})
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cur.close()
        conn.close()
    return [_row_to_dict(r) for r in rows]


@app.get("/analytics")
def get_analytics():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT COUNT(*) AS cnt FROM traces")
        total = cur.fetchone()["cnt"]
        cur.execute("SELECT AVG(response_time_ms) AS avg_rt FROM traces")
        avg_rt = cur.fetchone()["avg_rt"] or 0.0
        cur.execute("SELECT category FROM traces")
        cat_rows = cur.fetchall()
    except Exception as exc:
        logger.error("Analytics failed: %s", exc, extra={"event": "db_error", "error": str(exc)})
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cur.close()
        conn.close()

    counts: dict[str, int] = {cat: 0 for cat in CATEGORIES}
    for row in cat_rows:
        for cat in json.loads(row["category"]):
            if cat in counts:
                counts[cat] += 1

    total_hits = sum(counts.values()) or 1
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


@app.get("/health")
def health():
    checks: dict = {}
    overall = "healthy"

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        checks["database"] = {"status": "up"}
    except Exception as exc:
        checks["database"] = {"status": "down", "error": str(exc)}
        overall = "unhealthy"

    if GEMINI_API_KEY and gemini is not None:
        checks["llm"] = {
            "status": "configured",
            "detail": "API key present, client initialised",
        }
    elif GEMINI_API_KEY and gemini is None:
        checks["llm"] = {
            "status": "error",
            "detail": "API key present but client failed to initialise",
        }
        if overall != "unhealthy":
            overall = "degraded"
    else:
        checks["llm"] = {
            "status": "unconfigured",
            "detail": ("No API key - /chat returns fallback responses; " "traces and analytics are fully functional"),
        }
        if overall != "unhealthy":
            overall = "degraded"

    uptime_seconds = int(time.time() - _start_time)

    return {
        "status": overall,
        "uptime_seconds": uptime_seconds,
        "checks": checks,
    }
