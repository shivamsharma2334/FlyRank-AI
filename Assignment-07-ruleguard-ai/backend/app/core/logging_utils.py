import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger("ruleguard")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)

QUARANTINE_PATH = settings.logs_dir / "quarantine.jsonl"


def log_event(event: str, **fields) -> None:
    payload = {"event": event, "timestamp": datetime.now(timezone.utc).isoformat(), **fields}
    logger.info(json.dumps(payload, default=str))


def quarantine(entry: dict) -> None:
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), **entry}
    with QUARANTINE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
