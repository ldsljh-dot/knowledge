"""
Common utilities for KnowledgeEngine skills.
"""

import os
import re
from pathlib import Path
from typing import Optional

def load_env() -> bool:
    """
    Attempt to load the .env file by searching upwards from the current file's directory.
    Returns True if successfully loaded, False otherwise.
    """
    try:
        from dotenv import load_dotenv
        _here = Path(__file__).resolve()
        # Search up to 4 levels up (e.g., from .gemini/skills/common/utils.py to project root)
        for _parent in [_here.parent, _here.parent.parent, _here.parent.parent.parent, _here.parent.parent.parent.parent]:
            _env = _parent / ".env"
            if _env.exists():
                load_dotenv(_env)
                return True
    except ImportError:
        pass
    return False

def safe_filename(text: str, max_length: int = 100) -> str:
    """
    Convert text to a safe filename (alphanumeric + underscores/dashes).
    Truncates to max_length.
    """
    safe = "".join([c if c.isalnum() or c in "-_" else "_" for c in text]).strip("_")
    # 연속된 언더바 하나로 축소
    safe = re.sub(r"__+", "_", safe)
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip("_")
    return safe
