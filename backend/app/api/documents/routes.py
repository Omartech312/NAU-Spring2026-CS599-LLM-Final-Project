import os
import uuid
import json
import time as time_module
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import Document, DocumentChunk
from app.models import User
from app.utils.helpers import allowed_file, sanitize_filename, extract_title_from_filename
from app.services.pdf_service import extract_text_from_pdf
from app.services.latex_service import extract_text_from_tex
from app.services.chunker import chunk_text
from app.services.embedding_service import generate_embeddings_batch
from app.services.analytics_service import (
    log_document_processing,
    log_embedding,
    log_api_cost,
    estimate_embedding_cost,
    log_system_health,
)
from app.utils.decorators import jwt_required_custom

documents_bp = Blueprint("documents", __name__)


def process_document(document: Document) -> dict:
    """Process a PDF or LaTeX document: extract text, chunk, embed."""
    overall_start = time_module.time()
    file_ext = document.filename.rsplit(".", 1)[-1].lower()
    total_chars = 0

    try:
        # --- Extraction phase ---
        extraction_start = time_module.time()
        if file_ext == "tex":
            extraction_result = extract_text_from_tex(document.file_path)
        else:
            extraction_result = extract_text_from_pdf(document.file_path)
        extraction_ms = (time_module.time() - extraction_start) * 1000

        if not extraction_result.get("success"):
            document.status = "error"
            document.error_message = extraction_result.get("error", "Extraction failed")
            db.session.commit()

            log_document_processing(
                document_id=str(document.id),
                user_id=str(document.user_id),
                file_type=file_ext,
                status="error",
                error_stage="extraction",
                error_message=document.error_message,
            )
            return {"success": False, "error": document.error_message}

        pages = extraction_result["pages"]
        full_text = extraction_result["full_text"]
        total_pages = extraction_result["total_pages"]
        total_chars = len(full_text)

        document.total_pages = total_pages
        document.status = "processing"
        db.session.commit()

        # --- Chunking phase ---
        chunking_start = time_module.time()
        chunks = chunk_text(
            full_text,
            chunk_size=current_app.config.get("CHUNK_SIZE", 800),
            overlap=current_app.config.get("CHUNK_OVERLAP", 200),
            page_info=pages,
        )
        chunking_ms = (time_module.time() - chunking_start) * 1000

        # --- Embedding phase ---
        embedding_start = time_module.time()
        chunk_texts = [c["text"] for c in chunks]

        # Log embedding call (batch = document processing)
        embedding_success = False
        embedding_error = None
        embeddings = []
        try:
            embeddings = generate_embeddings_batch(
                chunk_texts,
                model=current_app.config.get("EMBEDDING_MODEL", "text-embedding-3-small"),
            )
            embedding_success = True
        except Exception as emb_err:
            embeddings = []
            embedding_error = str(emb_err)
            log_system_health(
                event_type="embedding_error",
                severity="error",
                details={"document_id": str(document.id), "error": embedding_error},
            )

        embedding_ms = (time_module.time() - embedding_start) * 1000
        total_processing_ms = (time_module.time() - overall_start) * 1000

        # Log embedding analytics
        total_tokens = sum(len(t) for t in chunk_texts)
        embedding_model = current_app.config.get("EMBEDDING_MODEL", "text-embedding-3-small")
        log_embedding(
            call_type="batch",
            success=embedding_success,
            latency_ms=embedding_ms,
            input_text_len=total_chars,
            model=embedding_model,
            error_message=embedding_error,
            document_id=str(document.id),
            user_id=str(document.user_id),
            api_provider="openai",
        )

        # Log embedding cost
        if embedding_success:
            cost = estimate_embedding_cost(total_tokens)
            log_api_cost(
                user_id=str(document.user_id),
                api_provider="openai",
                cost_type="embedding",
                tokens=total_tokens,
                estimated_cost_usd=cost,
                model_name=embedding_model,
                query_session_id=None,
            )

        if not embedding_success:
            document.status = "error"
            document.error_message = f"Embedding failed: {embedding_error}"
            db.session.commit()

            log_document_processing(
                document_id=str(document.id),
                user_id=str(document.user_id),
                file_type=file_ext,
                file_size_bytes=os.path.getsize(document.file_path) if os.path.exists(document.file_path) else 0,
                total_pages=total_pages,
                total_chunks=len(chunks),
                extraction_ms=extraction_ms,
                chunking_ms=chunking_ms,
                embedding_ms=embedding_ms,
                total_processing_ms=total_processing_ms,
                status="error",
                error_stage="embedding",
                error_message=embedding_error,
            )
            return {"success": False, "error": document.error_message}

        # Save chunks with embeddings
        chunk_objects = []
        for i, chunk_data in enumerate(chunks):
            embedding = embeddings[i] if i < len(embeddings) else None
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=chunk_data["chunk_index"],
                page_number=chunk_data.get("page_numbers", [1])[0] if chunk_data.get("page_numbers") else 1,
                text=chunk_data["text"],
                embedding=json.dumps(embedding) if embedding is not None else None,
            )
            db.session.add(chunk)
            chunk_objects.append(chunk)

        db.session.commit()

        document.total_chunks = len(chunks)
        document.status = "ready"
        document.processed_at = db.func.now()
        db.session.commit()

        # --- Log success ---
        log_document_processing(
            document_id=str(document.id),
            user_id=str(document.user_id),
            file_type=file_ext,
            file_size_bytes=os.path.getsize(document.file_path) if os.path.exists(document.file_path) else 0,
            total_pages=total_pages,
            total_chunks=len(chunks),
            extraction_ms=extraction_ms,
            chunking_ms=chunking_ms,
            embedding_ms=embedding_ms,
            total_processing_ms=total_processing_ms,
            status="success",
        )

        return {
            "success": True,
            "total_pages": total_pages,
            "total_chunks": len(chunks),
        }

    except Exception as e:
        total_processing_ms = (time_module.time() - overall_start) * 1000
        document.status = "error"
        document.error_message = str(e)
        db.session.commit()

        log_document_processing(
            document_id=str(document.id),
            user_id=str(document.user_id),
            file_type=file_ext,
            total_processing_ms=total_processing_ms,
            status="error",
            error_stage="unknown",
            error_message=str(e),
        )
        log_system_health(
            event_type="document_processing_error",
            severity="error",
            details={"document_id": str(document.id), "error": str(e)},
        )
        return {"success": False, "error": str(e)}


@documents_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():
    """Upload and process a PDF document."""
    user_id = get_jwt_identity()

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF or LaTeX (.tex) files are allowed"}), 400

    # Save file
    original_filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{sanitize_filename(original_filename)}"
    upload_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(user_id))
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)

    # Create document record
    title = request.form.get("title", "").strip()
    if not title:
        title = extract_title_from_filename(original_filename)

    document = Document(
        user_id=user_id,
        title=title,
        filename=original_filename,
        file_path=file_path,
        status="pending",
    )
    db.session.add(document)
    db.session.commit()

    # Process in the same request (can be moved to background task later)
    result = process_document(document)

    # Log user activity on successful upload
    if result.get("success"):
        from app.services.analytics_service import log_user_activity
        log_user_activity(
            user_id=str(user_id),
            event_type="upload",
            document_id=str(document.id),
        )

    return jsonify({
        "message": "Document uploaded successfully",
        "document": document.to_dict(),
        "processing": result,
    }), 201


@documents_bp.route("", methods=["GET"])
@jwt_required()
def list_documents():
    """List all documents for the current user."""
    user_id = get_jwt_identity()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    status = request.args.get("status", None)

    query = Document.query.filter_by(user_id=user_id)

    if status:
        query = query.filter_by(status=status)

    query = query.order_by(Document.uploaded_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "documents": [doc.to_dict() for doc in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    }), 200


@documents_bp.route("/<document_id>", methods=["GET"])
@jwt_required()
def get_document(document_id):
    """Get a specific document by ID."""
    user_id = get_jwt_identity()

    document = Document.query.filter_by(id=document_id, user_id=user_id).first()
    if not document:
        return jsonify({"error": "Document not found"}), 404

    return jsonify({"document": document.to_dict()}), 200


@documents_bp.route("/<document_id>", methods=["DELETE"])
@jwt_required()
def delete_document(document_id):
    """Delete a document and all its chunks."""
    user_id = get_jwt_identity()

    document = Document.query.filter_by(id=document_id, user_id=user_id).first()
    if not document:
        return jsonify({"error": "Document not found"}), 404

    # Delete the file
    if os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except Exception:
            pass

    # Delete from DB (cascade will handle chunks)
    db.session.delete(document)
    db.session.commit()

    return jsonify({"message": "Document deleted successfully"}), 200


@documents_bp.route("/<document_id>/chunks", methods=["GET"])
@jwt_required()
def list_chunks(document_id):
    """List chunks for a document (paginated)."""
    user_id = get_jwt_identity()

    document = Document.query.filter_by(id=document_id, user_id=user_id).first()
    if not document:
        return jsonify({"error": "Document not found"}), 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    pagination = DocumentChunk.query.filter_by(document_id=document_id) \
        .order_by(DocumentChunk.chunk_index) \
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "chunks": [c.to_dict() for c in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    }), 200


@documents_bp.route("/<document_id>/reprocess", methods=["POST"])
@jwt_required()
def reprocess_document(document_id):
    """Re-process a document that had errors."""
    user_id = get_jwt_identity()

    document = Document.query.filter_by(id=document_id, user_id=user_id).first()
    if not document:
        return jsonify({"error": "Document not found"}), 404

    if document.status == "processing":
        return jsonify({"error": "Document is already being processed"}), 409

    document.status = "pending"
    document.error_message = None
    db.session.commit()

    result = process_document(document)

    return jsonify({
        "message": "Document re-processed",
        "document": document.to_dict(),
        "processing": result,
    }), 200
