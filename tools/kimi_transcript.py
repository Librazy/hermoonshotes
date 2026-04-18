"""Transcript helpers for Moonshot/Kimi plugin tool calls."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

TRANSCRIPTS_ENV_VAR = "KIMI_TOOLS_VERBOSE"
ALL_VALUES = {"1", "true", "all"}


def _get_hermes_home() -> Path:
    """Get Hermes home directory, creating it if necessary."""
    try:
        from hermes_constants import get_hermes_home
        return get_hermes_home()
    except ImportError:
        # Fallback for tests or when hermes_constants is not available
        home = os.getenv("HERMES_HOME")
        if home:
            return Path(home)
        # Default to ~/.hermes
        return Path.home() / ".hermes"


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
    transcripts_dir = _get_hermes_home() / "sessions" / "moonshot"
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


class SearchTranscriptManager:
    """Manages JSONL transcript for kimi_builtin_search with immediate append."""

    def __init__(
        self,
        tool_name: str,
        registered_name: str,
        session_id: str,
        tool_args: Dict[str, Any],
        task_id: Optional[str] = None,
    ):
        self.tool_name = tool_name
        self.registered_name = registered_name
        self.session_id = session_id
        self.tool_args = tool_args
        self.task_id = task_id
        self.round_index = 0
        self.file_path: Optional[Path] = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Initialize transcript file if not already done. Returns True if enabled."""
        if self._initialized:
            return self.file_path is not None

        self._initialized = True

        if not should_save_transcript(self.tool_name):
            return False

        timestamp = datetime.now(timezone.utc)
        transcripts_dir = _get_hermes_home() / "sessions" / "moonshot"
        transcripts_dir.mkdir(parents=True, exist_ok=True)

        filename = (
            f"{timestamp.strftime('%Y%m%dT%H%M%S.%fZ')}"
            f"-{self.tool_name}-{self.session_id}.jsonl"
        )
        self.file_path = transcripts_dir / filename

        # Write metadata line
        metadata = {
            "type": "metadata",
            "timestamp": timestamp.isoformat(),
            "session_id": self.session_id,
            "tool_name": self.tool_name,
            "registered_name": self.registered_name,
            "task_id": self.task_id,
            "tool_args": self.tool_args,
        }
        self._append_line(metadata)
        return True

    def _append_line(self, data: Dict[str, Any]) -> None:
        """Append a single JSON line to the transcript file."""
        if self.file_path is None:
            return
        line = json.dumps(data, ensure_ascii=False, sort_keys=True)
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def log_request(self, messages: List[Dict[str, Any]]) -> None:
        """Log a request with new messages for the current round."""
        if not self._ensure_initialized():
            return

        self.round_index += 1
        timestamp = datetime.now(timezone.utc)

        entry = {
            "type": "request",
            "timestamp": timestamp.isoformat(),
            "round": self.round_index,
            "messages": messages,
        }
        self._append_line(entry)

    def log_response(
        self,
        response_data: Any,
        http_code: Optional[int] = None,
        http_message: Optional[str] = None,
    ) -> None:
        """
        Log a response for the current round.

        If response_data is a dict, it's saved directly.
        Otherwise, http_code and http_message should be provided.
        """
        if not self._ensure_initialized():
            return

        timestamp = datetime.now(timezone.utc)

        # Try to parse response as JSON object
        if isinstance(response_data, dict):
            response_payload = response_data
        elif isinstance(response_data, str):
            try:
                parsed = json.loads(response_data)
                if isinstance(parsed, dict):
                    response_payload = parsed
                else:
                    response_payload = {
                        "raw": response_data,
                        "parsed": parsed,
                    }
            except json.JSONDecodeError:
                response_payload = {
                    "http_code": http_code,
                    "http_message": http_message,
                    "body": response_data,
                }
        else:
            response_payload = {
                "http_code": http_code,
                "http_message": http_message,
                "body": str(response_data) if response_data is not None else None,
            }

        entry = {
            "type": "response",
            "timestamp": timestamp.isoformat(),
            "round": self.round_index,
            "response": response_payload,
        }
        self._append_line(entry)

    def get_file_path(self) -> Optional[Path]:
        """Return the transcript file path if initialized."""
        return self.file_path
