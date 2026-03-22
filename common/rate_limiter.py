"""File-based daily rate limiter."""

import json
from datetime import datetime, timezone
from pathlib import Path

_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


class RateLimiter:
    def __init__(self, logs_dir: Path | None = None):
        self._dir = logs_dir or _LOGS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def _counter_path(self, operation: str) -> Path:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._dir / f".rate_{operation}_{date_str}.json"

    def _read(self, operation: str) -> int:
        path = self._counter_path(operation)
        if not path.exists():
            return 0
        data = json.loads(path.read_text())
        return data.get("count", 0)

    def _write(self, operation: str, count: int) -> None:
        path = self._counter_path(operation)
        path.write_text(json.dumps({"count": count}))

    def can_proceed(self, operation: str, limit: int) -> bool:
        """Check if the operation is still under its daily limit."""
        return self._read(operation) < limit

    def increment(self, operation: str) -> int:
        """Increment the counter and return the new count."""
        count = self._read(operation) + 1
        self._write(operation, count)
        return count

    def current_count(self, operation: str) -> int:
        return self._read(operation)
