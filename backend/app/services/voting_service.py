import numpy as np
from typing import List, Dict, Any
from app.services.embedding_service import generate_embedding, cosine_similarity
from app.services.analytics_service import log_embedding


def extract_cited_chunks_from_text(
    answer_text: str,
    retrieved_chunks: List[Dict[str, Any]],
    similarity_threshold: float = 0.3,
) -> List[str]:
    """
    Extract which chunks are cited in an LLM answer.
    Tries [n] pattern first (short citation format), then falls back
    to keyword/n-gram overlap.
    """
    if not answer_text or not retrieved_chunks:
        return []

    # Try [n] pattern first (short citation format)
    cited_nums = set()
    import re
    for match in re.finditer(r"\[(\d+)\]", answer_text):
        cited_nums.add(int(match.group(1)))

    if cited_nums:
        chunk_ids = [c.get("id", "") for c in retrieved_chunks]
        cited_ids = []
        for num in cited_nums:
            idx = num - 1
            if 0 <= idx < len(chunk_ids):
                cited_ids.append(str(chunk_ids[idx]))
        return cited_ids

    # Fallback: keyword overlap matching
    cited_ids = []
    answer_lower = answer_text.lower()

    for chunk in retrieved_chunks:
        chunk_text = chunk.get("text", "").lower()
        if not chunk_text:
            continue

        answer_words = set(answer_lower.split())
        chunk_words = set(chunk_text.split())

        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "this", "that", "these",
            "those", "i", "you", "he", "she", "it", "we", "they", "their", "its",
        }

        answer_keywords = answer_words - stopwords
        chunk_keywords = chunk_words - stopwords

        overlap = answer_keywords & chunk_keywords
        if len(overlap) >= 5:
            cited_ids.append(str(chunk.get("id", "")))

    return cited_ids


def compute_answer_similarity(answer1: str, answer2: str) -> float:
    """
    Compute semantic similarity between two answers using their embeddings.
    """
    if not answer1 or not answer2:
        return 0.0

    try:
        emb1 = generate_embedding(answer1[:2000])
        emb2 = generate_embedding(answer2[:2000])
        similarity = cosine_similarity(emb1, emb2)
        # Log the two embeddings used for voting similarity computation
        log_embedding(
            call_type="voting_similarity",
            success=True,
            latency_ms=0,
            input_text_len=len(answer1),
            error_message=None,
            api_provider="openai",
        )
        log_embedding(
            call_type="voting_similarity",
            success=True,
            latency_ms=0,
            input_text_len=len(answer2),
            error_message=None,
            api_provider="openai",
        )
        return similarity
    except Exception:
        # Fallback: simple word overlap
        words1 = set(answer1.lower().split())
        words2 = set(answer2.lower().split())
        if not words1 or not words2:
            return 0.0
        overlap = len(words1 & words2)
        union = len(words1 | words2)
        return overlap / union if union > 0 else 0.0


def jaccard_similarity(set1: List, set2: List) -> float:
    """Compute Jaccard similarity between two lists."""
    if not set1 or not set2:
        return 0.0
    s1 = set(set1)
    s2 = set(set2)
    intersection = len(s1 & s2)
    union = len(s1 | s2)
    return intersection / union if union > 0 else 0.0


def vote_and_select(
    llm_results: List[Dict[str, Any]],
    retrieved_chunks: List[Dict[str, Any]],
    weights: Dict[str, float] = None,
) -> Dict[str, Any]:
    """
    Voting mechanism to select the best answer from multiple LLM results.

    Steps:
    1. Extract cited chunks for each answer
    2. Compute pairwise semantic similarity between answers
    3. Compute citation overlap (Jaccard) between answers
    4. Combine scores to select the winner
    5. Extract top citation sentences for the final answer
    """
    if weights is None:
        weights = {"agreement": 0.5, "citation_overlap": 0.5}

    if not llm_results:
        return {
            "winner": None,
            "answer_text": "No results available",
            "agreement_score": 0.0,
            "citation_overlap": 0.0,
            "combined_score": 0.0,
            "model_scores": {},
        }

    # Filter successful results
    successful = [r for r in llm_results if r.get("success", False) and not r.get("error")]
    if not successful:
        # All failed, return the first one
        first = llm_results[0] if llm_results else {}
        return {
            "winner": first,
            "answer_text": first.get("answer_text", "All models failed"),
            "winning_model": first.get("model_name", "unknown"),
            "agreement_score": 0.0,
            "citation_overlap": 0.0,
            "combined_score": 0.0,
            "model_scores": {},
        }

    if len(successful) == 1:
        # Only one model succeeded
        cited = extract_cited_chunks_from_text(
            successful[0].get("answer_text", ""),
            retrieved_chunks,
        )
        return {
            "winner": successful[0],
            "answer_text": successful[0].get("answer_text", ""),
            "winning_model": successful[0].get("model_name", "unknown"),
            "citation_chunk_ids": cited,
            "agreement_score": 1.0,
            "citation_overlap": 1.0,
            "combined_score": 1.0,
            "model_scores": {
                successful[0].get("model_name", "unknown"): 1.0
            },
        }

    # Compute citation sets for each model
    citations_by_model = {}
    for result in successful:
        cited = extract_cited_chunks_from_text(
            result.get("answer_text", ""),
            retrieved_chunks,
        )
        citations_by_model[result.get("model_name", "unknown")] = cited

    # Compute pairwise answer similarity
    answers = [r.get("answer_text", "") for r in successful]
    model_names = [r.get("model_name", f"model_{i}") for i, r in enumerate(successful)]

    similarity_matrix = np.zeros((len(answers), len(answers)))
    for i in range(len(answers)):
        for j in range(len(answers)):
            if i != j:
                similarity_matrix[i][j] = compute_answer_similarity(answers[i], answers[j])

    # Agreement score: average similarity across all pairs
    agreement_scores = similarity_matrix.mean(axis=1)

    # Citation overlap: Jaccard similarity with all other models
    citation_overlaps = np.zeros(len(successful))
    for i, model_name in enumerate(model_names):
        cited_i = citations_by_model[model_name]
        other_overlaps = []
        for j, other_model in enumerate(model_names):
            if i != j:
                cited_j = citations_by_model[other_model]
                other_overlaps.append(jaccard_similarity(cited_i, cited_j))
        citation_overlaps[i] = np.mean(other_overlaps) if other_overlaps else 0.0

    # Combined score
    combined_scores = (
        weights["agreement"] * agreement_scores +
        weights["citation_overlap"] * citation_overlaps
    )

    # Build model scores
    model_scores = {}
    for i, model_name in enumerate(model_names):
        model_scores[model_name] = {
            "agreement_score": float(agreement_scores[i]),
            "citation_overlap": float(citation_overlaps[i]),
            "combined_score": float(combined_scores[i]),
            "latency_ms": successful[i].get("latency_ms", 0),
        }

    # Select winner
    best_idx = int(np.argmax(combined_scores))
    winner = successful[best_idx]
    winner_model = model_names[best_idx]
    winner_cited = citations_by_model[winner_model]

    # Get citation details
    citation_chunks = []
    chunk_id_to_info = {str(c.get("id", "")): c for c in retrieved_chunks}
    for cid in winner_cited:
        if cid in chunk_id_to_info:
            citation_chunks.append(chunk_id_to_info[cid])

    # Extract top 3 most relevant citations (by order in answer)
    top_citations = []
    if citation_chunks:
        # Sort by page number then chunk index for natural reading order
        sorted_chunks = sorted(citation_chunks, key=lambda x: (x.get("page_number", 0), x.get("chunk_index", 0)))
        top_citations = sorted_chunks[:3]

    return {
        "winner": winner,
        "answer_text": winner.get("answer_text", ""),
        "winning_model": winner_model,
        "citation_chunk_ids": winner_cited,
        "top_citations": top_citations,
        "agreement_score": float(agreement_scores[best_idx]),
        "citation_overlap": float(citation_overlaps[best_idx]),
        "combined_score": float(combined_scores[best_idx]),
        "model_scores": model_scores,
    }
