"""
LaTeX (.tex) text extraction service.

Extracts plain text from LaTeX source files, stripping commands
and preserving meaningful content for chunking and embedding.
"""
import re
from typing import Dict, Any, List


# Patterns for whitespace normalization
WHITESPACE_PATTERNS = [
    (re.compile(r'\n{3,}'), '\n\n'),
    (re.compile(r' {2,}'), ' '),
    (re.compile(r'\n '), '\n'),
    (re.compile(r' \n'), '\n'),
]


def _strip_latex_commands(text: str) -> str:
    """Remove LaTeX commands, leaving only readable text."""
    lines = text.split('\n')
    clean_lines = []

    for line in lines:
        # Handle % comments within lines
        line = re.sub(r' %.*$', '', line)
        # Skip lines that are purely LaTeX commands / lengths / assignments
        stripped = re.sub(r'\\[a-zA-Z]+', '', line)
        stripped = re.sub(r'\{[^}]*\}', '', stripped)
        stripped = re.sub(r'\[[^\]]*\]', '', stripped)
        stripped = re.sub(r'[0-9]+(?:\.[0-9]+)?(?:pt|cm|mm|in|em|ex|bp)', '', stripped)
        cleaned = stripped.strip()

        # Drop lines that are empty or only contain numbers/punctuation
        if cleaned and not re.fullmatch(r'[\d.,;:\-+]+', cleaned):
            clean_lines.append(line)

    return '\n'.join(clean_lines)


def _remove_latex_artifacts(text: str) -> str:
    """Remove remaining LaTeX artifacts after command stripping."""
    # Remove lengths, coordinates, picture commands
    text = re.sub(r'\b\d+(?:\.\d+)?(?:pt|cm|mm|in|em|ex|bp)\b', '', text)
    # Remove picture/tabular column specs like |c|c|c|
    text = re.sub(r'\|[lcrp]+\|?', ' ', text)
    # Remove common picture environment artifacts
    text = re.sub(r'\b(?:put|multiput|line|vector|circle|oval|rectangle)\b[^{]*\{[^}]*\}', ' ', text)
    text = re.sub(r'\{-?[0-9., ]+\}', ' ', text)
    # Remove remaining brace content that looks like coordinates or lengths
    text = re.sub(r'\{[0-9.,\s\-]+\}', ' ', text)
    # Remove leftover backslashes
    text = re.sub(r'\\[{}]', '', text)
    # Remove dash variations
    text = re.sub(r'--+', ' ', text)
    # Remove page refs and figure refs
    text = re.sub(r'\\ref\{[^}]*\}', '', text)
    text = re.sub(r'\\pageref\{[^}]*\}', '', text)
    text = re.sub(r'\\cite\{[^}]*\}', '', text)
    text = re.sub(r'\\label\{[^}]*\}', '', text)
    return text


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace in extracted text."""
    for pattern, replacement in WHITESPACE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()


def _split_into_sections(text: str) -> List[Dict[str, str]]:
    """
    Attempt to split LaTeX text into sections with metadata.
    Returns list of {"section": name, "text": content}.
    """
    sections = []
    current_section = "Document"
    current_lines = []

    section_pattern = re.compile(r'^\s*(chapter|section|subsection|subsubsection)\s*[:.]?\s*(.+)$', re.IGNORECASE)

    for line in text.split('\n'):
        match = section_pattern.match(line.strip())
        if match:
            level, title = match.groups()
            if current_lines:
                sections.append({
                    "section": current_section,
                    "text": '\n'.join(current_lines).strip(),
                })
            current_section = f"{level.title()}: {title.strip()}"
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            "section": current_section,
            "text": '\n'.join(current_lines).strip(),
        })

    return sections


def extract_text_from_tex(file_path: str) -> Dict[str, Any]:
    """
    Extract text content from a LaTeX (.tex) file.

    Returns a dict with:
        - success: bool
        - full_text: the complete extracted text
        - pages: list of {"page_number": 1, "text": str} (section-based "pages")
        - total_pages: number of sections (or 1 if no clear sections)
        - sections: list of section names (if detected)
        - error: error message if failed
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            raw_text = f.read()

        if not raw_text.strip():
            return {
                "success": False,
                "error": "Empty file",
                "full_text": "",
                "pages": [],
                "total_pages": 0,
                "sections": [],
            }

        # Strip LaTeX commands
        plain_text = _strip_latex_commands(raw_text)

        # Remove remaining LaTeX artifacts
        plain_text = _remove_latex_artifacts(plain_text)

        # Normalize whitespace
        plain_text = _normalize_whitespace(plain_text)

        if not plain_text.strip():
            return {
                "success": False,
                "error": "No readable text content found",
                "full_text": "",
                "pages": [],
                "total_pages": 0,
                "sections": [],
            }

        # Split into sections
        sections = _split_into_sections(plain_text)

        # Build "pages" list (one per section for chunking)
        pages = []
        for i, section_data in enumerate(sections):
            pages.append({
                "page_number": i + 1,
                "text": section_data["text"],
            })

        # If no sections detected, treat whole thing as one page
        if not pages:
            pages = [{"page_number": 1, "text": plain_text}]

        return {
            "success": True,
            "full_text": plain_text,
            "pages": pages,
            "total_pages": len(pages),
            "sections": [s["section"] for s in sections],
            "error": None,
        }

    except UnicodeDecodeError as e:
        return {
            "success": False,
            "error": f"Encoding error: {str(e)}",
            "full_text": "",
            "pages": [],
            "total_pages": 0,
            "sections": [],
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to extract LaTeX: {str(e)}",
            "full_text": "",
            "pages": [],
            "total_pages": 0,
            "sections": [],
        }
