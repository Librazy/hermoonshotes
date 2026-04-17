# Implementation Plan: Kimi Web Search & Formula Tools for Hermes Agent

## Executive Summary

This document outlines the integration of Moonshot/Kimi AI's search capabilities into Hermes Agent, supporting:
1. **Builtin `$web_search`** - Native Kimi web search with customizable output formatting
2. **Formula tools** - Additional tools like `fetch`, `convert`, `code_runner`, etc.

The integration follows the same architectural pattern used by OpenClaw's Moonshot plugin, decoupling web search from the model provider.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Builtin `$web_search` Implementation](#2-builtin-web_search-implementation)
3. [Formula Tools Implementation](#3-formula-tools-implementation)
4. [Configuration & Credentials](#4-configuration--credentials)
5. [Testing Strategy](#5-testing-strategy)
6. [Deployment Checklist](#6-deployment-checklist)

---

## 1. Architecture Overview

### 1.1 Design Principles

Based on OpenClaw's implementation:

| Principle | Description |
|-----------|-------------|
| **Decoupled** | Web search works independently of the LLM provider (OpenAI, Anthropic, etc.) |
| **Pluggable** | Tools register via Hermes registry, auto-discovered at startup |
| **Configurable** | Supports API keys via env vars or config files |
| **Fallback Chain** | Multiple credential sources with clear priority |

### 1.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hermes Agent                             │
│                                                                 │
│  ┌──────────────────────┐     ┌──────────────────────────────┐ │
│  │   Tool Registry      │────▶│  Tool Dispatcher             │ │
│  │  (tools/registry.py) │     │  (run_agent.py)              │ │
│  └──────────────────────┘     └──────────────────────────────┘ │
│              │                            │                    │
│              ▼                            ▼                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Kimi Tool Module                              │  │
│  │         (tools/kimi_tools.py)                              │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │  │
│  │  │Builtin Search│    │ Formula Fetch│    │ Formula Code │  │  │
│  │  │  ($web_search)│    │   (fetch)    │    │   (runner)   │  │  │
│  │  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │  │
│  │         │                   │                   │           │  │
│  │         └───────────────────┼───────────────────┘           │  │
│  │                             ▼                               │  │
│  │                  ┌─────────────────────┐                   │  │
│  │                  │  Kimi API Client      │                   │  │
│  │                  │  (httpx-based)      │                   │  │
│  │                  └──────────┬──────────┘                   │  │
│  │                             │                               │  │
│  └─────────────────────────────┼───────────────────────────────┘  │
│                                │                                 │
└────────────────────────────────┼─────────────────────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────┐
                  │   Moonshot/Kimi API       │
                  │   api.moonshot.cn/v1      │
                  │                           │
                  │  • /chat/completions      │
                  │  • /formulas/{uri}/tools  │
                  │  • /formulas/{uri}/fibers │
                  └──────────────────────────┘
```

### 1.3 File Structure

```
hermes/
├── tools/
│   ├── kimi_tools.py          # Main tool implementations
│   ├── kimi_search.py         # Builtin search specific
│   ├── kimi_formula.py        # Formula tools wrapper
│   └── registry.py            # Existing registry (modified)
├── toolsets.py                # Add to _HERMES_CORE_TOOLS
├── hermes_cli/
│   └── config.py              # Add OPTIONAL_ENV_VARS
└── tests/
    └── tools/
        └── test_kimi_tools.py # Unit tests
```

---

## 2. Builtin `$web_search` Implementation

### 2.1 Key Characteristics

- **Endpoint**: `POST /chat/completions`
- **Tool Type**: `builtin_function` with `name: "$web_search"`
- **Requirement**: Must disable thinking (`thinking: {type: "disabled"}`)
- **Execution Flow**: 2-step process (request tool → return args → get answer)

### 2.2 Implementation Details

#### 2.2.1 Tool Definition

```python
KIMI_WEB_SEARCH_TOOL = {
    "type": "builtin_function",
    "function": {"name": "$web_search"}
}
```

#### 2.2.2 System Prompt Strategy

Custom system prompts control output format:

| Format | Use Case | System Prompt Focus |
|--------|----------|---------------------|
| `detailed` | General queries | Full summary + citations |
| `brief` | Quick facts | 1-2 sentences + URLs |
| `structured` | Data extraction | JSON/markdown tables |
| `academic` | Research | APA citations, methodology |

#### 2.2.3 Request/Response Flow

```
Step 1: Initial Request
┌────────────────────────────────────┐
│ POST /chat/completions             │
│ {                                  │
│   "model": "kimi-k2.5",            │
│   "messages": [                    │
│     {"role": "system", "content":  │
│       "Custom system prompt..."},  │
│     {"role": "user", "content":     │
│       "Search for..."}              │
│   ],                               │
│   "tools": [{                      │
│     "type": "builtin_function",    │
│     "function": {"name":            │
│       "$web_search"}               │
│   }],                              │
│   "thinking": {"type": "disabled"}  │
│ }                                  │
└────────────────────────────────────┘
                │
                ▼
Step 2: Tool Call Response
┌────────────────────────────────────┐
│ {                                  │
│   "choices": [{                   │
│     "finish_reason": "tool_calls", │
│     "message": {                   │
│       "tool_calls": [{            │
│         "id": "web_search:0",      │
│         "function": {              │
│           "name": "$web_search",   │
│           "arguments": "{...}"      │
│         }                          │
│       }]                           │
│     }                              │
│   }]                               │
│ }                                  │
└────────────────────────────────────┘
                │
                ▼
Step 3: Return Tool Results
┌────────────────────────────────────┐
│ POST /chat/completions             │
│ {                                  │
│   "messages": [                    │
│     ...previous messages...,       │
│     {"role": "assistant",           │
│      "tool_calls": [...]},         │
│     {"role": "tool",                │
│      "tool_call_id": "web_search:0",│
│      "name": "$web_search",        │
│      "content": "{...}"}            │
│   ],                               │
│   "tools": [...]                   │
│ }                                  │
└────────────────────────────────────┘
                │
                ▼
Step 4: Final Answer
┌────────────────────────────────────┐
│ {                                  │
│   "choices": [{                   │
│     "finish_reason": "stop",       │
│     "message": {                   │
│       "content": "Search results...│
│        formatted per system       │
│        prompt instructions"        │
│     }                              │
│   }],                              │
│   "search_results": [...]          │
│ }                                  │
└────────────────────────────────────┘
```

### 2.3 Code Implementation

#### File: `tools/kimi_builtin_search.py`

```python
"""Kimi Builtin Web Search - Native $web_search implementation."""

import json
import os
import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")

# Default system prompts for different output formats
DEFAULT_SYSTEM_PROMPTS = {
    "detailed": """你是 Kimi，具有联网搜索能力的 AI 助手。

当使用 $web_search 工具搜索后，按以下格式输出：

## 搜索结果摘要
[2-3句话概括核心内容]

## 详细信息
[详细回答，包含具体数据]

## 引用来源
- [标题](URL)
- [标题](URL)

保持回答在500字以内。""",

    "brief": """你是 Kimi。搜索后给出1-2句话的简短回答，并列出主要来源URL。""",

    "structured": """你是 Kimi。搜索后用 markdown 表格呈现关键数据。""",

    "academic": """你是 Kimi。搜索后以学术格式输出，使用 APA 引用格式。"""
}


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
    format_style: str = "detailed"
) -> str:
    """
    Execute Kimi builtin web search.
    
    Args:
        query: Search query string
        model: Kimi model (default: kimi-k2.5)
        format_style: Output format (detailed|brief|structured|academic)
    
    Returns:
        JSON string with search results
    """
    api_key = _resolve_api_key()
    if not api_key:
        return json.dumps({
            "error": "Kimi API key not configured",
            "message": "Set MOONSHOT_API_KEY or KIMI_API_KEY environment variable"
        })
    
    # Validate format style
    if format_style not in DEFAULT_SYSTEM_PROMPTS:
        format_style = "detailed"
    
    system_prompt = DEFAULT_SYSTEM_PROMPTS[format_style]
    
    messages = [
        {"role": "system", "content": system_prompt},
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


# --- Schema Definition ---

KIMI_BUILTIN_SEARCH_SCHEMA = {
    "name": "kimi_web_search",
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
            }
        },
        "required": ["query"]
    }
}


# --- Registration ---
from tools.registry import registry

registry.register(
    name="kimi_web_search",
    toolset="web",
    schema=KIMI_BUILTIN_SEARCH_SCHEMA,
    handler=lambda args, **kw: kimi_builtin_search(
        query=args.get("query", ""),
        model=args.get("model", "kimi-k2.5"),
        format_style=args.get("format_style", "detailed")
    ),
    check_fn=check_kimi_search_available,
    requires_env=["MOONSHOT_API_KEY"],
)
```

---

## 3. Formula Tools Implementation

### 3.1 Available Formula Tools

Per `use-official-tools.md`:

| Formula URI | Tool Name | Purpose |
|-------------|-----------|---------|
| `moonshot/web-search:latest` | `web_search` | Web search (encrypted output) |
| `moonshot/fetch:latest` | `fetch` | URL content extraction |
| `moonshot/convert:latest` | `convert` | Unit conversion |
| `moonshot/date:latest` | `date` | Date/time operations |
| `moonshot/base64:latest` | `base64` | Encoding/decoding |
| `moonshot/quickjs:latest` | `quickjs` | JavaScript execution |
| `moonshot/code_runner:latest` | `code_runner` | Python code execution |
| `moonshot/excel:latest` | `excel` | Excel/CSV analysis |

### 3.2 API Flow

```
Step 1: Get Tool Definition
┌────────────────────────────────────┐
│ GET /formulas/{uri}/tools          │
│ Response:                          │
│ {                                  │
│   "tools": [{                      │
│     "type": "function",            │
│     "function": {                  │
│       "name": "fetch",             │
│       "description": "...",        │
│       "parameters": {...}          │
│     }                              │
│   }]                               │
│ }                                  │
└────────────────────────────────────┘
                │
                ▼
Step 2: Execute Tool
┌────────────────────────────────────┐
│ POST /formulas/{uri}/fibers        │
│ {                                  │
│   "name": "fetch",                 │
│   "arguments": "{\"url\": \"...\"}" │
│ }                                  │
└────────────────────────────────────┘
                │
                ▼
Step 3: Get Result
┌────────────────────────────────────┐
│ {                                  │
│   "status": "succeeded",           │
│   "context": {                     │
│     "output": "...",               │
│     "encrypted_output": "..."       │
│   }                                │
│ }                                  │
└────────────────────────────────────┘
```

### 3.3 Implementation

#### File: `tools/kimi_formula_tools.py`

```python
"""Kimi Formula Tools - Official Moonshot formula tools."""

import json
import os
import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")

# Formula registry
FORMULAS = {
    "web_search": "moonshot/web-search:latest",
    "fetch": "moonshot/fetch:latest",
    "convert": "moonshot/convert:latest",
    "date": "moonshot/date:latest",
    "base64": "moonshot/base64:latest",
    "quickjs": "moonshot/quickjs:latest",
    "code_runner": "moonshot/code_runner:latest",
    "excel": "moonshot/excel:latest",
}


class KimiFormulaClient:
    """Client for Kimi Formula API."""
    
    def __init__(self, api_key: str, base_url: str = KIMI_BASE_URL):
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )
    
    def get_tool_schema(self, formula_uri: str) -> Optional[Dict]:
        """Fetch tool schema from formula."""
        try:
            response = self.client.get(f"/formulas/{formula_uri}/tools")
            response.raise_for_status()
            data = response.json()
            tools = data.get("tools", [])
            return tools[0] if tools else None
        except Exception as e:
            logger.error(f"Failed to get schema for {formula_uri}: {e}")
            return None
    
    def execute_tool(
        self,
        formula_uri: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a formula tool."""
        try:
            payload = {
                "name": tool_name,
                "arguments": json.dumps(arguments)
            }
            
            response = self.client.post(
                f"/formulas/{formula_uri}/fibers",
                json=payload
            )
            response.raise_for_status()
            fiber = response.json()
            
            status = fiber.get("status")
            context = fiber.get("context", {})
            
            if status == "succeeded":
                # Prefer output, fall back to encrypted_output
                output = context.get("output") or context.get("encrypted_output")
                return {
                    "status": "success",
                    "result": output,
                    "fiber_id": fiber.get("id")
                }
            
            # Handle errors
            error = fiber.get("error") or context.get("error") or context.get("output")
            return {
                "status": "error",
                "error": error,
                "fiber_id": fiber.get("id")
            }
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error executing {tool_name}: {e}")
            return {"status": "error", "error": str(e)}
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {e}")
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """Close HTTP client."""
        self.client.close()


def check_formula_tools_available() -> bool:
    """Check if API key is configured."""
    return bool(os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY"))


def _get_client() -> Optional[KimiFormulaClient]:
    """Get configured client."""
    api_key = os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY")
    if not api_key:
        return None
    return KimiFormulaClient(api_key)


# --- Individual Tool Handlers ---

def kimi_fetch_tool(url: str) -> str:
    """Fetch URL content."""
    client = _get_client()
    if not client:
        return json.dumps({"error": "Kimi API key not configured"})
    
    try:
        result = client.execute_tool(
            FORMULAS["fetch"],
            "fetch",
            {"url": url}
        )
        return json.dumps(result)
    finally:
        client.close()


def kimi_convert_tool(value: float, from_unit: str, to_unit: str) -> str:
    """Convert units."""
    client = _get_client()
    if not client:
        return json.dumps({"error": "Kimi API key not configured"})
    
    try:
        result = client.execute_tool(
            FORMULAS["convert"],
            "convert",
            {
                "value": value,
                "from_unit": from_unit,
                "to_unit": to_unit
            }
        )
        return json.dumps(result)
    finally:
        client.close()


def kimi_quickjs_tool(code: str) -> str:
    """Execute JavaScript code."""
    client = _get_client()
    if not client:
        return json.dumps({"error": "Kimi API key not configured"})
    
    try:
        result = client.execute_tool(
            FORMULAS["quickjs"],
            "quickjs",
            {"code": code}
        )
        return json.dumps(result)
    finally:
        client.close()


def kimi_code_runner_tool(code: str, language: str = "python") -> str:
    """Execute code (Python/JS)."""
    client = _get_client()
    if not client:
        return json.dumps({"error": "Kimi API key not configured"})
    
    try:
        result = client.execute_tool(
            FORMULAS["code_runner"],
            "code_runner",
            {"code": code, "language": language}
        )
        return json.dumps(result)
    finally:
        client.close()


def kimi_excel_tool(file_content: str, operation: str = "analyze") -> str:
    """Analyze Excel/CSV content."""
    client = _get_client()
    if not client:
        return json.dumps({"error": "Kimi API key not configured"})
    
    try:
        result = client.execute_tool(
            FORMULAS["excel"],
            "excel",
            {"content": file_content, "operation": operation}
        )
        return json.dumps(result)
    finally:
        client.close()


# --- Schemas ---

KIMI_FETCH_SCHEMA = {
    "name": "kimi_fetch",
    "description": "Fetch and extract content from a URL using Kimi Formula API. Returns markdown-formatted content.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch content from"
            }
        },
        "required": ["url"]
    }
}

KIMI_CONVERT_SCHEMA = {
    "name": "kimi_convert",
    "description": "Convert between units (length, mass, volume, temperature, currency, etc.)",
    "parameters": {
        "type": "object",
        "properties": {
            "value": {
                "type": "number",
                "description": "Value to convert"
            },
            "from_unit": {
                "type": "string",
                "description": "Source unit (e.g., 'meters', 'kg', 'celsius')"
            },
            "to_unit": {
                "type": "string",
                "description": "Target unit (e.g., 'feet', 'lbs', 'fahrenheit')"
            }
        },
        "required": ["value", "from_unit", "to_unit"]
    }
}

KIMI_QUICKJS_SCHEMA = {
    "name": "kimi_quickjs",
    "description": "Execute JavaScript code safely using QuickJS engine",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "JavaScript code to execute"
            }
        },
        "required": ["code"]
    }
}

KIMI_CODE_RUNNER_SCHEMA = {
    "name": "kimi_code_runner",
    "description": "Execute Python code safely in sandboxed environment",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            },
            "language": {
                "type": "string",
                "enum": ["python", "javascript"],
                "default": "python"
            }
        },
        "required": ["code"]
    }
}


# --- Registration ---
from tools.registry import registry

registry.register(
    name="kimi_fetch",
    toolset="web",
    schema=KIMI_FETCH_SCHEMA,
    handler=lambda args, **kw: kimi_fetch_tool(args.get("url", "")),
    check_fn=check_formula_tools_available,
    requires_env=["MOONSHOT_API_KEY"],
)

registry.register(
    name="kimi_convert",
    toolset="utility",
    schema=KIMI_CONVERT_SCHEMA,
    handler=lambda args, **kw: kimi_convert_tool(
        args.get("value", 0),
        args.get("from_unit", ""),
        args.get("to_unit", "")
    ),
    check_fn=check_formula_tools_available,
    requires_env=["MOONSHOT_API_KEY"],
)

registry.register(
    name="kimi_quickjs",
    toolset="utility",
    schema=KIMI_QUICKJS_SCHEMA,
    handler=lambda args, **kw: kimi_quickjs_tool(args.get("code", "")),
    check_fn=check_formula_tools_available,
    requires_env=["MOONSHOT_API_KEY"],
)

registry.register(
    name="kimi_code_runner",
    toolset="utility",
    schema=KIMI_CODE_RUNNER_SCHEMA,
    handler=lambda args, **kw: kimi_code_runner_tool(
        args.get("code", ""),
        args.get("language", "python")
    ),
    check_fn=check_formula_tools_available,
    requires_env=["MOONSHOT_API_KEY"],
)
```

---

## 4. Configuration & Credentials

### 4.1 Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `MOONSHOT_API_KEY` | Primary API key | Yes (or `KIMI_API_KEY`) |
| `KIMI_API_KEY` | Alternative API key | Yes (or `MOONSHOT_API_KEY`) |
| `KIMI_BASE_URL` | API base URL | No (default: https://api.moonshot.cn/v1) |

### 4.2 Hermes CLI Configuration

Update `hermes_cli/config.py`:

```python
OPTIONAL_ENV_VARS = {
    # ... existing vars ...
    
    "MOONSHOT_API_KEY": {
        "description": "Moonshot/Kimi API key for web search and formula tools",
        "prompt": "Moonshot API key (get from https://platform.moonshot.cn/)",
        "url": "https://platform.moonshot.cn/",
        "tools": [
            "kimi_web_search",
            "kimi_fetch",
            "kimi_convert",
            "kimi_quickjs",
            "kimi_code_runner"
        ],
        "password": True,
    },
}
```

### 4.3 Toolset Configuration

Update `toolsets.py`:

```python
_HERMES_CORE_TOOLS = [
    # ... existing tools ...
    "kimi_web_search",
    "kimi_fetch",
]

# Or create dedicated toolsets
KIMI_TOOLSETS = {
    "kimi_search": {
        "description": "Kimi AI web search tools",
        "tools": ["kimi_web_search"],
        "includes": []
    },
    "kimi_utility": {
        "description": "Kimi formula utility tools",
        "tools": ["kimi_fetch", "kimi_convert", "kimi_quickjs", "kimi_code_runner"],
        "includes": []
    },
    "kimi_all": {
        "description": "All Kimi tools",
        "tools": ["kimi_web_search", "kimi_fetch", "kimi_convert", "kimi_quickjs", "kimi_code_runner"],
        "includes": []
    }
}
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

File: `tests/tools/test_kimi_tools.py`

```python
"""Tests for Kimi tools integration."""

import json
import os
import pytest
from unittest.mock import Mock, patch

from tools.kimi_builtin_search import (
    check_kimi_search_available,
    kimi_builtin_search,
    _resolve_api_key,
)
from tools.kimi_formula_tools import (
    check_formula_tools_available,
    KimiFormulaClient,
)


class TestKimiBuiltinSearch:
    """Test builtin $web_search functionality."""
    
    def test_check_available_with_key(self):
        """Tool available when API key set."""
        with patch.dict(os.environ, {"MOONSHOT_API_KEY": "sk-test"}):
            assert check_kimi_search_available() is True
    
    def test_check_available_without_key(self):
        """Tool unavailable when no API key."""
        with patch.dict(os.environ, {}, clear=True):
            assert check_kimi_search_available() is False
    
    def test_resolve_api_key_priority(self):
        """MOONSHOT_API_KEY takes priority."""
        with patch.dict(os.environ, {
            "MOONSHOT_API_KEY": "sk-moonshot",
            "KIMI_API_KEY": "sk-kimi"
        }):
            assert _resolve_api_key() == "sk-moonshot"
    
    def test_search_returns_error_without_key(self):
        """Search returns error JSON when no API key."""
        with patch.dict(os.environ, {}, clear=True):
            result = kimi_builtin_search("test query")
            data = json.loads(result)
            assert "error" in data
            assert "MOONSHOT_API_KEY" in data.get("message", "")

    @patch("httpx.Client.post")
    def test_search_success_flow(self, mock_post):
        """Test successful search with tool call loop."""
        # First response: tool call request
        first_response = {
            "choices": [{
                "finish_reason": "tool_calls",
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "web_search:0",
                        "function": {
                            "name": "$web_search",
                            "arguments": '{"query": "test"}'
                        }
                    }]
                }
            }]
        }
        
        # Second response: final answer
        second_response = {
            "choices": [{
                "finish_reason": "stop",
                "message": {
                    "content": "Search results here"
                }
            }],
            "search_results": [
                {"title": "Result 1", "url": "https://example.com"}
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50
            }
        }
        
        mock_post.side_effect = [
            Mock(status_code=200, json=lambda: first_response),
            Mock(status_code=200, json=lambda: second_response)
        ]
        
        with patch.dict(os.environ, {"MOONSHOT_API_KEY": "sk-test"}):
            result = kimi_builtin_search("test query")
            data = json.loads(result)
            
            assert "content" in data
            assert "sources" in data
            assert "usage" in data


class TestKimiFormulaTools:
    """Test formula tool functionality."""
    
    def test_client_execute_success(self):
        """Test successful formula execution."""
        client = KimiFormulaClient("sk-test")
        
        with patch.object(client.client, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "status": "succeeded",
                    "id": "fiber-123",
                    "context": {
                        "output": "Fetched content"
                    }
                }
            )
            
            result = client.execute_tool(
                "moonshot/fetch:latest",
                "fetch",
                {"url": "https://example.com"}
            )
            
            assert result["status"] == "success"
            assert result["result"] == "Fetched content"
            
        client.close()


class TestIntegration:
    """Integration tests with real API (marked as slow)."""
    
    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.getenv("MOONSHOT_API_KEY"),
        reason="No API key available"
    )
    def test_live_builtin_search(self):
        """Test real search API call."""
        result = kimi_builtin_search("What is the capital of France?")
        data = json.loads(result)
        
        assert "error" not in data
        assert "Paris" in data.get("content", "")
        assert len(data.get("sources", [])) > 0
```

### 5.2 Manual Testing Commands

```bash
# 1. Set API key
export MOONSHOT_API_KEY="sk-..."

# 2. Test builtin search
hermes chat -q "Use kimi_web_search to find recent AI news"

# 3. Test fetch
hermes chat -q "Use kimi_fetch to extract content from https://example.com"

# 4. Test convert
hermes chat -q "Use kimi_convert to convert 100 miles to kilometers"

# 5. Test with different format styles
hermes chat -q "Search with format_style=brief: what is Python?"
```

---

## 6. Deployment Checklist

### 6.1 Pre-deployment

- [ ] Code review completed
- [ ] Unit tests passing (`pytest tests/tools/test_kimi_tools.py`)
- [ ] Integration tests passing (with real API key)
- [ ] Documentation updated
- [ ] Error handling verified
- [ ] Rate limiting considered

### 6.2 Deployment Steps

1. **Create tool files**
   ```bash
   cp tools/kimi_builtin_search.py /path/to/hermes/tools/
   cp tools/kimi_formula_tools.py /path/to/hermes/tools/
   ```

2. **Update toolsets.py**
   - Add `kimi_web_search`, `kimi_fetch` to `_HERMES_CORE_TOOLS`
   - Or create dedicated `kimi` toolset

3. **Update config.py**
   - Add `MOONSHOT_API_KEY` to `OPTIONAL_ENV_VARS`

4. **Restart Hermes**
   ```bash
   hermes restart
   ```

5. **Verify registration**
   ```bash
   hermes tools list | grep kimi
   ```

### 6.3 Post-deployment Verification

- [ ] Tool appears in `hermes tools list`
- [ ] Check function returns `True` when API key set
- [ ] Search returns formatted results
- [ ] Error messages are user-friendly
- [ ] Token usage is tracked

---

## 7. Usage Examples

### 7.1 CLI Usage

```bash
# Search with default (detailed) format
hermes chat -q "kimi_web_search: latest developments in quantum computing"

# Search with brief format
hermes chat -q "Use kimi_web_search with format_style=brief to find the weather in Tokyo"

# Fetch URL content
hermes chat -q "kimi_fetch: https://news.ycombinator.com"

# Unit conversion
hermes chat -q "kimi_convert: 5 feet to meters"

# Execute code
hermes chat -q "kimi_code_runner: print([x**2 for x in range(10)])"
```

### 7.2 Programmatic Usage

```python
from tools.kimi_builtin_search import kimi_builtin_search
import json

# Search
result = kimi_builtin_search(
    query="machine learning trends 2024",
    format_style="structured"
)
data = json.loads(result)
print(data["content"])
print(data["sources"])

# Fetch
from tools.kimi_formula_tools import kimi_fetch_tool
result = kimi_fetch_tool("https://docs.python.org/3/")
print(json.loads(result))
```

---

## 8. Troubleshooting

### 8.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "API key not configured" | Missing env var | Set `MOONSHOT_API_KEY` |
| "tool_calls not found" | Invalid request format | Check system prompt and thinking settings |
| "Max rounds exceeded" | Loop detection failed | Check API response format |
| Empty results | Search returned no hits | Try different query |
| Encrypted output (formula) | Using formula instead of builtin | Use `kimi_web_search` not formula |

### 8.2 Debug Mode

```python
import logging
logging.getLogger("tools.kimi_builtin_search").setLevel(logging.DEBUG)
```

---

## Appendix A: Comparison with OpenClaw

| Feature | OpenClaw | Hermes Implementation |
|---------|----------|----------------------|
| Registration | `api.registerWebSearchProvider()` | `registry.register()` |
| Tool creation | `createTool()` method | Handler function |
| Credential path | `credentialPath` string | `requires_env` list |
| Auto-discovery | Plugin manifest | File-based auto-discovery |
| Fallback | Provider chain | Check function exclusion |

---

## Appendix B: API Reference

### Kimi Chat Completions

```http
POST /chat/completions
Content-Type: application/json
Authorization: Bearer {api_key}

{
  "model": "kimi-k2.5",
  "messages": [...],
  "tools": [{
    "type": "builtin_function",
    "function": {"name": "$web_search"}
  }],
  "thinking": {"type": "disabled"}
}
```

### Kimi Formula Tools

```http
GET /formulas/{formula_uri}/tools
Authorization: Bearer {api_key}

POST /formulas/{formula_uri}/fibers
Content-Type: application/json
Authorization: Bearer {api_key}

{
  "name": "{tool_name}",
  "arguments": "{json_encoded_args}"
}
```

---

*Document Version: 1.0*
*Last Updated: 2025*
