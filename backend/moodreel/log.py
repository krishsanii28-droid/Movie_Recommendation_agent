"""Logging helpers. Agent steps are logged as structured one-liners for debugging."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

_CONFIGURED = False


def setup_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s", "%H:%M:%S")
    )
    root = logging.getLogger("moodreel")
    root.addHandler(handler)
    root.setLevel(level.upper())
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"moodreel.{name}")


def log_step(logger: logging.Logger, step: str, **fields: Any) -> None:
    """Log an agent step as ``step key=value ...`` with compact JSON values."""
    parts = []
    for key, value in fields.items():
        text = value if isinstance(value, str) else json.dumps(value, default=str)
        if len(text) > 300:
            text = text[:297] + "..."
        parts.append(f"{key}={text}")
    logger.info("%s %s", step, " ".join(parts))
