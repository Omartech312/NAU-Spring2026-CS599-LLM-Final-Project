import re
import pdfplumber
from typing import List, Dict, Any


def extract_text_from_pdf(file_path: str) -> Dict[str, Any]:
    """
    Extract text from a PDF file using pdfplumber.
    Returns a dictionary with:
      - pages: list of {page_number, text}
      - total_pages: int
      - full_text: concatenated text
    """
    pages = []
    full_text_parts = []

    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)

            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                text = clean_text(text)

                pages.append({
                    "page_number": i + 1,
                    "text": text,
                    "char_count": len(text),
                })

                if text.strip():
                    full_text_parts.append(text)

            full_text = "\n\n".join(full_text_parts)

            return {
                "pages": pages,
                "total_pages": total_pages,
                "full_text": full_text,
                "success": True,
            }

    except Exception as e:
        return {
            "pages": [],
            "total_pages": 0,
            "full_text": "",
            "success": False,
            "error": str(e),
        }


def clean_text(text: str) -> str:
    """Clean extracted text for better chunking quality."""
    if not text:
        return ""

    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    # Replace multiple newlines with double newline (paragraph break)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove very short lines that are likely headers/footers (single words on a line)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that are page numbers or very short artifacts
        if stripped and len(stripped) > 3:
            cleaned_lines.append(line)
        elif stripped:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def get_page_text_by_number(pages: List[Dict], page_number: int) -> str:
    """Get the text content of a specific page."""
    for page in pages:
        if page["page_number"] == page_number:
            return page["text"]
    return ""


def get_paragraphs_by_page(pages: List[Dict]) -> List[Dict]:
    """Split pages into paragraphs with page metadata."""
    paragraphs = []

    for page in pages:
        page_text = page["text"]
        if not page_text.strip():
            continue

        page_paragraphs = page_text.split('\n\n')
        for para in page_paragraphs:
            para = para.strip()
            if len(para) > 50:  # Filter out short fragments
                paragraphs.append({
                    "text": para,
                    "page_number": page["page_number"],
                    "char_count": len(para),
                })

    return paragraphs
