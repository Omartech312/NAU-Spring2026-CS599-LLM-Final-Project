"""
Analytics service using SQLite.

Stores detailed per-operation logs for analytics dashboards:
- Embedding API calls (timing, cost, errors)
- LLM call logs (per-model, per-call)
- Query pipeline phase timing
- Voting/selection metrics
- Citation analytics
- Document processing metrics
- User activity tracking
- API cost estimation
- System health / fallback events
"""
import os
import json
import time
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from contextlib import contextmanager

from app.config import Config


def _db_path() -> str:
    """Return path to analytics SQLite DB."""
    db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "analytics.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    if row is None:
        return None
    return dict(row)


@contextmanager
def _conn_ctx():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema initialization
# ---------------------------------------------------------------------------

def init_analytics_db():
    """Create all analytics tables and indexes if they don't exist."""
    schema = """
    -- 1. Embedding API calls
    CREATE TABLE IF NOT EXISTS embedding_logs (
        id              TEXT PRIMARY KEY,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        call_type       TEXT NOT NULL,
        input_text_len  INTEGER,
        model           TEXT,
        latency_ms      REAL,
        tokens_used     INTEGER,
        success         INTEGER NOT NULL,
        error_message   TEXT,
        document_id     TEXT,
        user_id         TEXT,
        api_provider    TEXT DEFAULT 'openai'
    );

    -- 2. Raw LLM call logs
    CREATE TABLE IF NOT EXISTS llm_call_logs (
        id                  TEXT PRIMARY KEY,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        query_session_id    TEXT NOT NULL,
        model_provider      TEXT NOT NULL,
        model_name          TEXT NOT NULL,
        query_type          TEXT NOT NULL,
        context_chars       INTEGER,
        question_chars      INTEGER,
        latency_ms          REAL,
        input_tokens        INTEGER,
        output_tokens       INTEGER,
        total_tokens        INTEGER,
        answer_chars        INTEGER,
        success             INTEGER NOT NULL,
        error_type          TEXT,
        error_message       TEXT,
        citation_chunk_ids   TEXT,
        citation_count      INTEGER,
        retrieved_chunk_ids  TEXT,
        top_k               INTEGER,
        api_cost_estimate   REAL
    );

    -- 3. Query pipeline phase timing
    CREATE TABLE IF NOT EXISTS query_timing_logs (
        id                  TEXT PRIMARY KEY,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        query_session_id    TEXT NOT NULL,
        phase               TEXT NOT NULL,
        latency_ms          REAL NOT NULL,
        chunk_count         INTEGER,
        notes               TEXT
    );

    -- 4. Voting/selection analytics
    CREATE TABLE IF NOT EXISTS voting_logs (
        id                  TEXT PRIMARY KEY,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        query_session_id    TEXT NOT NULL,
        winning_model       TEXT NOT NULL,
        agreement_score     REAL,
        citation_overlap    REAL,
        combined_score      REAL,
        model_count         INTEGER,
        successful_models   TEXT,
        failed_models       TEXT,
        citation_chunk_count INTEGER,
        voting_weights      TEXT
    );

    -- 5. Citation analytics
    CREATE TABLE IF NOT EXISTS citation_analytics (
        id                  TEXT PRIMARY KEY,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        query_session_id    TEXT NOT NULL,
        document_id         TEXT NOT NULL,
        chunk_id            TEXT NOT NULL,
        page_number         INTEGER,
        cited_by_model      TEXT,
        cited_in_final      INTEGER DEFAULT 0
    );

    -- 6. Document processing analytics
    CREATE TABLE IF NOT EXISTS document_processing_logs (
        id                  TEXT PRIMARY KEY,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        document_id         TEXT NOT NULL,
        user_id             TEXT NOT NULL,
        file_type           TEXT NOT NULL,
        file_size_bytes     INTEGER,
        total_pages         INTEGER,
        total_chunks        INTEGER,
        extraction_ms       REAL,
        chunking_ms         REAL,
        embedding_ms        REAL,
        total_processing_ms REAL,
        status              TEXT NOT NULL,
        error_stage         TEXT,
        error_message       TEXT
    );

    -- 7. User activity tracking
    CREATE TABLE IF NOT EXISTS user_activity_logs (
        id                  TEXT PRIMARY KEY,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_id             TEXT NOT NULL,
        event_type          TEXT NOT NULL,
        document_id         TEXT,
        query_session_id    TEXT,
        session_id          TEXT,
        duration_ms         REAL
    );

    -- 8. API cost tracking
    CREATE TABLE IF NOT EXISTS api_cost_logs (
        id                  TEXT PRIMARY KEY,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_id             TEXT NOT NULL,
        api_provider        TEXT NOT NULL,
        cost_type           TEXT NOT NULL,
        model_name          TEXT,
        tokens              INTEGER,
        estimated_cost_usd  REAL,
        query_session_id    TEXT
    );

    -- 9. System health / fallbacks
    CREATE TABLE IF NOT EXISTS system_health_logs (
        id          TEXT PRIMARY KEY,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        event_type  TEXT NOT NULL,
        severity    TEXT NOT NULL,
        details     TEXT,
        resolved    INTEGER DEFAULT 0
    );
    """

    indexes = """
    CREATE INDEX IF NOT EXISTS ix_emb_created ON embedding_logs(created_at);
    CREATE INDEX IF NOT EXISTS ix_emb_document ON embedding_logs(document_id);
    CREATE INDEX IF NOT EXISTS ix_llm_session ON llm_call_logs(query_session_id);
    CREATE INDEX IF NOT EXISTS ix_llm_model ON llm_call_logs(model_provider, model_name);
    CREATE INDEX IF NOT EXISTS ix_llm_created ON llm_call_logs(created_at);
    CREATE INDEX IF NOT EXISTS ix_voting_session ON voting_logs(query_session_id);
    CREATE INDEX IF NOT EXISTS ix_citation_doc_page ON citation_analytics(document_id, page_number);
    CREATE INDEX IF NOT EXISTS ix_doc_proc_user ON document_processing_logs(user_id);
    CREATE INDEX IF NOT EXISTS ix_user_act_user ON user_activity_logs(user_id, created_at);
    CREATE INDEX IF NOT EXISTS ix_api_cost_user ON api_cost_logs(user_id, created_at);
    """

    with _conn_ctx() as conn:
        conn.executescript(schema)
        conn.executescript(indexes)


# ---------------------------------------------------------------------------
# Embedding log helpers
# ---------------------------------------------------------------------------

def log_embedding(
    call_type: str,
    success: bool,
    latency_ms: float = None,
    tokens_used: int = None,
    input_text_len: int = None,
    model: str = None,
    error_message: str = None,
    document_id: str = None,
    user_id: str = None,
    api_provider: str = "openai",
) -> str:
    """Log a single embedding API call (query or batch)."""
    log_id = str(uuid.uuid4())
    with _conn_ctx() as conn:
        conn.execute(
            """INSERT INTO embedding_logs
            (id, call_type, input_text_len, model, latency_ms, tokens_used,
             success, error_message, document_id, user_id, api_provider)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                log_id, call_type, input_text_len, model, latency_ms,
                tokens_used, int(success), error_message, document_id,
                user_id, api_provider,
            ),
        )
    return log_id


# ---------------------------------------------------------------------------
# LLM call log helpers
# ---------------------------------------------------------------------------

def log_llm_call(
    query_session_id: str,
    model_provider: str,
    model_name: str,
    query_type: str,
    success: bool,
    latency_ms: float = None,
    input_tokens: int = None,
    output_tokens: int = None,
    answer_chars: int = None,
    context_chars: int = None,
    question_chars: int = None,
    error_type: str = None,
    error_message: str = None,
    citation_chunk_ids: list = None,
    retrieved_chunk_ids: list = None,
    top_k: int = None,
    api_cost_estimate: float = None,
) -> str:
    """Log a raw LLM API call (before voting/selection)."""
    log_id = str(uuid.uuid4())
    with _conn_ctx() as conn:
        conn.execute(
            """INSERT INTO llm_call_logs
            (id, query_session_id, model_provider, model_name, query_type,
             context_chars, question_chars, latency_ms, input_tokens,
             output_tokens, total_tokens, answer_chars, success, error_type,
             error_message, citation_chunk_ids, citation_count,
             retrieved_chunk_ids, top_k, api_cost_estimate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                log_id, query_session_id, model_provider, model_name, query_type,
                context_chars, question_chars, latency_ms,
                input_tokens, output_tokens,
                (input_tokens or 0) + (output_tokens or 0),
                answer_chars, int(success), error_type, error_message,
                json.dumps(citation_chunk_ids or []),
                len(citation_chunk_ids) if citation_chunk_ids else 0,
                json.dumps(retrieved_chunk_ids or []),
                top_k, api_cost_estimate,
            ),
        )
    return log_id


# ---------------------------------------------------------------------------
# Query timing helpers
# ---------------------------------------------------------------------------

def log_query_phase(
    query_session_id: str,
    phase: str,
    latency_ms: float,
    chunk_count: int = None,
    notes: str = None,
) -> str:
    """Log timing for a specific phase of the query pipeline."""
    log_id = str(uuid.uuid4())
    with _conn_ctx() as conn:
        conn.execute(
            """INSERT INTO query_timing_logs
            (id, query_session_id, phase, latency_ms, chunk_count, notes)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (log_id, query_session_id, phase, latency_ms, chunk_count, notes),
        )
    return log_id


# ---------------------------------------------------------------------------
# Voting log helpers
# ---------------------------------------------------------------------------

def log_voting(
    query_session_id: str,
    winning_model: str,
    agreement_score: float = None,
    citation_overlap: float = None,
    combined_score: float = None,
    model_count: int = None,
    successful_models: list = None,
    failed_models: list = None,
    citation_chunk_count: int = None,
    voting_weights: dict = None,
) -> str:
    """Log voting/selection results."""
    log_id = str(uuid.uuid4())
    with _conn_ctx() as conn:
        conn.execute(
            """INSERT INTO voting_logs
            (id, query_session_id, winning_model, agreement_score,
             citation_overlap, combined_score, model_count,
             successful_models, failed_models, citation_chunk_count,
             voting_weights)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                log_id, query_session_id, winning_model, agreement_score,
                citation_overlap, combined_score, model_count,
                json.dumps(successful_models or []),
                json.dumps(failed_models or []),
                citation_chunk_count,
                json.dumps(voting_weights or {}),
            ),
        )
    return log_id


# ---------------------------------------------------------------------------
# Citation analytics helpers
# ---------------------------------------------------------------------------

def log_citation(
    query_session_id: str,
    document_id: str,
    chunk_id: str,
    page_number: int = None,
    cited_by_model: str = None,
    cited_in_final: bool = False,
) -> str:
    """Log a single citation event."""
    log_id = str(uuid.uuid4())
    with _conn_ctx() as conn:
        conn.execute(
            """INSERT INTO citation_analytics
            (id, query_session_id, document_id, chunk_id,
             page_number, cited_by_model, cited_in_final)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (log_id, query_session_id, document_id, chunk_id,
             page_number, cited_by_model, int(cited_in_final)),
        )
    return log_id


def log_citations_batch(
    query_session_id: str,
    document_id: str,
    citations: list,
    cited_in_final: bool = False,
) -> list:
    """Log multiple citations at once. citations = [{chunk_id, page_number, cited_by_model}, ...]"""
    log_ids = []
    for c in citations:
        log_ids.append(log_citation(
            query_session_id=query_session_id,
            document_id=document_id,
            chunk_id=c.get("chunk_id", ""),
            page_number=c.get("page_number"),
            cited_by_model=c.get("cited_by_model"),
            cited_in_final=cited_in_final,
        ))
    return log_ids


# ---------------------------------------------------------------------------
# Document processing log helpers
# ---------------------------------------------------------------------------

def log_document_processing(
    document_id: str,
    user_id: str,
    file_type: str,
    file_size_bytes: int = None,
    total_pages: int = None,
    total_chunks: int = None,
    extraction_ms: float = None,
    chunking_ms: float = None,
    embedding_ms: float = None,
    total_processing_ms: float = None,
    status: str = "success",
    error_stage: str = None,
    error_message: str = None,
) -> str:
    """Log document processing pipeline metrics."""
    log_id = str(uuid.uuid4())
    with _conn_ctx() as conn:
        conn.execute(
            """INSERT INTO document_processing_logs
            (id, document_id, user_id, file_type, file_size_bytes,
             total_pages, total_chunks, extraction_ms, chunking_ms,
             embedding_ms, total_processing_ms, status, error_stage, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                log_id, document_id, user_id, file_type, file_size_bytes,
                total_pages, total_chunks, extraction_ms, chunking_ms,
                embedding_ms, total_processing_ms, status, error_stage, error_message,
            ),
        )
    return log_id


# ---------------------------------------------------------------------------
# User activity helpers
# ---------------------------------------------------------------------------

def log_user_activity(
    user_id: str,
    event_type: str,
    document_id: str = None,
    query_session_id: str = None,
    session_id: str = None,
    duration_ms: float = None,
) -> str:
    """Log user interaction events."""
    log_id = str(uuid.uuid4())
    with _conn_ctx() as conn:
        conn.execute(
            """INSERT INTO user_activity_logs
            (id, user_id, event_type, document_id, query_session_id, session_id, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (log_id, user_id, event_type, document_id, query_session_id, session_id, duration_ms),
        )
    return log_id


# ---------------------------------------------------------------------------
# API cost helpers
# ---------------------------------------------------------------------------

# Rough cost estimates per 1M tokens (USD)
LLM_COST_PER_M = {
    # Provider / model: (input_cost_per_1M, output_cost_per_1M)
    "openai/gpt-4o": (2.50, 10.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "anthropic/claude-3-5-sonnet": (3.00, 15.00),
    "anthropic/claude-3-5-sonnet-20240620": (3.00, 15.00),
    "google/gemini-1.5-flash": (0.075, 0.30),
    "google/gemini-1.5-pro": (1.25, 5.00),
    "codex/gpt-5.2": (2.50, 10.00),  # Codex uses OpenAI pricing
    # Claude CLI (billed to user's Anthropic account)
    "claude/claude-opus-4-6": (15.00, 75.00),
    "claude/claude-sonnet-4": (3.00, 15.00),
    "claude/opus": (15.00, 75.00),
    "claude/sonnet": (3.00, 15.00),
}

EMBEDDING_COST_PER_1K = 0.00002  # OpenAI text-embedding-3-small: $0.02/1M tokens


def estimate_llm_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    costs = LLM_COST_PER_M.get(model_name, (0.0, 0.0))
    return (input_tokens / 1_000_000) * costs[0] + (output_tokens / 1_000_000) * costs[1]


def estimate_embedding_cost(tokens: int) -> float:
    return (tokens / 1000) * EMBEDDING_COST_PER_1K


def log_api_cost(
    user_id: str,
    api_provider: str,
    cost_type: str,
    tokens: int,
    estimated_cost_usd: float,
    model_name: str = None,
    query_session_id: str = None,
) -> str:
    """Log API usage cost."""
    log_id = str(uuid.uuid4())
    with _conn_ctx() as conn:
        conn.execute(
            """INSERT INTO api_cost_logs
            (id, user_id, api_provider, cost_type, model_name, tokens, estimated_cost_usd, query_session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (log_id, user_id, api_provider, cost_type, model_name, tokens, estimated_cost_usd, query_session_id),
        )
    return log_id


# ---------------------------------------------------------------------------
# System health helpers
# ---------------------------------------------------------------------------

def log_system_health(
    event_type: str,
    severity: str,
    details: dict = None,
) -> str:
    """Log system health events (fallbacks, errors, etc.)."""
    log_id = str(uuid.uuid4())
    with _conn_ctx() as conn:
        conn.execute(
            """INSERT INTO system_health_logs (id, event_type, severity, details)
            VALUES (?, ?, ?, ?)""",
            (log_id, event_type, severity, json.dumps(details) if details else None),
        )
    return log_id


# ---------------------------------------------------------------------------
# Analytics query helpers (for dashboards)
# ---------------------------------------------------------------------------

def get_user_summary(user_id: str, days: int = 30) -> dict:
    """Get analytics summary for a user over N days."""
    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

    with _conn_ctx() as conn:
        # Query counts
        uploads = conn.execute(
            """SELECT COUNT(*) FROM document_processing_logs
               WHERE user_id = ? AND created_at >= ? AND status = 'success'""",
            (user_id, cutoff_dt)
        ).fetchone()[0]

        queries = conn.execute(
            """SELECT COUNT(DISTINCT query_session_id) FROM llm_call_logs
               WHERE query_session_id IN (
                   SELECT query_session_id FROM llm_call_logs
                   WHERE query_session_id IN (
                       SELECT id FROM query_sessions_subq WHERE user_id = ?
                   ) AND created_at >= ?
               )""",
            (user_id, cutoff_dt)
        ).fetchone()[0]

        # This subquery approach is awkward - let's do simpler
        queries = conn.execute(
            """SELECT COUNT(*) FROM llm_call_logs
               WHERE query_session_id IN (
                   SELECT query_session_id FROM query_timing_logs WHERE created_at >= ?
               )""",
            (cutoff_dt,)
        ).fetchone()[0]

        total_cost = conn.execute(
            """SELECT COALESCE(SUM(estimated_cost_usd), 0) FROM api_cost_logs
               WHERE user_id = ? AND created_at >= ?""",
            (user_id, cutoff_dt)
        ).fetchone()[0]

        avg_latency = conn.execute(
            """SELECT COALESCE(AVG(latency_ms), 0) FROM llm_call_logs
               WHERE success = 1 AND created_at >= ?""",
            (cutoff_dt,)
        ).fetchone()[0]

        model_usage = conn.execute(
            """SELECT model_provider, model_name, COUNT(*) as calls
               FROM llm_call_logs WHERE created_at >= ?
               GROUP BY model_provider, model_name
               ORDER BY calls DESC LIMIT 10""",
            (cutoff_dt,)
        ).fetchall()

        return {
            "user_id": user_id,
            "period_days": days,
            "documents_uploaded": uploads,
            "queries_asked": queries,
            "estimated_cost_usd": round(total_cost, 6),
            "avg_llm_latency_ms": round(avg_latency, 2),
            "model_usage": [_row_to_dict(r) for r in model_usage],
        }


def get_system_health_summary(days: int = 7) -> dict:
    """Get system health summary."""
    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

    with _conn_ctx() as conn:
        events = conn.execute(
            """SELECT event_type, severity, COUNT(*) as count
               FROM system_health_logs WHERE created_at >= ?
               GROUP BY event_type, severity ORDER BY count DESC""",
            (cutoff_dt,)
        ).fetchall()

        unresolved = conn.execute(
            """SELECT COUNT(*) FROM system_health_logs
               WHERE resolved = 0 AND created_at >= ?""",
            (cutoff_dt,)
        ).fetchone()[0]

        return {
            "period_days": days,
            "total_events": sum(r["count"] for r in events),
            "unresolved_events": unresolved,
            "events_by_type": [_row_to_dict(r) for r in events],
        }


# ---------------------------------------------------------------------------
# Auto-init on import
# ---------------------------------------------------------------------------
init_analytics_db()
