from __future__ import annotations

from pathlib import Path

from changelog_gen.writer import Extension


def detect_extension() -> str | None:
    """Detect existing CHANGELOG file extension."""
    for ext in Extension:
        if Path(f"CHANGELOG.{ext.value}").exists():
            return ext
    return None
