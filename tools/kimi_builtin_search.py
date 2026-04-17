"""Kimi Builtin Web Search - Native ``$web_search`` implementation."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from .kimi_config import DEFAULT_SYSTEM_PROMPTS, get_config
from .kimi_transcript import save_tool_transcript

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"


def check_kimi_search_available() -> bool:
    """Check if Kimi API key is configured."""
    return bool(os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY"))


def _resolve_api_key() -> Optional[str]:
    """Resolve API key from environment."""
    return os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY")


def _build_kimi_client(api_key: str) -> httpx.Client:
    """Build HTTP client with auth headers."""
    return httpx.Client(
        base_url=os.getenv("KIMI_BASE_URL") or os.getenv("MOONSHOT_BASE_URL") or DEFAULT_BASE_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        timeout=120.0
    )


def _execute_search_loop(
    client: httpx.Client,
    messages: List[Dict[str, Any]],
    model: str,
    max_rounds: int = 3,
    transcript_rounds: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Execute the search tool call loop.
    
    This handles the multi-turn conversation where Kimi:
    1. Requests the web_search tool
    2. We return the tool arguments
    3. Kimi executes search and returns formatted results
    """
    for round_num in range(max_rounds):
        payload = {
            "model": model,
            "messages": messages,
            "tools": [{
                "type": "builtin_function",
                "function": {"name": "$web_search"}
            }],
            "thinking": {"type": "disabled"}
        }

        try:
            response = client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            if transcript_rounds is not None:
                transcript_rounds.append(
                    {
                        "round": round_num + 1,
                        "request": payload,
                        "response": data,
                    }
                )
            
            choice = data.get("choices", [{}])[0]
            finish_reason = choice.get("finish_reason")
            message = choice.get("message", {})
            
            # If not a tool call, we're done
            if finish_reason != "tool_calls":
                return {
                    "content": message.get("content", ""),
                    "finish_reason": finish_reason,
                    "usage": data.get("usage", {})
                }
            
            # Handle tool calls - echo back arguments
            tool_calls = message.get("tool_calls", [])
            if not tool_calls:
                return {"error": "Expected tool_calls but none found"}
            
            # Add assistant message with tool_calls
            messages.append(message)
            
            # Add tool responses (echo arguments back)
            for tc in tool_calls:
                tc_id = tc.get("id")
                func_name = tc.get("function", {}).get("name", "")
                arguments = tc.get("function", {}).get("arguments", "{}")
                
                if func_name == "$web_search":
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": arguments  # Echo back for Kimi to execute
                    })
                else:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": json.dumps({"error": f"Unknown tool: {func_name}"})
                    })
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in round {round_num}: {e}")
            if transcript_rounds is not None:
                transcript_rounds.append(
                    {
                        "round": round_num + 1,
                        "request": payload,
                        "error": f"HTTP error: {e}",
                    }
                )
            return {"error": f"HTTP error: {e}"}
        except Exception as e:
            logger.error(f"Error in round {round_num}: {e}")
            if transcript_rounds is not None:
                transcript_rounds.append(
                    {
                        "round": round_num + 1,
                        "request": payload,
                        "error": str(e),
                    }
                )
            return {"error": str(e)}
    
    return {"error": "Max rounds exceeded without final answer"}


def kimi_builtin_search(
    query: str,
    model: str = "kimi-k2.5",
    format_style: str = "detailed",
    system_prompt: Optional[str] = None,
    task_id: Optional[str] = None,
) -> str:
    """
    Execute Kimi builtin web search.
    
    Args:
        query: Search query string
        model: Kimi model (default: kimi-k2.5)
        format_style: Output format (detailed|brief|structured|academic)
        system_prompt: Optional custom system prompt to override default
    
    Returns:
        JSON string with search results
    """
    api_key = _resolve_api_key()
    if not api_key:
        return json.dumps({
            "error": "Kimi API key not configured",
            "message": "Set MOONSHOT_API_KEY or KIMI_API_KEY environment variable"
        })
    
    # Get system prompt - parameter takes precedence over config
    if system_prompt:
        final_prompt = system_prompt
    else:
        config = get_config()
        final_prompt = config.get_system_prompt(format_style)
    
    messages = [
        {"role": "system", "content": final_prompt},
        {"role": "user", "content": query}
    ]
    transcript_rounds: List[Dict[str, Any]] = []
    
    try:
        with _build_kimi_client(api_key) as client:
            result = _execute_search_loop(
                client,
                messages,
                model,
                transcript_rounds=transcript_rounds,
            )
            
            if "error" in result:
                save_tool_transcript(
                    "web_search",
                    _get_schema_name(),
                    {
                        "query": query,
                        "model": model,
                        "format_style": format_style,
                        "system_prompt": final_prompt,
                    },
                    result,
                    task_id=task_id,
                    metadata={"rounds": transcript_rounds},
                )
                return json.dumps(result)
            
            # Format output
            output = {
                "query": query,
                "content": result.get("content", ""),
                "usage": result.get("usage", {})
            }
            save_tool_transcript(
                "web_search",
                _get_schema_name(),
                {
                    "query": query,
                    "model": model,
                    "format_style": format_style,
                    "system_prompt": final_prompt,
                },
                output,
                task_id=task_id,
                metadata={"rounds": transcript_rounds},
            )
            
            return result.get("content", "")
            
    except Exception as e:
        logger.error(f"Search failed: {e}")
        error_payload = {"error": str(e)}
        save_tool_transcript(
            "web_search",
            _get_schema_name(),
            {
                "query": query,
                "model": model,
                "format_style": format_style,
                "system_prompt": final_prompt,
            },
            error_payload,
            task_id=task_id,
            metadata={"rounds": transcript_rounds},
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
        "description": "Search the web using Kimi's native $web_search. Returns formatted results with citations.",
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
                    "enum": ["detailed", "brief", "markdown", "structured", "academic"],
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
KIMI_BUILTIN_SEARCH_SCHEMA = _get_schema()


def get_builtin_search_registration(toolset: str = "plugin_hermoonshotes_web") -> Dict[str, Any]:
    """Return the registration payload used by the Hermes plugin entrypoint."""
    schema = _get_schema()
    return {
        "name": schema["name"],
        "toolset": toolset,
        "schema": schema,
        "handler": lambda args, **kw: kimi_builtin_search(
            query=args.get("query", ""),
            model=args.get("model", "kimi-k2.5"),
            format_style=args.get("format_style", "structured"),
            system_prompt=args.get("system_prompt"),
            task_id=kw.get("task_id"),
        ),
        "check_fn": check_kimi_search_available,
        "requires_env": ["MOONSHOT_API_KEY"],
    }
