import re
import tiktoken
from typing import List, Dict, Any


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens in text using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 200,
    page_info: List[Dict] = None,
) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks of approximately chunk_size tokens.

    Strategy:
    1. Try to split on paragraph boundaries (\n\n)
    2. Fall back to sentence boundaries (\n or .)
    3. Fall back to character limit
    4. Track which page each chunk came from
    """
    if not text or not text.strip():
        return []

    chunks = []
    chunk_size_chars = chunk_size * 4  # rough approximation: 1 token ≈ 4 chars
    overlap_chars = overlap * 4

    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    current_chunk_texts = []
    current_chunk_size = 0
    current_pages = set()

    def add_chunk(texts: List[str], pages: set) -> Dict[str, Any]:
        """Create a chunk dict from accumulated texts."""
        combined = "\n\n".join(texts)
        # Find which pages contributed to this chunk
        page_nums = []
        if page_info:
            page_nums = [p["page_number"] for p in page_info if p["text"] and any(
                p["text"][i:i+50] in combined for i in range(0, min(len(p["text"]), 200), 50)
            )]
        if not page_nums and page_info:
            # Fallback: estimate based on character position
            total_chars = sum(len(p["text"]) for p in page_info)
            pos = 0
            for p in page_info:
                if pos <= len(combined) < pos + len(p["text"]):
                    page_nums = [p["page_number"]]
                    break
                pos += len(p["text"])

        return {
            "text": combined,
            "token_count": count_tokens(combined),
            "char_count": len(combined),
            "page_numbers": sorted(set(page_nums)) if page_nums else [1],
            "start_sources": list(pages),
        }

    for para in paragraphs:
        para_tokens = count_tokens(para)
        para_chars = len(para)

        # If single paragraph exceeds chunk size, split it further
        if para_tokens > chunk_size:
            sub_chunks = _split_paragraph(para, chunk_size_chars)
            for sub in sub_chunks:
                sub_tokens = count_tokens(sub)
                if current_chunk_size + sub_tokens > chunk_size:
                    if current_chunk_texts:
                        chunks.append(add_chunk(current_chunk_texts, current_pages))
                    # Start new chunk with overlap from previous
                    overlap_text = ""
                    if overlap_chars > 0 and current_chunk_texts:
                        overlap_text = "\n\n".join(current_chunk_texts)[-overlap_chars:]
                        if overlap_text:
                            current_chunk_texts = [overlap_text]
                            current_chunk_size = count_tokens(overlap_text)
                        else:
                            current_chunk_texts = []
                            current_chunk_size = 0
                    else:
                        current_chunk_texts = []
                        current_chunk_size = 0

                current_chunk_texts.append(sub)
                current_chunk_size += sub_tokens
                current_pages.add(f"para_{len(current_chunk_texts)}")
        else:
            # Normal paragraph
            if current_chunk_size + para_tokens > chunk_size:
                # Finalize current chunk
                if current_chunk_texts:
                    chunks.append(add_chunk(current_chunk_texts, current_pages))

                # Start new chunk with overlap
                overlap_text = ""
                if overlap_chars > 0 and current_chunk_texts:
                    combined_prev = "\n\n".join(current_chunk_texts)
                    overlap_text = combined_prev[-(overlap_chars):]
                    if overlap_text.strip():
                        current_chunk_texts = [overlap_text]
                        current_chunk_size = count_tokens(overlap_text)
                    else:
                        current_chunk_texts = []
                        current_chunk_size = 0
                else:
                    current_chunk_texts = []
                    current_chunk_size = 0
                current_pages = set()

            current_chunk_texts.append(para)
            current_chunk_size += para_tokens
            current_pages.add(f"para_{len(current_chunk_texts)}")

    # Don't forget the last chunk
    if current_chunk_texts:
        chunks.append(add_chunk(current_chunk_texts, current_pages))

    # Assign chunk indices
    for i, chunk in enumerate(chunks):
        chunk["chunk_index"] = i

    return chunks


def _split_paragraph(paragraph: str, max_chars: int) -> List[str]:
    """Split a large paragraph into smaller chunks at sentence boundaries."""
    # Try splitting on sentences first
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    sentences = sentence_endings.split(paragraph)

    chunks = []
    current = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        current_text = "\n".join(current)
        if current and (len(current_text) + len(sentence) + 1 > max_chars):
            chunks.append("\n".join(current))
            # Start next with partial overlap
            overlap_lines = []
            for line in reversed(current):
                overlap_lines.insert(0, line)
                if sum(len(l) for l in overlap_lines) > max_chars // 2:
                    break
            current = overlap_lines + [sentence]
        else:
            current.append(sentence)

    if current:
        chunks.append("\n".join(current))

    return chunks if chunks else [paragraph]
