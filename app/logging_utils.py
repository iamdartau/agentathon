import json
import os
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(os.environ.get("LOG_DIR", "logs"))
LOG_DIR.mkdir(exist_ok=True)
TRACE_PATH = LOG_DIR / "agent_trace.jsonl"


def log_event(
    run_id: str,
    agent: str,
    action: str,
    input_summary: str,
    output_summary: str,
    target_agent: str | None = None,
    confidence: float | None = None,
    retry_count: int = 0,
    status: str = "success",
) -> dict:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "agent_name": agent,
        "action": action,
        "input_summary": input_summary[:300],
        "output_summary": output_summary[:300],
        "target_agent": target_agent,
        "confidence": confidence,
        "retry_count": retry_count,
        "status": status,
        "sample_mode": os.environ.get("SAMPLE_MODE", "false").lower() == "true",
    }
    line = json.dumps(event, ensure_ascii=False)
    print(line, flush=True)
    with TRACE_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return event
