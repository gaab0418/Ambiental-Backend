"""
Utility logger for startup/validation routines.

Provides lightweight JSONL logging per category (database, tests, etc.)
stored under `Backend/logs`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


LOG_ROOT = Path(__file__).resolve().parent.parent / "logs"
LOG_ROOT.mkdir(parents=True, exist_ok=True)


def _build_entry(level: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "message": message,
    }
    if details:
        entry["details"] = details
    return entry


def _log_path(name: str) -> Path:
    sanitized = name.replace(" ", "_").lower()
    return LOG_ROOT / f"{sanitized}.log"


def _write_entry(log_name: str, entry: Dict[str, Any]) -> None:
    with _log_path(log_name).open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")


class StartupLogger:
    """Simple structured logger for startup workflows."""

    default_log = "startup"

    @classmethod
    def info(cls, message: str, *, log_name: str | None = None, details: Optional[Dict[str, Any]] = None) -> None:
        _write_entry(log_name or cls.default_log, _build_entry("info", message, details))

    @classmethod
    def warning(cls, message: str, *, log_name: str | None = None, details: Optional[Dict[str, Any]] = None) -> None:
        _write_entry(log_name or cls.default_log, _build_entry("warning", message, details))

    @classmethod
    def error(cls, message: str, *, log_name: str | None = None, details: Optional[Dict[str, Any]] = None) -> None:
        _write_entry(log_name or cls.default_log, _build_entry("error", message, details))

    @classmethod
    def exception(cls, message: str, exc: Exception, *, log_name: str | None = None) -> None:
        details = {"exception": type(exc).__name__, "detail": str(exc)}
        _write_entry(log_name or cls.default_log, _build_entry("error", message, details))


