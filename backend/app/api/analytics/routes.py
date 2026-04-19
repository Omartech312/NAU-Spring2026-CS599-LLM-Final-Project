"""
Analytics API endpoints.
Serves data from the SQLite analytics database.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone, timedelta
import sqlite3

from app.services.analytics_service import _db_path

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


def _conn():
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _row(row):
    if row is None:
        return None
    return dict(row)


def _rows(rows):
    return [_row(r) for r in rows]


@analytics_bp.route("/overview", methods=["GET"])
@jwt_required()
def get_overview():
    """
    High-level analytics overview for the current user.
    """
    user_id = get_jwt_identity()
    days = request.args.get("days", 30, type=int)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    conn = _conn()
    cur = conn.cursor()

    try:
        # Uploads
        cur.execute(
            """SELECT COUNT(*) as count FROM document_processing_logs
               WHERE user_id = ? AND status = 'success' AND created_at >= ?""",
            (user_id, cutoff_str),
        )
        total_uploads = cur.fetchone()["count"]

        # Total queries
        cur.execute(
            """SELECT COUNT(*) as count FROM llm_call_logs
               WHERE query_session_id IN (
                   SELECT DISTINCT query_session_id FROM query_timing_logs
                   WHERE created_at >= ?
               )""",
            (cutoff_str,),
        )
        total_queries = cur.fetchone()["count"]

        # Total cost
        cur.execute(
            """SELECT COALESCE(SUM(estimated_cost_usd), 0) as total FROM api_cost_logs
               WHERE user_id = ? AND created_at >= ?""",
            (user_id, cutoff_str),
        )
        total_cost = round(cur.fetchone()["total"], 6)

        # Avg LLM latency
        cur.execute(
            """SELECT COALESCE(AVG(latency_ms), 0) as avg FROM llm_call_logs
               WHERE success = 1 AND created_at >= ?""",
            (cutoff_str,),
        )
        avg_llm_latency = round(cur.fetchone()["avg"], 2)

        # Successful vs failed queries
        cur.execute(
            """SELECT
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                   SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
               FROM llm_call_logs WHERE created_at >= ?""",
            (cutoff_str,),
        )
        row = cur.fetchone()
        successful_calls = row["successful"]
        failed_calls = row["failed"]

        return jsonify({
            "period_days": days,
            "total_uploads": total_uploads,
            "total_queries": total_queries,
            "total_cost_usd": total_cost,
            "avg_llm_latency_ms": avg_llm_latency,
            "successful_llm_calls": successful_calls,
            "failed_llm_calls": failed_calls,
        }), 200

    finally:
        conn.close()


@analytics_bp.route("/cost", methods=["GET"])
@jwt_required()
def get_cost_breakdown():
    """
    API cost breakdown by provider and model.
    """
    user_id = get_jwt_identity()
    days = request.args.get("days", 30, type=int)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    conn = _conn()
    cur = conn.cursor()

    try:
        # By provider
        cur.execute(
            """SELECT api_provider, cost_type,
                      COALESCE(SUM(tokens), 0) as total_tokens,
                      COALESCE(SUM(estimated_cost_usd), 0) as total_cost
               FROM api_cost_logs
               WHERE user_id = ? AND created_at >= ?
               GROUP BY api_provider, cost_type
               ORDER BY total_cost DESC""",
            (user_id, cutoff_str),
        )
        by_provider = _rows(cur.fetchall())

        # Daily cost trend
        cur.execute(
            """SELECT DATE(created_at) as date,
                      COALESCE(SUM(estimated_cost_usd), 0) as cost,
                      COALESCE(SUM(tokens), 0) as tokens
               FROM api_cost_logs
               WHERE user_id = ? AND created_at >= ?
               GROUP BY DATE(created_at)
               ORDER BY date ASC""",
            (user_id, cutoff_str),
        )
        daily = _rows(cur.fetchall())

        # By model
        cur.execute(
            """SELECT model_name, api_provider,
                      COALESCE(SUM(tokens), 0) as total_tokens,
                      COALESCE(SUM(estimated_cost_usd), 0) as total_cost,
                      COUNT(*) as call_count
               FROM api_cost_logs
               WHERE user_id = ? AND created_at >= ?
               GROUP BY model_name, api_provider
               ORDER BY total_cost DESC
               LIMIT 20""",
            (user_id, cutoff_str),
        )
        by_model = _rows(cur.fetchall())

        return jsonify({
            "by_provider": by_provider,
            "daily": daily,
            "by_model": by_model,
        }), 200

    finally:
        conn.close()


@analytics_bp.route("/model-performance", methods=["GET"])
@jwt_required()
def get_model_performance():
    """
    Model performance: latency, success rate, usage count.
    """
    user_id = get_jwt_identity()
    days = request.args.get("days", 30, type=int)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    conn = _conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """SELECT
                   model_provider,
                   model_name,
                   COUNT(*) as call_count,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                   SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_calls,
                   ROUND(100.0 * SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate,
                   ROUND(COALESCE(AVG(CASE WHEN success = 1 THEN latency_ms END), 0), 2) as avg_latency_ms,
                   ROUND(COALESCE(MAX(latency_ms), 0), 2) as max_latency_ms,
                   ROUND(COALESCE(AVG(answer_chars), 0), 0) as avg_answer_chars
               FROM llm_call_logs
               WHERE created_at >= ?
               GROUP BY model_provider, model_name
               ORDER BY call_count DESC""",
            (cutoff_str,),
        )
        rows = _rows(cur.fetchall())

        return jsonify({"models": rows}), 200

    finally:
        conn.close()


@analytics_bp.route("/processing", methods=["GET"])
@jwt_required()
def get_processing_metrics():
    """
    Document processing analytics: timing, file types, failures.
    """
    user_id = get_jwt_identity()
    days = request.args.get("days", 30, type=int)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    conn = _conn()
    cur = conn.cursor()

    try:
        # By file type
        cur.execute(
            """SELECT file_type,
                      COUNT(*) as count,
                      ROUND(AVG(total_pages), 1) as avg_pages,
                      ROUND(AVG(total_chunks), 1) as avg_chunks,
                      ROUND(AVG(extraction_ms), 2) as avg_extraction_ms,
                      ROUND(AVG(chunking_ms), 2) as avg_chunking_ms,
                      ROUND(AVG(embedding_ms), 2) as avg_embedding_ms,
                      ROUND(AVG(total_processing_ms), 2) as avg_total_ms
               FROM document_processing_logs
               WHERE user_id = ? AND status = 'success' AND created_at >= ?
               GROUP BY file_type""",
            (user_id, cutoff_str),
        )
        by_type = _rows(cur.fetchall())

        # Errors
        cur.execute(
            """SELECT error_stage, error_message, COUNT(*) as count
               FROM document_processing_logs
               WHERE user_id = ? AND status = 'error' AND created_at >= ?
               GROUP BY error_stage, error_message
               ORDER BY count DESC""",
            (user_id, cutoff_str),
        )
        errors = _rows(cur.fetchall())

        # Recent processing
        cur.execute(
            """SELECT document_id, file_type, total_pages, total_chunks,
                      extraction_ms, chunking_ms, embedding_ms, total_processing_ms,
                      created_at
               FROM document_processing_logs
               WHERE user_id = ? AND created_at >= ?
               ORDER BY created_at DESC
               LIMIT 20""",
            (user_id, cutoff_str),
        )
        recent = _rows(cur.fetchall())

        return jsonify({
            "by_file_type": by_type,
            "errors": errors,
            "recent": recent,
        }), 200

    finally:
        conn.close()


@analytics_bp.route("/query-timeline", methods=["GET"])
@jwt_required()
def get_query_timeline():
    """
    Query pipeline timing breakdown per session.
    """
    days = request.args.get("days", 30, type=int)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    conn = _conn()
    cur = conn.cursor()

    try:
        # Phase breakdown per session
        cur.execute(
            """SELECT
                   query_session_id,
                   phase,
                   ROUND(AVG(latency_ms), 2) as avg_ms,
                   ROUND(MIN(latency_ms), 2) as min_ms,
                   ROUND(MAX(latency_ms), 2) as max_ms,
                   COUNT(*) as call_count
               FROM query_timing_logs
               WHERE created_at >= ?
               GROUP BY query_session_id, phase
               ORDER BY query_session_id DESC
               LIMIT 200""",
            (cutoff_str,),
        )
        sessions = _rows(cur.fetchall())

        # Aggregate phase averages
        cur.execute(
            """SELECT phase,
                      ROUND(AVG(latency_ms), 2) as avg_ms,
                      ROUND(MIN(latency_ms), 2) as min_ms,
                      ROUND(MAX(latency_ms), 2) as max_ms,
                      COUNT(*) as count
               FROM query_timing_logs
               WHERE created_at >= ?
               GROUP BY phase
               ORDER BY avg_ms DESC""",
            (cutoff_str,),
        )
        aggregates = _rows(cur.fetchall())

        return jsonify({
            "sessions": sessions,
            "aggregates": aggregates,
        }), 200

    finally:
        conn.close()


@analytics_bp.route("/voting", methods=["GET"])
@jwt_required()
def get_voting_stats():
    """
    Voting/answer quality analytics.
    """
    days = request.args.get("days", 30, type=int)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    conn = _conn()
    cur = conn.cursor()

    try:
        # Win rate by model
        cur.execute(
            """SELECT winning_model,
                      COUNT(*) as win_count,
                      ROUND(AVG(agreement_score), 3) as avg_agreement,
                      ROUND(AVG(citation_overlap), 3) as avg_citation_overlap,
                      ROUND(AVG(combined_score), 3) as avg_combined_score,
                      ROUND(AVG(citation_chunk_count), 1) as avg_citation_chunks
               FROM voting_logs
               WHERE created_at >= ?
               GROUP BY winning_model
               ORDER BY win_count DESC""",
            (cutoff_str,),
        )
        win_rates = _rows(cur.fetchall())

        # Agreement distribution
        cur.execute(
            """SELECT
                   CASE
                     WHEN agreement_score = 1.0 THEN '1.0 (perfect)'
                     WHEN agreement_score >= 0.8 THEN '0.8-0.99'
                     WHEN agreement_score >= 0.5 THEN '0.5-0.79'
                     WHEN agreement_score >= 0.2 THEN '0.2-0.49'
                     ELSE '< 0.2'
                   END as bucket,
                   COUNT(*) as count
               FROM voting_logs
               WHERE created_at >= ?
               GROUP BY bucket
               ORDER BY bucket DESC""",
            (cutoff_str,),
        )
        agreement_dist = _rows(cur.fetchall())

        return jsonify({
            "win_rates": win_rates,
            "agreement_distribution": agreement_dist,
        }), 200

    finally:
        conn.close()


@analytics_bp.route("/citations", methods=["GET"])
@jwt_required()
def get_citation_stats():
    """
    Citation analytics: most-cited pages/chunks.
    """
    user_id = get_jwt_identity()
    days = request.args.get("days", 30, type=int)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    conn = _conn()
    cur = conn.cursor()

    try:
        # Most cited pages
        cur.execute(
            """SELECT page_number, document_id,
                      COUNT(*) as citation_count,
                      SUM(CASE WHEN cited_in_final = 1 THEN 1 ELSE 0 END) as final_citations
               FROM citation_analytics
               WHERE query_session_id IN (
                   SELECT DISTINCT query_session_id FROM query_timing_logs
                   WHERE created_at >= ?
               )
               GROUP BY page_number, document_id
               ORDER BY citation_count DESC
               LIMIT 20""",
            (cutoff_str,),
        )
        page_stats = _rows(cur.fetchall())

        # Citations per model
        cur.execute(
            """SELECT cited_by_model, COUNT(*) as count
               FROM citation_analytics
               WHERE cited_by_model IS NOT NULL
               AND query_session_id IN (
                   SELECT DISTINCT query_session_id FROM query_timing_logs
                   WHERE created_at >= ?
               )
               GROUP BY cited_by_model
               ORDER BY count DESC""",
            (cutoff_str,),
        )
        by_model = _rows(cur.fetchall())

        return jsonify({
            "most_cited_pages": page_stats,
            "citations_by_model": by_model,
        }), 200

    finally:
        conn.close()
