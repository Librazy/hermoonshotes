"""Kimi Formula Web Search - Forced web_search tool call via Formula API.

This module implements web search using the Kimi Formula API approach:
1. Call the formula web_search endpoint directly to get search results
2. Craft a chat completion with the tool call and search result already in context
3. This forces the model to work with actual search results rather than hallucinating

Transcript format (.jsonl):
- metadata: Session info, tool_args
- formula_request: The formula API request
- formula_response: The formula API response (including encrypted_output)
- chat_request: The chat completions request
- chat_response: The chat completions response
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

from .kimi_api_config import resolve_api_config
from .kimi_config import DEFAULT_SYSTEM_PROMPTS, get_config
from .kimi_transcript import SearchTranscriptManager

logger = logging.getLogger(__name__)

# Formula URI for web search
FORMULA_WEB_SEARCH = "moonshot/web-search:latest"


def check_kimi_search_available() -> bool:
    """Check if Kimi API key is configured."""
    api_key, base_url, warning = resolve_api_config()
    return api_key is not None and base_url is not None and warning is None


def _resolve_api_key() -> Optional[str]:
    """Resolve API key from environment."""
    api_key, _, _ = resolve_api_config()
    return api_key


def _resolve_base_url() -> Optional[str]:
    """Resolve base URL from environment."""
    _, base_url, _ = resolve_api_config()
    return base_url


def _build_kimi_client(api_key: str, base_url: str) -> httpx.Client:
    """Build HTTP client with auth headers."""
    return httpx.Client(
        base_url=base_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        timeout=120.0
    )


def _execute_formula_web_search(
    client: httpx.Client,
    query: str,
    transcript_manager: Optional[SearchTranscriptManager] = None,
) -> Dict[str, Any]:
    """
    Execute the formula web_search tool directly.

    Args:
        client: HTTP client for API calls
        query: Search query string
        transcript_manager: Optional transcript manager for logging

    Returns:
        Dict with status, result (or encrypted_output), and fiber info
    """
    formula_uri = FORMULA_WEB_SEARCH
    formula_payload = {
        "name": "web_search",
        "arguments": json.dumps({"query": query})
    }

    # Log formula request
    if transcript_manager is not None:
        transcript_manager.log_formula_request(formula_payload)

    try:
        response = client.post(
            f"/formulas/{formula_uri}/fibers",
            json=formula_payload
        )
        response.raise_for_status()
        data = response.json()

        # Log formula response
        if transcript_manager is not None:
            transcript_manager.log_formula_response(data)

        status = data.get("status", "")

        if status == "succeeded":
            context = data.get("context", {})
            # Try output first, then encrypted_output
            search_result = context.get("output")
            if search_result:
                return {
                    "status": "success",
                    "result": search_result,
                    "fiber_id": data.get("id"),
                    "encrypted": False,
                }

            # Handle encrypted output (standard for web-search)
            encrypted_result = context.get("encrypted_output")
            if encrypted_result:
                return {
                    "status": "success",
                    "result": encrypted_result,
                    "fiber_id": data.get("id"),
                    "encrypted": True,
                }

            return {
                "status": "error",
                "error": "No output or encrypted_output in response",
                "fiber_id": data.get("id"),
            }

        # Handle failed status
        error_msg = "Formula execution failed"
        if "error" in data:
            error_msg = f"Formula error: {data['error']}"
        elif "context" in data and "error" in data["context"]:
            error_msg = f"Formula error: {data['context']['error']}"

        return {
            "status": "error",
            "error": error_msg,
            "fiber_id": data.get("id"),
        }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error calling formula: {e}")
        error_result = {
            "status": "error",
            "error": f"HTTP error: {e}",
        }
        if transcript_manager is not None:
            transcript_manager.log_formula_response(
                error_result,
                http_code=e.response.status_code if e.response else None,
                http_message=str(e),
            )
        return error_result
    except Exception as e:
        logger.error(f"Error calling formula: {e}")
        error_result = {
            "status": "error",
            "error": str(e),
        }
        if transcript_manager is not None:
            transcript_manager.log_formula_response(
                error_result,
                http_message=str(e),
            )
        return error_result


def _execute_chat_with_search_result(
    client: httpx.Client,
    query: str,
    search_result: str,
    model: str,
    system_prompt: str,
    format_style: str = "detailed",
    transcript_manager: Optional[SearchTranscriptManager] = None,
) -> Dict[str, Any]:
    """
    Execute chat completion with the search result pre-populated as a tool response.

    This crafts the conversation history to make it appear as if:
    1. The assistant called the web_search tool
    2. The tool returned the search result
    3. Now the assistant should process and format the result

    Args:
        client: HTTP client for API calls
        query: Original search query
        search_result: The result from the formula web_search tool
        model: Model to use
        system_prompt: System prompt for formatting
        format_style: Output format style (enables JSON mode when "json")
        transcript_manager: Optional transcript manager for logging

    Returns:
        Dict with content, finish_reason, and usage
    """
    # Craft the tool schema for web_search
    tool_schema = {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "用于信息检索的网络搜索",
            "parameters": {
                "type": "object",
                "properties": {
                    "classes": {
                        "description": "要关注的搜索领域。如果未指定，则默认为 'all'。",
                        "items": {
                            "enum": [
                                "all",
                                "academic",
                                "social",
                                "library",
                                "finance",
                                "code",
                                "ecommerce",
                                "medical"
                            ],
                            "type": "string"
                        },
                        "type": "array"
                    },
                    "query": {
                        "description": "要搜索的内容",
                        "type": "string"
                    }
                },
                "required": ["query"],
                "type": "object"
            }
        }
    }

    # Build messages with forced tool call workflow
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "web_search:0",
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "arguments": json.dumps({"query": query, "classes": ["all"]})
                    }
                }
            ]
        },
        {
            "role": "tool",
            "tool_call_id": "web_search:0",
            "content": search_result
        }
    ]

    payload = {
        "model": model,
        "messages": messages,
        "tools": [tool_schema],
        "thinking": {"type": "disabled"}
    }

    # Enable JSON mode when format_style is "json"
    if format_style == "json":
        payload["response_format"] = {"type": "json_object"}

    # Log chat request
    if transcript_manager is not None:
        transcript_manager.log_chat_request(payload)

    try:
        response = client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        # Log chat response
        if transcript_manager is not None:
            transcript_manager.log_chat_response(data)

        choice = data.get("choices", [{}])[0]
        finish_reason = choice.get("finish_reason")
        message = choice.get("message", {})

        return {
            "content": message.get("content", ""),
            "finish_reason": finish_reason,
            "usage": data.get("usage", {})
        }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error in chat completion: {e}")
        error_result = {
            "error": f"HTTP error: {e}",
        }
        if transcript_manager is not None:
            transcript_manager.log_chat_response(
                error_result,
                http_code=e.response.status_code if e.response else None,
                http_message=str(e),
            )
        return error_result
    except Exception as e:
        logger.error(f"Error in chat completion: {e}")
        error_result = {"error": str(e)}
        if transcript_manager is not None:
            transcript_manager.log_chat_response(
                error_result,
                http_message=str(e),
            )
        return error_result


def kimi_formula_web_search(
    query: str,
    model: str = "kimi-k2.5",
    format_style: str = "detailed",
    system_prompt: Optional[str] = None,
    task_id: Optional[str] = None,
) -> str:
    """
    Execute Kimi web search using formula API with forced tool call.

    This approach:
    1. Calls the formula web_search endpoint directly (guarantees search happens)
    2. Crafts a chat completion with the tool call and result pre-populated
    3. The model formats the search results according to the system prompt

    Args:
        query: Search query string
        model: Kimi model (default: kimi-k2.5)
        format_style: Output format (detailed|brief|markdown|json|academic)
        system_prompt: Optional custom system prompt to override default
        task_id: Optional task ID for transcript tracking

    Returns:
        Plain text search result content on success, or JSON error payload on failure
    """
    api_key = _resolve_api_key()
    base_url = _resolve_base_url()
    if not api_key or not base_url:
        return json.dumps({
            "error": "Kimi API key not configured",
            "message": "Set MOONSHOT_API_KEY and MOONSHOT_BASE_URL environment variables, or KIMI_CN_API_KEY / KIMI_API_KEY"
        })

    # Get system prompt - parameter takes precedence over config
    if system_prompt:
        final_prompt = system_prompt
    else:
        config = get_config()
        final_prompt = config.get_system_prompt(format_style)

    # Create transcript manager for JSONL logging
    session_id = str(uuid4())
    tool_args = {
        "query": query,
        "model": model,
        "format_style": format_style,
        "system_prompt": final_prompt,
    }
    transcript_manager = FormulaWebSearchTranscriptManager(
        tool_name="web_search",
        registered_name=_get_schema_name(),
        session_id=session_id,
        tool_args=tool_args,
        task_id=task_id,
    )

    try:
        with _build_kimi_client(api_key, base_url) as client:
            # Step 1: Execute formula web_search
            search_result_data = _execute_formula_web_search(
                client,
                query,
                transcript_manager=transcript_manager,
            )

            if search_result_data.get("status") != "success":
                error_msg = search_result_data.get("error", "Unknown error")
                return json.dumps({
                    "error": "Formula web_search failed",
                    "message": error_msg,
                })

            search_result = search_result_data.get("result", "")

            # Step 2: Execute chat completion with forced tool context
            chat_result = _execute_chat_with_search_result(
                client,
                query,
                search_result,
                model,
                final_prompt,
                format_style=format_style,
                transcript_manager=transcript_manager,
            )

            if "error" in chat_result:
                return json.dumps(chat_result)

            return chat_result.get("content", "")

    except Exception as e:
        logger.error(f"Search failed: {e}")
        error_payload = {"error": str(e)}
        # Log exception
        transcript_manager.log_chat_response(
            error_payload,
            http_message=str(e),
        )
        return json.dumps(error_payload)


def _get_schema_name() -> str:
    """Get the schema name with configured prefix."""
    config = get_config()
    return config.apply_prefix("web_search")


def _get_schema() -> Dict[str, Any]:
    """Build the tool schema with dynamic name."""
    name = _get_schema_name()
    return {
        "name": name,
        "description": "Search the web using Kimi by Moonshot Formula API. Returns synthesized answers formatted per request from Kimi's AI.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string"
                },
                "model": {
                    "type": "string",
                    "description": "Kimi model to use (default: kimi-k2.5)",
                    "default": "kimi-k2.5"
                },
                "format_style": {
                    "type": "string",
                    "enum": ["detailed", "brief", "markdown", "json", "academic"],
                    "description": "Output format style",
                    "default": "detailed"
                },
                "system_prompt": {
                    "type": "string",
                    "description": "Optional custom system prompt to override default formatting",
                    "default": None
                }
            },
            "required": ["query"]
        }
    }


# Exported schema constant for tests and external consumers
KIMI_FORMULA_WEB_SEARCH_SCHEMA = _get_schema()


def get_formula_web_search_registration(toolset: str = "plugin_hermoonshotes_web") -> Dict[str, Any]:
    """Return the registration payload used by the Hermes plugin entrypoint."""
    schema = _get_schema()
    return {
        "name": schema["name"],
        "toolset": toolset,
        "schema": schema,
        "handler": lambda args, **kw: kimi_formula_web_search(
            query=args.get("query", ""),
            model=args.get("model", "kimi-k2.5"),
            format_style=args.get("format_style", "json"),
            system_prompt=args.get("system_prompt"),
            task_id=kw.get("task_id"),
        ),
        "check_fn": check_kimi_search_available,
    }


class FormulaWebSearchTranscriptManager(SearchTranscriptManager):
    """
    Extended transcript manager for formula web search.

    Records:
    - metadata: Session info
    - formula_request: The formula API call
    - formula_response: The formula API result
    - chat_request: The chat completions request
    - chat_response: The chat completions response
    """

    def log_formula_request(self, formula_payload: Dict[str, Any]) -> None:
        """Log the formula API request."""
        if not self._ensure_initialized():
            return

        timestamp = datetime.now(timezone.utc)
        entry = {
            "type": "formula_request",
            "timestamp": timestamp.isoformat(),
            "formula_uri": FORMULA_WEB_SEARCH,
            "payload": formula_payload,
        }
        self._append_line(entry)

    def log_formula_response(
        self,
        response_data: Any,
        http_code: Optional[int] = None,
        http_message: Optional[str] = None,
    ) -> None:
        """Log the formula API response."""
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
            "type": "formula_response",
            "timestamp": timestamp.isoformat(),
            "response": response_payload,
        }
        self._append_line(entry)

    def log_chat_request(self, chat_payload: Dict[str, Any]) -> None:
        """Log the chat completions request."""
        if not self._ensure_initialized():
            return

        timestamp = datetime.now(timezone.utc)
        entry = {
            "type": "chat_request",
            "timestamp": timestamp.isoformat(),
            "payload": chat_payload,
        }
        self._append_line(entry)

    def log_chat_response(
        self,
        response_data: Any,
        http_code: Optional[int] = None,
        http_message: Optional[str] = None,
    ) -> None:
        """Log the chat completions response."""
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
            "type": "chat_response",
            "timestamp": timestamp.isoformat(),
            "response": response_payload,
        }
        self._append_line(entry)
