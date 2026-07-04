"""Structured JSON logging for the A2A auth chain."""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any


class StructuredLogger:
    """Emits one JSON object per log record to stdout."""

    def __init__(self, name: str) -> None:
        self._log = logging.getLogger(name)
        if not self._log.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._log.addHandler(handler)
        self._log.setLevel(logging.DEBUG)

    def _emit(self, level: int, event: str, **kwargs: Any) -> None:
        record = {"ts": time.time(), "event": event, **kwargs}
        self._log.log(level, json.dumps(record))

    def debug(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.ERROR, event, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
