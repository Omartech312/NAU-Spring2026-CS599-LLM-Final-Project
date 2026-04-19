import uuid
import time as time_module
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Document, DocumentChunk, QuerySession, LLMResult, FinalAnswer
from app.services.embedding_service import generate_embedding
from app.services.vector_service import search_similar_chunks, build_context_from_chunks
from app.services.llm_service import query_all_models
from app.services.voting_service import vote_and_select
from app.services.analytics_service import (
    log_embedding,
    log_llm_call,
    log_query_phase,
    log_voting,
    log_citations_batch,
    log_api_cost,
    estimate_llm_cost,
    estimate_embedding_cost,
    log_system_health,
    log_user_activity,
)

queries_bp = Blueprint("queries", __name__)


@queries_bp.route("/qa", methods=["POST"])
@jwt_required()
def ask_question():
    """
    Ask a question about a document.
    1. Generate query embedding
    2. Retrieve relevant chunks
    3. Query all LLM models
    4. Vote and select best answer
    5. Return answer with citations
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    document_id = data.get("document_id")
    question = data.get("question", "").strip()
    top_k = data.get("top_k", current_app.config.get("TOP_K", 5))

    if not document_id:
        return jsonify({"error": "document_id is required"}), 400
    if not question:
        return jsonify({"error": "question is required"}), 400

    # Verify document access
    document = Document.query.filter_by(id=document_id, user_id=user_id).first()
    if not document:
        return jsonify({"error": "Document not found"}), 404
    if document.status != "ready":
        return jsonify({"error": f"Document is not ready (status: {document.status})"}), 400

    overall_start = time_module.time()

    # Pre-create query session so we have a stable ID for analytics
    query_session = QuerySession(
        user_id=user_id,
        document_id=document_id,
        query_text=question,
        query_type="qa",
        retrieved_chunk_ids=[],  # will be updated below
    )
    db.session.add(query_session)
    db.session.commit()  # now query_session.id is stable
    query_session_id = str(query_session.id)

    # Step 1: Generate query embedding
    embedding_start = time_module.time()
    embedding_success = False
    embedding_error = None
    query_embedding = None
    try:
        query_embedding = generate_embedding(question)
        embedding_success = True
    except Exception as emb_err:
        embedding_error = str(emb_err)
        log_system_health(
            event_type="embedding_error",
            severity="error",
            details={"query_session_id": query_session_id, "error": embedding_error},
        )

    embedding_ms = (time_module.time() - embedding_start) * 1000

    log_embedding(
        call_type="query",
        success=embedding_success,
        latency_ms=embedding_ms,
        input_text_len=len(question),
        model=current_app.config.get("EMBEDDING_MODEL", "text-embedding-3-small"),
        error_message=embedding_error,
        document_id=str(document_id),
        user_id=str(user_id),
        api_provider="openai",
    )

    if not embedding_success:
        return jsonify({
            "error": f"Query embedding failed: {embedding_error}",
            "question": question,
        }), 200

    # Step 2: Search for relevant chunks
    search_start = time_module.time()
    try:
        chunks = search_similar_chunks(
            query_embedding=query_embedding,
            document_id=str(document_id),
            top_k=top_k,
            db_session=db.session,
        )
    except Exception as search_err:
        chunks = []
        log_system_health(
            event_type="vector_search_error",
            severity="error",
            details={"query_session_id": query_session_id, "error": str(search_err)},
        )
    search_ms = (time_module.time() - search_start) * 1000

    log_query_phase(
        query_session_id=query_session_id,
        phase="embedding",
        latency_ms=embedding_ms,
        chunk_count=len(chunks),
        notes=f"top_k={top_k}",
    )
    log_query_phase(
        query_session_id=query_session_id,
        phase="vector_search",
        latency_ms=search_ms,
        chunk_count=len(chunks),
    )

    if not chunks:
        return jsonify({
            "error": "No relevant content found in document",
            "question": question,
        }), 200

    retrieved_chunk_ids = [c["id"] for c in chunks]
    context = build_context_from_chunks(chunks)
    context_chars = len(context)

    # Step 3: Query all LLM models
    llm_start = time_module.time()
    config = {
        "OPENAI_API_KEY": current_app.config.get("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": current_app.config.get("ANTHROPIC_API_KEY"),
        "GOOGLE_API_KEY": current_app.config.get("GOOGLE_API_KEY"),
        "OPENAI_MODEL": current_app.config.get("OPENAI_MODEL"),
        "ANTHROPIC_MODEL": current_app.config.get("ANTHROPIC_MODEL"),
        "GOOGLE_MODEL": current_app.config.get("GOOGLE_MODEL"),
    }

    llm_results = query_all_models(
        context=context,
        question=question,
        query_type="qa",
        config=config,
    )
    llm_ms = (time_module.time() - llm_start) * 1000

    # Log each LLM call
    for result in llm_results:
        provider = result.get("model_name", "").split("/")[0] if "/" in result.get("model_name", "") else "unknown"
        error_type = None
        if not result.get("success"):
            err_msg = result.get("error", "")
            if "API key" in str(err_msg):
                error_type = "api_missing"
            elif "timeout" in str(err_msg).lower():
                error_type = "timeout"
            elif "rate limit" in str(err_msg).lower():
                error_type = "rate_limit"
            else:
                error_type = "other"

        # Extract cited chunk IDs
        cited_ids = extract_cited_from_result(result, chunks)

        log_llm_call(
            query_session_id=query_session_id,
            model_provider=provider,
            model_name=result.get("model_name", "unknown"),
            query_type="qa",
            success=result.get("success", False),
            latency_ms=result.get("latency_ms"),
            input_tokens=result.get("input_tokens") or 0,
            output_tokens=result.get("output_tokens") or 0,
            answer_chars=len(result.get("answer_text", "")),
            context_chars=context_chars,
            question_chars=len(question),
            error_type=error_type,
            error_message=result.get("error"),
            citation_chunk_ids=cited_ids,
            retrieved_chunk_ids=retrieved_chunk_ids,
            top_k=top_k,
            api_cost_estimate=0.0,  # Cost computed below
        )

        # Log API cost if successful
        if result.get("success") and result.get("tokens_used", 0) > 0:
            tokens_used = result.get("tokens_used", 0)
            cost = estimate_llm_cost(result.get("model_name", ""), tokens_used, 0)
            if cost > 0:
                log_api_cost(
                    user_id=str(user_id),
                    api_provider=provider,
                    cost_type="llm_output",
                    tokens=tokens_used,
                    estimated_cost_usd=cost,
                    model_name=result.get("model_name"),
                    query_session_id=query_session_id,
                )

    log_query_phase(
        query_session_id=query_session_id,
        phase="llm_calls",
        latency_ms=llm_ms,
        chunk_count=len(chunks),
        notes=f"models={len(llm_results)}, successful={sum(1 for r in llm_results if r.get('success'))}",
    )

    # Update query session with actual chunk IDs
    query_session.retrieved_chunk_ids = retrieved_chunk_ids
    db.session.commit()

    # Save LLM results to main DB
    result_objects = []
    for llm_result in llm_results:
        result_obj = LLMResult(
            query_session_id=query_session.id,
            model_name=llm_result["model_name"],
            answer_text=llm_result["answer_text"],
            cited_chunk_ids=extract_cited_from_result(llm_result, chunks),
            latency_ms=llm_result.get("latency_ms", 0),
            tokens_used=llm_result.get("tokens_used", 0),
        )
        db.session.add(result_obj)
        result_objects.append(result_obj)
    db.session.commit()

    # Step 4: Voting mechanism
    voting_start = time_module.time()
    voting_result = vote_and_select(
        llm_results=[
            {
                **r,
                "cited_chunk_ids": extract_cited_from_result(r, chunks),
            }
            for r in llm_results
        ],
        retrieved_chunks=chunks,
    )
    voting_ms = (time_module.time() - voting_start) * 1000
    overall_ms = (time_module.time() - overall_start) * 1000

    # Log voting
    successful_models = [r.get("model_name") for r in llm_results if r.get("success")]
    failed_models = [r.get("model_name") for r in llm_results if not r.get("success")]
    log_voting(
        query_session_id=str(query_session.id),
        winning_model=voting_result.get("winning_model", "unknown"),
        agreement_score=voting_result.get("agreement_score"),
        citation_overlap=voting_result.get("citation_overlap"),
        combined_score=voting_result.get("combined_score"),
        model_count=len(llm_results),
        successful_models=successful_models,
        failed_models=failed_models,
        citation_chunk_count=len(voting_result.get("citation_chunk_ids", [])),
        voting_weights={"agreement": 0.5, "citation_overlap": 0.5},
    )

    log_query_phase(
        query_session_id=str(query_session.id),
        phase="voting",
        latency_ms=voting_ms,
        chunk_count=len(chunks),
    )
    log_query_phase(
        query_session_id=str(query_session.id),
        phase="total",
        latency_ms=overall_ms,
        chunk_count=len(chunks),
    )

    # Log citations
    citation_list = [
        {
            "chunk_id": c["id"],
            "page_number": c.get("page_number"),
            "cited_by_model": voting_result.get("winning_model"),
        }
        for c in chunks
        if c["id"] in voting_result.get("citation_chunk_ids", [])
    ]
    log_citations_batch(
        query_session_id=str(query_session.id),
        document_id=str(document_id),
        citations=citation_list,
        cited_in_final=True,
    )

    # Step 5: Save final answer
    final_answer = FinalAnswer(
        query_session_id=query_session.id,
        answer_text=voting_result.get("answer_text", ""),
        citation_chunk_ids=voting_result.get("citation_chunk_ids", []),
        winning_model=voting_result.get("winning_model", "unknown"),
        agreement_score=voting_result.get("agreement_score", 0),
        citation_overlap=voting_result.get("citation_overlap", 0),
    )
    db.session.add(final_answer)
    db.session.commit()

    # Get citation details
    citation_chunks = []
    chunk_map = {str(c["id"]): c for c in chunks}
    for idx, cid in enumerate(voting_result.get("citation_chunk_ids", [])):
        if cid in chunk_map:
            full_text = chunk_map[cid]["text"]
            citation_chunks.append({
                "id": cid,
                "number": idx + 1,          # [1], [2]... reference number
                "page_number": chunk_map[cid]["page_number"],
                "text": full_text,           # full text kept for citations panel
                "first_sentence": _extract_first_sentence(full_text, max_len=200),
                "similarity": chunk_map[cid].get("similarity", 0),
            })

    # Build citation_map: number -> citation (for [n] resolution in frontend)
    # Map ALL retrieved chunks by their position in the chunks list
    citation_map = {}
    for idx, c in enumerate(chunks):
        citation_map[str(idx + 1)] = {
            "id": c["id"],
            "number": idx + 1,
            "page_number": c.get("page_number"),
            "text": c.get("text"),
            "first_sentence": _extract_first_sentence(c.get("text", ""), max_len=200),
            "similarity": c.get("similarity", 0),
        }

    # Log user activity
    log_user_activity(
        user_id=str(user_id),
        event_type="query",
        document_id=str(document_id),
        query_session_id=str(query_session.id),
    )

    return jsonify({
        "query_session_id": str(query_session.id),
        "question": question,
        "final_answer": final_answer.to_dict(),
        "citations": citation_chunks,
        "citation_map": citation_map,   # { "1": {id, number, page, text, first_sentence}, ... }
        "model_results": [
            {
                "model_name": r.model_name,
                "answer_text": r.answer_text,
                "latency_ms": r.latency_ms,
                "tokens_used": r.tokens_used,
                "success": not r.answer_text.startswith("Error:") and not r.answer_text.startswith("API key"),
            }
            for r in result_objects
        ],
        "voting_scores": voting_result.get("model_scores", {}),
        "retrieved_chunks": [
            {
                "id": c["id"],
                "page_number": c["page_number"],
                "text_preview": c["text"][:150] + "...",
                "similarity": c.get("similarity", 0),
            }
            for c in chunks
        ],
    }), 200


def extract_cited_from_result(result: dict, chunks: list) -> list:
    """
    Extract cited chunk IDs from an LLM result.
    Tries [n] pattern first, then falls back to word-overlap.
    """
    answer_text = result.get("answer_text", "")
    if not answer_text:
        return []

    # Try [n] pattern first (short citation format)
    cited_nums = set()
    import re
    for match in re.finditer(r"\[(\d+)\]", answer_text):
        cited_nums.add(int(match.group(1)))

    if cited_nums:
        # Build index map: number -> chunk_id (1-based index)
        chunk_ids = [c["id"] for c in chunks]
        cited_ids = []
        for num in cited_nums:
            idx = num - 1
            if 0 <= idx < len(chunk_ids):
                cited_ids.append(chunk_ids[idx])
        return cited_ids

    # Fallback: word-overlap detection
    answer_words = set(answer_text.lower().split())
    cited_ids = []

    for chunk in chunks:
        chunk_text = chunk.get("text", "").lower()
        if not chunk_text:
            continue
        chunk_words = set(chunk_text.split())
        overlap = len(answer_words & chunk_words)
        if overlap >= 5:
            cited_ids.append(chunk["id"])

    return cited_ids


def _extract_first_sentence(text: str, max_len: int = 200) -> str:
    """Extract the first sentence or first N characters of text."""
    text = text.strip()
    for i, ch in enumerate(text):
        if ch in ".!?" and i > 10:
            sentence = text[: i + 1].strip()
            if len(sentence) <= max_len:
                return sentence
            break
    return text[:max_len].strip() + ("..." if len(text) > max_len else "")


@queries_bp.route("/summarize", methods=["POST"])
@jwt_required()
def summarize_document():
    """Generate a summary of a document using multi-LLM."""
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    document_id = data.get("document_id")
    summary_type = data.get("type", "abstract")  # 'abstract', 'full', 'section'
    top_k = data.get("top_k", current_app.config.get("TOP_K", 5))

    if not document_id:
        return jsonify({"error": "document_id is required"}), 400

    document = Document.query.filter_by(id=document_id, user_id=user_id).first()
    if not document:
        return jsonify({"error": "Document not found"}), 404
    if document.status != "ready":
        return jsonify({"error": f"Document is not ready (status: {document.status})"}), 400

    # Get all chunks for context
    chunks = DocumentChunk.query.filter_by(document_id=document_id) \
        .order_by(DocumentChunk.chunk_index).all()

    if not chunks:
        return jsonify({"error": "No chunks found for document"}), 400

    chunk_data = [
        {
            "id": str(c.id),
            "chunk_index": c.chunk_index,
            "page_number": c.page_number,
            "text": c.text,
            "similarity": 1.0,
        }
        for c in chunks
    ]

    context = build_context_from_chunks(chunk_data, max_chars=12000, short_citation=True)

    question = (
        "Provide a comprehensive summary of this academic paper including: "
        "1) Main research question/objective, "
        "2) Key methodology, "
        "3) Main findings and results, "
        "4) Contributions and significance. "
        "Cite sources using [1], [2], etc. referring to the chunk numbers in the context."
    )

    config = {
        "OPENAI_API_KEY": current_app.config.get("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": current_app.config.get("ANTHROPIC_API_KEY"),
        "GOOGLE_API_KEY": current_app.config.get("GOOGLE_API_KEY"),
        "OPENAI_MODEL": current_app.config.get("OPENAI_MODEL"),
        "ANTHROPIC_MODEL": current_app.config.get("ANTHROPIC_MODEL"),
        "GOOGLE_MODEL": current_app.config.get("GOOGLE_MODEL"),
    }

    llm_start = time_module.time()
    llm_results = query_all_models(
        context=context,
        question=question,
        query_type="summary",
        config=config,
    )
    llm_ms = (time_module.time() - llm_start) * 1000

    # Log each LLM call
    for result in llm_results:
        provider = result.get("model_name", "").split("/")[0] if "/" in result.get("model_name", "") else "unknown"
        cited_ids = extract_cited_from_result(result, chunk_data)
        log_llm_call(
            query_session_id=str(uuid.uuid4()),
            model_provider=provider,
            model_name=result.get("model_name", "unknown"),
            query_type="summary",
            success=result.get("success", False),
            latency_ms=result.get("latency_ms"),
            answer_chars=len(result.get("answer_text", "")),
            context_chars=len(context),
            error_message=result.get("error"),
            citation_chunk_ids=cited_ids,
            retrieved_chunk_ids=[str(c.id) for c in chunks],
        )
        if result.get("success") and result.get("tokens_used", 0) > 0:
            cost = estimate_llm_cost(result.get("model_name", ""), result.get("tokens_used", 0), 0)
            if cost > 0:
                log_api_cost(user_id=str(user_id), api_provider=provider,
                    cost_type="llm_output", tokens=result.get("tokens_used", 0),
                    estimated_cost_usd=cost, model_name=result.get("model_name"))

    query_session = QuerySession(
        user_id=user_id,
        document_id=document_id,
        query_text=f"Summary request: {summary_type}",
        query_type="summary",
        retrieved_chunk_ids=[str(c.id) for c in chunks],
    )
    db.session.add(query_session)
    db.session.commit()

    result_objects = []
    for llm_result in llm_results:
        result_obj = LLMResult(
            query_session_id=query_session.id,
            model_name=llm_result["model_name"],
            answer_text=llm_result["answer_text"],
            latency_ms=llm_result.get("latency_ms", 0),
            tokens_used=llm_result.get("tokens_used", 0),
        )
        db.session.add(result_obj)
        result_objects.append(result_obj)
    db.session.commit()

    voting_result = vote_and_select(llm_results, chunk_data)

    # Log voting + user activity
    successful_models = [r.get("model_name") for r in llm_results if r.get("success")]
    failed_models = [r.get("model_name") for r in llm_results if not r.get("success")]
    log_voting(
        query_session_id=str(query_session.id),
        winning_model=voting_result.get("winning_model", "unknown"),
        agreement_score=voting_result.get("agreement_score"),
        citation_overlap=voting_result.get("citation_overlap"),
        combined_score=voting_result.get("combined_score"),
        model_count=len(llm_results),
        successful_models=successful_models,
        failed_models=failed_models,
    )
    log_user_activity(
        user_id=str(user_id),
        event_type="summary",
        document_id=str(document_id),
        query_session_id=str(query_session.id),
    )

    final_answer = FinalAnswer(
        query_session_id=query_session.id,
        answer_text=voting_result.get("answer_text", ""),
        citation_chunk_ids=[],
        winning_model=voting_result.get("winning_model", "unknown"),
        agreement_score=voting_result.get("agreement_score", 0),
        citation_overlap=voting_result.get("citation_overlap", 0),
    )
    db.session.add(final_answer)
    db.session.commit()

    return jsonify({
        "query_session_id": str(query_session.id),
        "document_id": str(document_id),
        "summary_type": summary_type,
        "final_answer": final_answer.to_dict(),
        "model_results": [
            {
                "model_name": r.model_name,
                "answer_text": r.answer_text,
                "latency_ms": r.latency_ms,
                "tokens_used": r.tokens_used,
                "success": not r.answer_text.startswith("Error:") and not r.answer_text.startswith("API key"),
            }
            for r in result_objects
        ],
        "voting_scores": voting_result.get("model_scores", {}),
    }), 200


@queries_bp.route("/history", methods=["GET"])
@jwt_required()
def get_history():
    """Get query history for the current user."""
    user_id = get_jwt_identity()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    document_id = request.args.get("document_id", None)

    query = QuerySession.query.filter_by(user_id=user_id)

    if document_id:
        query = query.filter_by(document_id=document_id)

    query = query.order_by(QuerySession.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    sessions = []
    for session in pagination.items:
        session_dict = session.to_dict()
        if session.final_answer:
            session_dict["final_answer"] = session.final_answer.to_dict()
        sessions.append(session_dict)

    return jsonify({
        "sessions": sessions,
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    }), 200


@queries_bp.route("/<session_id>", methods=["GET"])
@jwt_required()
def get_query_result(session_id):
    """Get detailed results for a specific query session."""
    user_id = get_jwt_identity()

    session = QuerySession.query.filter_by(id=session_id, user_id=user_id).first()
    if not session:
        return jsonify({"error": "Query session not found"}), 404

    # Get document
    document = Document.query.get(session.document_id)
    document_info = None
    if document:
        document_info = {
            "id": str(document.id),
            "title": document.title,
        }

    # Get LLM results
    llm_results = LLMResult.query.filter_by(query_session_id=session_id).all()

    # Get citation chunks
    citation_chunks = []
    if session.final_answer and session.final_answer.citation_chunk_ids:
        for cid in session.final_answer.citation_chunk_ids:
            chunk = DocumentChunk.query.get(cid)
            if chunk:
                citation_chunks.append(chunk.to_dict())

    return jsonify({
        "session": session.to_dict(),
        "document": document_info,
        "final_answer": session.final_answer.to_dict() if session.final_answer else None,
        "citation_chunks": citation_chunks,
        "llm_results": [r.to_dict() for r in llm_results],
    }), 200


@queries_bp.route("/evaluation/metrics", methods=["GET"])
@jwt_required()
def get_evaluation_metrics():
    """Get aggregated evaluation metrics."""
    user_id = get_jwt_identity()

    # Get all QA sessions with final answers
    sessions = QuerySession.query.filter_by(
        user_id=user_id,
        query_type="qa",
    ).all()

    total_queries = len(sessions)

    if total_queries == 0:
        return jsonify({
            "total_queries": 0,
            "avg_agreement_score": 0,
            "avg_citation_overlap": 0,
            "avg_latency_by_model": {},
            "model_win_counts": {},
            "recent_sessions": [],
        }), 200

    # Calculate metrics
    agreement_scores = []
    citation_overlaps = []
    latency_by_model = {}
    model_win_counts = {}
    total_latencies = {}

    for session in sessions:
        if session.final_answer:
            agreement_scores.append(session.final_answer.agreement_score or 0)
            citation_overlaps.append(session.final_answer.citation_overlap or 0)
            model = session.final_answer.winning_model
            model_win_counts[model] = model_win_counts.get(model, 0) + 1

        # Latency per model
        for result in session.llm_results:
            model = result.model_name
            latency = result.latency_ms or 0
            if model not in total_latencies:
                total_latencies[model] = {"total": 0, "count": 0}
            total_latencies[model]["total"] += latency
            total_latencies[model]["count"] += 1

    avg_latency = {}
    for model, data in total_latencies.items():
        avg_latency[model] = round(data["total"] / data["count"], 2) if data["count"] > 0 else 0

    recent_sessions = []
    for session in sessions[:5]:
        recent_sessions.append({
            "id": str(session.id),
            "document_id": str(session.document_id),
            "query_text": session.query_text,
            "query_type": session.query_type,
            "agreement_score": session.final_answer.agreement_score if session.final_answer else None,
            "winning_model": session.final_answer.winning_model if session.final_answer else None,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        })

    return jsonify({
        "total_queries": total_queries,
        "avg_agreement_score": round(sum(agreement_scores) / len(agreement_scores), 3) if agreement_scores else 0,
        "avg_citation_overlap": round(sum(citation_overlaps) / len(citation_overlaps), 3) if citation_overlaps else 0,
        "avg_latency_by_model": avg_latency,
        "model_win_counts": model_win_counts,
        "recent_sessions": recent_sessions,
    }), 200
