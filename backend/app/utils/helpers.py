import os
import re
from datetime import datetime


def allowed_file(filename: str, allowed: set = {"pdf", "tex"}) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def sanitize_filename(filename: str) -> str:
    """Remove special characters from filename."""
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'[\s]+', '_', filename)
    return filename[:200]


def format_datetime(dt: datetime) -> str:
    """Format datetime to ISO string."""
    if dt is None:
        return None
    return dt.isoformat()


def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB."""
    return os.path.getsize(file_path) / (1024 * 1024)


def extract_title_from_filename(filename: str) -> str:
    """Extract a readable title from a PDF filename."""
    name = os.path.splitext(filename)[0]
    name = re.sub(r'[-_]+', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.title()
    if len(name) > 100:
        name = name[:100]
    return name


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to max length."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def validate_uuid(value: str) -> bool:
    """Check if string is a valid UUID."""
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(str(value)))
