import json
import numpy as np
from typing import List, Dict, Any
from sqlalchemy import text
from app.models import DocumentChunk
from app.services.embedding_service import generate_embedding, batch_cosine_similarity


def search_similar_chunks(
    query_embedding: List[float],
    document_id: str,
    top_k: int = 5,
    db_session=None,
) -> List[Dict[str, Any]]:
    """
    Search for the most similar chunks to a query embedding within a document.
    Uses cosine similarity via pgvector.
    """
    if not query_embedding:
        return []

    if db_session is None:
        from app.extensions import db
        db_session = db.session

    try:
        # Use pgvector's cosine distance operator <=>
        # Cosine similarity = 1 - cosine_distance
        query_vec = np.array(query_embedding)
        query_vec_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = text("""
            SELECT id, chunk_index, page_number, text,
                   1 - (embedding <=> CAST(:vec AS vector)) AS similarity
            FROM document_chunks
            WHERE document_id = :doc_id
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :top_k
        """)

        result = db_session.execute(
            sql,
            {"vec": query_vec_str, "doc_id": document_id, "top_k": top_k}
        )
        rows = result.fetchall()

        chunks = []
        for row in rows:
            chunks.append({
                "id": str(row.id),
                "chunk_index": row.chunk_index,
                "page_number": row.page_number,
                "text": row.text,
                "similarity": float(row.similarity) if row.similarity else 0.0,
            })

        return chunks

    except Exception as e:
        print(f"Vector search error: {e}")
        # Fallback: simple text search
        return fallback_search(query_embedding, document_id, top_k, db_session)


def fallback_search(
    query_embedding: List[float],
    document_id: str,
    top_k: int,
    db_session,
) -> List[Dict[str, Any]]:
    """Fallback search using in-memory cosine similarity."""
    chunks = DocumentChunk.query.filter_by(document_id=document_id).all()

    if not chunks:
        return []

    chunk_embeddings = []
    chunk_data = []

    for chunk in chunks:
        if chunk.embedding:
            emb = json.loads(chunk.embedding)
            if isinstance(emb, list) and emb and not (isinstance(emb[0], (int, float)) and sum(emb) == 0):
                chunk_embeddings.append(emb)
                chunk_data.append({
                    "id": str(chunk.id),
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "text": chunk.text,
                })

    if not chunk_embeddings:
        # Return first k chunks as fallback
        return [
            {
                "id": str(c.id),
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
                "text": c.text,
                "similarity": 0.0,
            }
            for c in chunks[:top_k]
        ]

    similarities = batch_cosine_similarity(query_embedding, chunk_embeddings)

    # Combine with data
    for i, data in enumerate(chunk_data):
        data["similarity"] = similarities[i]

    # Sort by similarity descending
    sorted_chunks = sorted(
        zip(chunk_data, similarities),
        key=lambda x: x[1],
        reverse=True,
    )

    result = [
        {**data, "similarity": float(sim)}
        for data, sim in sorted_chunks[:top_k]
    ]

    return result


def build_context_from_chunks(
    chunks: List[Dict[str, Any]],
    max_chars: int = 8000,
    short_citation: bool = True,
) -> str:
    """
    Build a context string from retrieved chunks for LLM input.
    Chunks are ordered by relevance (similarity).

    Args:
        chunks: List of chunk dicts with 'text', 'page_number', 'id'.
        max_chars: Hard cap on total context characters.
        short_citation: If True, use numbered refs [1], [2]... and return
                        chunk_map for citation resolution. If False, use
                        legacy full-text inline format.
    """
    context_parts = []
    total_chars = 0

    for idx, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        page = chunk.get("page_number", "?")
        chunk_id = chunk.get("id", f"chunk-{idx}")

        if short_citation:
            # Short format: [1] [Page 3] First sentence of chunk...
            # Extract first sentence (up to first period + space, max 150 chars)
            first_sentence = _extract_first_sentence(text, max_len=150)
            prefix = f"[{idx + 1}] [Page {page}] "
            chunk_text = prefix + first_sentence
        else:
            # Legacy format: full chunk text
            chunk_text = f"[Page {page}]\n{text}"

        chunk_chars = len(chunk_text)

        if total_chars + chunk_chars > max_chars:
            remaining = max_chars - total_chars
            if remaining > 200:
                context_parts.append(chunk_text[:remaining] + "...")
                total_chars += remaining
            break

        context_parts.append(chunk_text)
        total_chars += chunk_chars

    return "\n\n---\n\n".join(context_parts)


def _extract_first_sentence(text: str, max_len: int = 150) -> str:
    """Extract the first sentence or first N characters of text."""
    text = text.strip()
    # Find first sentence-ending punctuation
    for i, ch in enumerate(text):
        if ch in ".!?" and i > 10:
            sentence = text[: i + 1].strip()
            if len(sentence) <= max_len:
                return sentence
            break
    # Fallback: return up to max_len
    return text[:max_len].strip() + ("..." if len(text) > max_len else "")


def build_context_from_chunks_legacy(chunks: List[Dict[str, Any]], max_chars: int = 8000) -> str:
    """Legacy wrapper for backward compatibility."""
    return build_context_from_chunks(chunks, max_chars, short_citation=False)
