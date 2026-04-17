"""Kimi Formula Tools - Official Moonshot formula tools."""

import json
import os
import logging
from typing import Any, Dict, List, Optional
import httpx

from tools.kimi_config import get_config

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


def kimi_base64_tool(data: str, operation: str = "encode") -> str:
    """Base64 encode/decode data."""
    client = _get_client()
    if not client:
        return json.dumps({"error": "Kimi API key not configured"})
    
    try:
        result = client.execute_tool(
            FORMULAS["base64"],
            "base64",
            {"data": data, "operation": operation}
        )
        return json.dumps(result)
    finally:
        client.close()


def kimi_date_tool(operation: str = "now", format: str = "iso") -> str:
    """Date/time operations."""
    client = _get_client()
    if not client:
        return json.dumps({"error": "Kimi API key not configured"})
    
    try:
        result = client.execute_tool(
            FORMULAS["date"],
            "date",
            {"operation": operation, "format": format}
        )
        return json.dumps(result)
    finally:
        client.close()


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
        "description": "Base64 encode or decode data",
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
                    "enum": ["now", "parse", "format"],
                    "default": "now",
                    "description": "Date operation to perform"
                },
                "format": {
                    "type": "string",
                    "description": "Output format (e.g., 'iso', 'unix', custom format)"
                }
            }
        }
    }


# --- Registration ---
# Note: The registry import is placed at the end to avoid circular imports
try:
    from tools.registry import registry

    _config = get_config()

    # Define tool registrations with their builders and handlers
    _TOOL_DEFINITIONS = [
        ("fetch", _build_fetch_schema, lambda args, **kw: kimi_fetch_tool(args.get("url", "")), "web"),
        ("convert", _build_convert_schema, lambda args, **kw: kimi_convert_tool(
            args.get("value", 0),
            args.get("from_unit", ""),
            args.get("to_unit", "")
        ), "utility"),
        ("quickjs", _build_quickjs_schema, lambda args, **kw: kimi_quickjs_tool(args.get("code", "")), "utility"),
        ("code_runner", _build_code_runner_schema, lambda args, **kw: kimi_code_runner_tool(
            args.get("code", ""),
            args.get("language", "python")
        ), "utility"),
        ("excel", _build_excel_schema, lambda args, **kw: kimi_excel_tool(
            args.get("file_content", ""),
            args.get("operation", "analyze")
        ), "utility"),
        ("base64", _build_base64_schema, lambda args, **kw: kimi_base64_tool(
            args.get("data", ""),
            args.get("operation", "encode")
        ), "utility"),
        ("date", _build_date_schema, lambda args, **kw: kimi_date_tool(
            args.get("operation", "now"),
            args.get("format", "iso")
        ), "utility"),
    ]

    # Register all tools with configured prefix
    for base_name, schema_builder, handler, toolset in _TOOL_DEFINITIONS:
        prefixed_name = _config.apply_prefix(base_name)
        schema = schema_builder(prefixed_name)
        
        registry.register(
            name=prefixed_name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=check_formula_tools_available,
            requires_env=["MOONSHOT_API_KEY"],
        )
        logger.debug(f"Registered Kimi formula tool: {base_name} as: {prefixed_name}")

except ImportError:
    # Registry not available during initial import (e.g., during testing)
    pass
