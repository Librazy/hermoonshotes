"""Kimi Builtin Web Search - Native $web_search implementation."""

import json
import os
import logging
from typing import Any, Dict, List, Optional
import httpx

from tools.kimi_config import get_config, DEFAULT_SYSTEM_PROMPTS

logger = logging.getLogger(__name__)

KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")


def check_kimi_search_available() -> bool:
    """Check if Kimi API key is configured."""
    return bool(os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY"))


def _resolve_api_key() -> Optional[str]:
    """Resolve API key from environment."""
    return os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY")


def _build_kimi_client(api_key: str) -> httpx.Client:
    """Build HTTP client with auth headers."""
    return httpx.Client(
        base_url=KIMI_BASE_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        timeout=60.0
    )


def _execute_search_loop(
    client: httpx.Client,
    messages: List[Dict[str, Any]],
    model: str,
    max_rounds: int = 3
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
            
            choice = data.get("choices", [{}])[0]
            finish_reason = choice.get("finish_reason")
            message = choice.get("message", {})
            
            # If not a tool call, we're done
            if finish_reason != "tool_calls":
                return {
                    "content": message.get("content", ""),
                    "finish_reason": finish_reason,
                    "search_results": data.get("search_results", []),
                    "usage": data.get("usage", {})
                }
            
            # Handle tool calls - echo back arguments
            tool_calls = message.get("tool_calls", [])
            if not tool_calls:
                return {"error": "Expected tool_calls but none found"}
            
            # Add assistant message with tool_calls
            messages.append({
                "role": "assistant",
                "content": message.get("content", ""),
                "tool_calls": [
                    {
                        "id": tc.get("id"),
                        "type": "function",
                        "function": {
                            "name": tc.get("function", {}).get("name"),
                            "arguments": tc.get("function", {}).get("arguments", "{}")
                        }
                    }
                    for tc in tool_calls
                ]
            })
            
            # Add tool responses (echo arguments back)
            for tc in tool_calls:
                tc_id = tc.get("id")
                func_name = tc.get("function", {}).get("name", "")
                arguments = tc.get("function", {}).get("arguments", "{}")
                
                if func_name == "$web_search":
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "name": func_name,
                        "content": arguments  # Echo back for Kimi to execute
                    })
                else:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "name": func_name,
                        "content": json.dumps({"error": f"Unknown tool: {func_name}"})
                    })
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in round {round_num}: {e}")
            return {"error": f"HTTP error: {e}"}
        except Exception as e:
            logger.error(f"Error in round {round_num}: {e}")
            return {"error": str(e)}
    
    return {"error": "Max rounds exceeded without final answer"}


def kimi_builtin_search(
    query: str,
    model: str = "kimi-k2.5",
    format_style: str = "detailed",
    system_prompt: Optional[str] = None
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
    
    try:
        with _build_kimi_client(api_key) as client:
            result = _execute_search_loop(client, messages, model)
            
            if "error" in result:
                return json.dumps(result)
            
            # Format output
            output = {
                "query": query,
                "content": result.get("content", ""),
                "sources": [
                    {"title": sr.get("title"), "url": sr.get("url")}
                    for sr in result.get("search_results", [])
                ],
                "usage": result.get("usage", {})
            }
            
            return json.dumps(output)
            
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return json.dumps({"error": str(e)})


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
                    "enum": ["detailed", "brief", "structured", "academic"],
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


# --- Registration ---
# Note: The registry import is placed at the end to avoid circular imports
# when this module is imported during tool discovery.
try:
    from tools.registry import registry

    _config = get_config()
    _tool_name = KIMI_BUILTIN_SEARCH_SCHEMA["name"]

    registry.register(
        name=_tool_name,
        toolset="web",
        schema=KIMI_BUILTIN_SEARCH_SCHEMA,
        handler=lambda args, **kw: kimi_builtin_search(
            query=args.get("query", ""),
            model=args.get("model", "kimi-k2.5"),
            format_style=args.get("format_style", "detailed"),
            system_prompt=args.get("system_prompt")
        ),
        check_fn=check_kimi_search_available,
        requires_env=["MOONSHOT_API_KEY"],
    )
    logger.debug(f"Registered Kimi web search tool as: {_tool_name}")
except ImportError:
    # Registry not available during initial import (e.g., during testing)
    pass
