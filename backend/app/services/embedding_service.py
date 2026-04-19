import os
import openai
from typing import List, Dict, Any
import numpy as np


openai_client = None


def get_openai_client():
    global openai_client
    if openai_client is None:
        openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    return openai_client


def generate_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    Generate an embedding for a single text using OpenAI's embedding API.
    Returns a list of floats (embedding vector).
    """
    try:
        client = get_openai_client()
        text = text.replace("\n", " ").strip()
        if not text:
            return [0.0] * 1536

        response = client.embeddings.create(
            model=model,
            input=[text]
        )
        embedding = response.data[0].embedding
        return embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        return [0.0] * 1536


def generate_embeddings_batch(
    texts: List[str],
    model: str = "text-embedding-3-small",
    batch_size: int = 100,
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batches.
    Returns a list of embedding vectors.
    """
    if not texts:
        return []

    try:
        client = get_openai_client()
        # Clean texts
        cleaned = [t.replace("\n", " ").strip() or " " for t in texts]

        all_embeddings = []
        for i in range(0, len(cleaned), batch_size):
            batch = cleaned[i:i + batch_size]
            response = client.embeddings.create(model=model, input=batch)
            for item in response.data:
                all_embeddings.append(item.embedding)

        return all_embeddings
    except Exception as e:
        print(f"Batch embedding error: {e}")
        # Return zero embeddings for failed batch
        return [[0.0] * 1536 for _ in texts]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def batch_cosine_similarity(query_embedding: List[float], chunk_embeddings: List[List[float]]) -> List[float]:
    """Compute cosine similarity between a query and multiple chunk embeddings."""
    if not chunk_embeddings:
        return []
    q = np.array(query_embedding)
    chunks = np.array(chunk_embeddings)

    q_norm = np.linalg.norm(q)
    chunk_norms = np.linalg.norm(chunks, axis=1)

    valid_mask = (q_norm > 0) & (chunk_norms > 0)
    similarities = np.zeros(len(chunk_embeddings))

    if valid_mask.any():
        similarities[valid_mask] = np.dot(chunks[valid_mask], q) / (q_norm * chunk_norms[valid_mask])

    return similarities.tolist()
