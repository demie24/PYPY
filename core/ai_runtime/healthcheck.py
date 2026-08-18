"""Container healthcheck for model readiness, not merely process existence."""

import json
import os
import sys
import time
from pathlib import Path


component = os.environ["MODEL_COMPONENT"]
path = Path(f"/tmp/pypy_{component}_heartbeat.json")
try:
    status = json.loads(path.read_text(encoding="utf-8"))
    age = time.time() - path.stat().st_mtime
    healthy = status.get("ready") is True and status.get("model_loaded") is True and age <= 20.0
except (OSError, ValueError, TypeError):
    healthy = False
raise SystemExit(0 if healthy else 1)
