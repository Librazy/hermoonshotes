"""Kimi Formula Tools - Official Moonshot formula tools."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from .kimi_config import get_config
from .kimi_transcript import save_tool_transcript

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"

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
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=base_url or os.getenv("MOONSHOT_BASE_URL") or DEFAULT_BASE_URL,
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
    return bool(os.getenv("MOONSHOT_API_KEY"))


def _get_client() -> Optional[KimiFormulaClient]:
    """Get configured client."""
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        return None
    return KimiFormulaClient(api_key)


def _run_formula_tool(
    public_tool_name: str,
    formula_uri: str,
    api_tool_name: str,
    arguments: Dict[str, Any],
    *,
    task_id: Optional[str] = None,
) -> str:
    """Execute a Moonshot formula tool and optionally persist a transcript."""
    client = _get_client()
    if not client:
        error_payload = {"error": "Kimi API key not configured"}
        save_tool_transcript(
            public_tool_name,
            get_config().apply_prefix(public_tool_name),
            {
                "formula_uri": formula_uri,
                "api_tool_name": api_tool_name,
                "arguments": arguments,
            },
            error_payload,
            task_id=task_id,
        )
        return json.dumps(error_payload)

    try:
        result = client.execute_tool(formula_uri, api_tool_name, arguments)
        save_tool_transcript(
            public_tool_name,
            get_config().apply_prefix(public_tool_name),
            {
                "formula_uri": formula_uri,
                "api_tool_name": api_tool_name,
                "arguments": arguments,
            },
            result,
            task_id=task_id,
        )
        return json.dumps(result)
    finally:
        client.close()


# --- Individual Tool Handlers ---

def kimi_fetch_tool(url: str, task_id: Optional[str] = None) -> str:
    """Fetch URL content."""
    return _run_formula_tool(
        "fetch",
        FORMULAS["fetch"],
        "fetch",
        {"url": url},
        task_id=task_id,
    )


def kimi_convert_tool(
    value: float,
    from_unit: str,
    to_unit: str,
    task_id: Optional[str] = None,
) -> str:
    """Convert units."""
    return _run_formula_tool(
        "convert",
        FORMULAS["convert"],
        "convert",
        {
            "value": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
        },
        task_id=task_id,
    )


def kimi_quickjs_tool(code: str, task_id: Optional[str] = None) -> str:
    """Execute JavaScript code."""
    return _run_formula_tool(
        "quickjs",
        FORMULAS["quickjs"],
        "quickjs",
        {"code": code},
        task_id=task_id,
    )


def kimi_code_runner_tool(
    code: str,
    language: str = "python",
    task_id: Optional[str] = None,
) -> str:
    """Execute code (Python/JS)."""
    return _run_formula_tool(
        "code_runner",
        FORMULAS["code_runner"],
        "code_runner",
        {"code": code, "language": language},
        task_id=task_id,
    )


def kimi_excel_tool(
    file_content: str,
    operation: str = "analyze",
    task_id: Optional[str] = None,
) -> str:
    """Analyze Excel/CSV content."""
    return _run_formula_tool(
        "excel",
        FORMULAS["excel"],
        "excel",
        {"content": file_content, "operation": operation},
        task_id=task_id,
    )


def kimi_base64_tool(
    data: str,
    operation: str = "encode",
    encoding: str = "utf-8",
    task_id: Optional[str] = None,
) -> str:
    """Base64 encode/decode data."""
    tool_name = {
        "encode": "base64_encode",
        "decode": "base64_decode",
    }.get(operation)
    if not tool_name:
        return json.dumps({"error": f"Unsupported base64 operation: {operation}"})
    return _run_formula_tool(
        "base64",
        FORMULAS["base64"],
        tool_name,
        {"data": data, "encoding": encoding},
        task_id=task_id,
    )


def kimi_date_tool(
    operation: str = "time",
    format: str = "%Y-%m-%d %H:%M:%S",
    zone: Optional[str] = None,
    date: Optional[str] = None,
    date1: Optional[str] = None,
    date2: Optional[str] = None,
    days: Optional[int] = None,
    from_zone: Optional[str] = None,
    to_zone: Optional[str] = None,
    task_id: Optional[str] = None,
) -> str:
    """Date/time operations."""
    arguments = {"operation": operation, "format": format}
    optional_values = {
        "zone": zone,
        "date": date,
        "date1": date1,
        "date2": date2,
        "days": days,
        "from_zone": from_zone,
        "to_zone": to_zone,
    }
    arguments.update({key: value for key, value in optional_values.items() if value is not None})

    return _run_formula_tool(
        "date",
        FORMULAS["date"],
        "date",
        arguments,
        task_id=task_id,
    )


# --- Schema Builders ---

def _build_fetch_schema(name: str) -> Dict[str, Any]:
    """Build fetch tool schema."""
    return {
        "name": name,
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


def _build_convert_schema(name: str) -> Dict[str, Any]:
    """Build convert tool schema."""
    return {
        "name": name,
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


def _build_quickjs_schema(name: str) -> Dict[str, Any]:
    """Build quickjs tool schema."""
    return {
        "name": name,
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


def _build_code_runner_schema(name: str) -> Dict[str, Any]:
    """Build code_runner tool schema."""
    return {
        "name": name,
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


def _build_excel_schema(name: str) -> Dict[str, Any]:
    """Build excel tool schema."""
    return {
        "name": name,
        "description": "Analyze Excel/CSV file content",
        "parameters": {
            "type": "object",
            "properties": {
                "file_content": {
                    "type": "string",
                    "description": "Base64-encoded file content or raw CSV content"
                },
                "operation": {
                    "type": "string",
                    "enum": ["analyze", "summarize", "extract"],
                    "default": "analyze",
                    "description": "Operation to perform on the file"
                }
            },
            "required": ["file_content"]
        }
    }


def _build_base64_schema(name: str) -> Dict[str, Any]:
    """Build base64 tool schema."""
    return {
        "name": name,
        "description": "Base64 encode or decode text data",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "Data to encode or decode"
                },
                "operation": {
                    "type": "string",
                    "enum": ["encode", "decode"],
                    "default": "encode"
                },
                "encoding": {
                    "type": "string",
                    "description": "Text encoding used before encode or after decode",
                    "default": "utf-8",
                }
            },
            "required": ["data"]
        }
    }


def _build_date_schema(name: str) -> Dict[str, Any]:
    """Build date tool schema."""
    return {
        "name": name,
        "description": "Date and time operations",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["time", "convert", "between", "add", "subtract"],
                    "default": "time",
                    "description": "Date operation to perform"
                },
                "format": {
                    "type": "string",
                    "description": "Output format using Python strftime syntax",
                    "default": "%Y-%m-%d %H:%M:%S",
                },
                "zone": {
                    "type": "string",
                    "description": "Timezone name for time display operations",
                },
                "date": {
                    "type": "string",
                    "description": "Primary date string for convert/add/subtract operations",
                },
                "date1": {
                    "type": "string",
                    "description": "First date string for between operations",
                },
                "date2": {
                    "type": "string",
                    "description": "Second date string for between operations",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to add or subtract",
                },
                "from_zone": {
                    "type": "string",
                    "description": "Source timezone for convert operations",
                },
                "to_zone": {
                    "type": "string",
                    "description": "Target timezone for convert operations",
                },
            },
            "required": ["operation"],
        }
    }


def get_formula_tool_registrations() -> List[Dict[str, Any]]:
    """Return registration payloads used by the Hermes plugin entrypoint."""
    config = get_config()
    tool_definitions = [
        ("fetch", _build_fetch_schema, lambda args, **kw: kimi_fetch_tool(args.get("url", ""), task_id=kw.get("task_id")), "plugin_hermoonshotes_web"),
        ("convert", _build_convert_schema, lambda args, **kw: kimi_convert_tool(
            args.get("value", 0),
            args.get("from_unit", ""),
            args.get("to_unit", ""),
            task_id=kw.get("task_id"),
        ), "plugin_hermoonshotes_utility"),
        ("quickjs", _build_quickjs_schema, lambda args, **kw: kimi_quickjs_tool(args.get("code", ""), task_id=kw.get("task_id")), "plugin_hermoonshotes_utility"),
        ("base64", _build_base64_schema, lambda args, **kw: kimi_base64_tool(
            args.get("data", ""),
            args.get("operation", "encode"),
            args.get("encoding", "utf-8"),
            task_id=kw.get("task_id"),
        ), "plugin_hermoonshotes_utility"),
        ("date", _build_date_schema, lambda args, **kw: kimi_date_tool(
            args.get("operation", "time"),
            args.get("format", "%Y-%m-%d %H:%M:%S"),
            zone=args.get("zone"),
            date=args.get("date"),
            date1=args.get("date1"),
            date2=args.get("date2"),
            days=args.get("days"),
            from_zone=args.get("from_zone"),
            to_zone=args.get("to_zone"),
            task_id=kw.get("task_id"),
        ), "plugin_hermoonshotes_utility"),
    ]

    registrations: List[Dict[str, Any]] = []
    for base_name, schema_builder, handler, toolset in tool_definitions:
        prefixed_name = config.apply_prefix(base_name)
        registrations.append(
            {
                "name": prefixed_name,
                "toolset": toolset,
                "schema": schema_builder(prefixed_name),
                "handler": handler,
                "check_fn": check_formula_tools_available,
                "requires_env": ["MOONSHOT_API_KEY"],
            }
        )
    return registrations
