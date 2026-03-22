"""Structured JSON logger with file rotation."""

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "data"):
            entry["data"] = record.data  # type: ignore[attr-defined]
        return json.dumps(entry)


def get_logger(name: str, logs_dir: Path | None = None) -> logging.Logger:
    """Get a structured JSON logger that writes to file and stderr."""
    logger = logging.getLogger(f"prospector.{name}")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    base = logs_dir or _LOGS_DIR
    base.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    file_handler = RotatingFileHandler(
        base / f"{name}_{date_str}.jsonl",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=30,
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
    stderr_handler.setLevel(logging.INFO)
    logger.addHandler(stderr_handler)

    return logger
