"""Input validation helpers."""
import os
from pathlib import Path
from typing import Optional
from app.config import settings


def validate_file_extension(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in settings.allowed_extensions


def validate_file_size(size_bytes: int) -> bool:
    return size_bytes <= settings.max_file_size_bytes


def safe_filename(filename: str) -> str:
    """Strip path components and dangerous characters."""
    name = os.path.basename(filename)
    # Remove anything that's not alphanumeric, dash, underscore, dot
    import re
    name = re.sub(r"[^\w.\-]", "_", name)
    return name or "upload"


def validate_period_type(period_type: str) -> bool:
    return period_type in {"monthly", "quarterly", "annual", "semi_annual"}


def validate_scenario_name(name: str) -> bool:
    import re
    return bool(re.match(r"^[\w\s\-]{1,64}$", name))
