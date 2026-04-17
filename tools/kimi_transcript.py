"""Transcript helpers for Moonshot/Kimi plugin tool calls."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from hermes_constants import get_hermes_home

TRANSCRIPTS_ENV_VAR = "KIMI_TOOLS_VERBOSE"
ALL_VALUES = {"1", "true", "all"}


def should_save_transcript(tool_name: str) -> bool:
    """Return True when transcript capture is enabled for ``tool_name``."""
    raw = (os.getenv(TRANSCRIPTS_ENV_VAR) or "").strip()
    if not raw:
        return False

    normalized = raw.lower()
    if normalized in ALL_VALUES:
        return True

    enabled_tools = {
        item.strip().lower()
        for item in raw.split(",")
        if item.strip()
    }
    return tool_name.lower() in enabled_tools


def save_tool_transcript(
    tool_name: str,
    registered_name: str,
    request: Dict[str, Any],
    response: Dict[str, Any],
    *,
    task_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Path]:
    """Persist a tool transcript under ``sessions/moonshot`` when enabled."""
    if not should_save_transcript(tool_name):
        return None

    timestamp = datetime.now(timezone.utc)
    transcripts_dir = get_hermes_home() / "sessions" / "moonshot"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "saved_at": timestamp.isoformat(),
        "tool_name": tool_name,
        "registered_name": registered_name,
        "task_id": task_id,
        "request": request,
        "response": response,
        "metadata": metadata or {},
    }

    filename = (
        f"{timestamp.strftime('%Y%m%dT%H%M%S.%fZ')}"
        f"-{tool_name}-{uuid4().hex[:8]}.json"
    )
    output_path = transcripts_dir / filename
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path
