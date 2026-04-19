"""Tests for Kimi tools integration."""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Import the modules under test
from tools.kimi_formula_web_search import (
    check_kimi_search_available,
    kimi_formula_web_search,
    _resolve_api_key,
    KIMI_FORMULA_WEB_SEARCH_SCHEMA,
)
from tools.kimi_config import DEFAULT_SYSTEM_PROMPTS
from tools.kimi_formula_tools import (
    check_formula_tools_available,
    KimiFormulaClient,
    kimi_fetch_tool,
    kimi_convert_tool,
    kimi_quickjs_tool,
    kimi_code_runner_tool,
    FORMULAS,
)
from tools.kimi_api_config import DEFAULT_MOONSHOT_CN_URL, DEFAULT_MOONSHOT_AI_URL


class TestKimiFormulaWebSearch:
    """Test formula-based forced web_search functionality."""

    def test_check_available_with_key(self):
        """Tool available when API key set."""
        with patch.dict(os.environ, {"KIMI_CN_API_KEY": "sk-test"}):
            assert check_kimi_search_available() is True

    def test_check_available_without_key(self):
        """Tool unavailable when no API key."""
        with patch.dict(os.environ, {}, clear=True):
            assert check_kimi_search_available() is False

    def test_resolve_api_key(self):
        """Resolve API key from KIMI_CN_API_KEY."""
        with patch.dict(os.environ, {"KIMI_CN_API_KEY": "sk-moonshot"}):
            assert _resolve_api_key() == "sk-moonshot"

    def test_search_returns_error_without_key(self):
        """Search returns error JSON when no API key."""
        with patch.dict(os.environ, {}, clear=True):
            result = kimi_formula_web_search("test query")
            data = json.loads(result)
            assert "error" in data
            assert "MOONSHOT_API_KEY" in data.get("message", "") or "KIMI_CN_API_KEY" in data.get("message", "")

    @patch("httpx.Client.post")
    def test_search_success_flow(self, mock_post):
        """Test successful search with formula + chat flow."""
        # First response: formula web_search result
        first_response = {
            "status": "succeeded",
            "id": "fiber-123",
            "context": {
                "encrypted_output": "----MOONSHOT ENCRYPTED BEGIN----encrypted_search_result----MOONSHOT ENCRYPTED END----"
            }
        }

        # Second response: chat completion with formatted result
        second_response = {
            "choices": [{
                "finish_reason": "stop",
                "message": {
                    "content": "Search results here"
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50
            }
        }

        mock_post.side_effect = [
            Mock(status_code=200, json=lambda: first_response),
            Mock(status_code=200, json=lambda: second_response)
        ]

        with patch.dict(os.environ, {"KIMI_CN_API_KEY": "sk-test"}):
            result = kimi_formula_web_search("test query")
            assert result == "Search results here"

    @patch("httpx.Client.post")
    def test_search_formula_error(self, mock_post):
        """Test handling of formula execution errors."""
        # Formula returns error
        error_response = {
            "status": "failed",
            "id": "fiber-456",
            "context": {
                "error": "Search service unavailable"
            }
        }

        mock_post.return_value = Mock(status_code=200, json=lambda: error_response)

        with patch.dict(os.environ, {"KIMI_CN_API_KEY": "sk-test"}):
            result = kimi_formula_web_search("test query")
            data = json.loads(result)
            assert "error" in data
            assert "Formula web_search failed" in data.get("error", "")

    @patch("httpx.Client.post")
    def test_search_http_error(self, mock_post):
        """Test handling of HTTP errors."""
        mock_post.side_effect = Exception("Connection error")

        with patch.dict(os.environ, {"KIMI_CN_API_KEY": "sk-test"}):
            result = kimi_formula_web_search("test query")
            data = json.loads(result)
            assert "error" in data

    def test_default_system_prompts(self):
        """Test that default system prompts are defined."""
        assert "detailed" in DEFAULT_SYSTEM_PROMPTS
        assert "brief" in DEFAULT_SYSTEM_PROMPTS
        assert "json" in DEFAULT_SYSTEM_PROMPTS
        assert "academic" in DEFAULT_SYSTEM_PROMPTS

    def test_schema_structure(self):
        """Test that schema has required fields."""
        assert "name" in KIMI_FORMULA_WEB_SEARCH_SCHEMA
        assert "description" in KIMI_FORMULA_WEB_SEARCH_SCHEMA
        assert "parameters" in KIMI_FORMULA_WEB_SEARCH_SCHEMA
        assert KIMI_FORMULA_WEB_SEARCH_SCHEMA["name"] == "kimi_web_search"


class TestKimiFormulaTools:
    """Test formula tool functionality."""

    def test_check_formula_tools_available_with_key(self):
        """Formula tools available when API key set."""
        with patch.dict(os.environ, {"KIMI_CN_API_KEY": "sk-test"}):
            assert check_formula_tools_available() is True

    def test_check_formula_tools_available_without_key(self):
        """Formula tools unavailable when no API key."""
        with patch.dict(os.environ, {}, clear=True):
            assert check_formula_tools_available() is False

    def test_client_init(self):
        """Test client initialization."""
        client = KimiFormulaClient("sk-test", DEFAULT_MOONSHOT_CN_URL)
        assert client.api_key == "sk-test"
        assert client.client is not None
        client.close()

    def test_client_get_tool_schema_success(self):
        """Test successful schema fetch."""
        client = KimiFormulaClient("sk-test", DEFAULT_MOONSHOT_CN_URL)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tools": [{
                "type": "function",
                "function": {"name": "fetch", "description": "Fetch URL"}
            }]
        }

        with patch.object(client.client, "get", return_value=mock_response):
            schema = client.get_tool_schema("moonshot/fetch:latest")
            assert schema is not None
            assert schema["function"]["name"] == "fetch"

        client.close()

    def test_client_execute_tool_success(self):
        """Test successful formula execution."""
        client = KimiFormulaClient("sk-test", DEFAULT_MOONSHOT_CN_URL)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "succeeded",
            "id": "fiber-123",
            "context": {
                "output": "Fetched content"
            }
        }

        with patch.object(client.client, "post", return_value=mock_response):
            result = client.execute_tool(
                "moonshot/fetch:latest",
                "fetch",
                {"url": "https://example.com"}
            )

            assert result["status"] == "success"
            assert result["result"] == "Fetched content"

        client.close()

    def test_client_execute_tool_error(self):
        """Test formula execution with error response."""
        client = KimiFormulaClient("sk-test", DEFAULT_MOONSHOT_CN_URL)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "failed",
            "id": "fiber-456",
            "context": {
                "error": "Invalid URL"
            }
        }

        with patch.object(client.client, "post", return_value=mock_response):
            result = client.execute_tool(
                "moonshot/fetch:latest",
                "fetch",
                {"url": "invalid"}
            )

            assert result["status"] == "error"
            assert "error" in result

        client.close()

    def test_client_execute_tool_encrypted_output(self):
        """Test handling of encrypted output."""
        client = KimiFormulaClient("sk-test", DEFAULT_MOONSHOT_CN_URL)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "succeeded",
            "id": "fiber-789",
            "context": {
                "encrypted_output": "----MOONSHOT ENCRYPTED BEGIN----...----MOONSHOT ENCRYPTED END----"
            }
        }

        with patch.object(client.client, "post", return_value=mock_response):
            result = client.execute_tool(
                "moonshot/web-search:latest",
                "web_search",
                {"query": "test"}
            )

            assert result["status"] == "success"
            assert "encrypted" in result["result"].lower() or "MOONSHOT" in result["result"]

        client.close()


class TestKimiToolHandlers:
    """Test individual tool handlers."""
    
    def test_fetch_tool_no_api_key(self):
        """Fetch tool returns error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            result = kimi_fetch_tool("https://example.com")
            data = json.loads(result)
            assert "error" in data

    def test_convert_tool_no_api_key(self):
        """Convert tool returns error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            result = kimi_convert_tool(100, "meters", "feet")
            data = json.loads(result)
            assert "error" in data

    def test_quickjs_tool_no_api_key(self):
        """QuickJS tool returns error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            result = kimi_quickjs_tool("console.log('hello')")
            data = json.loads(result)
            assert "error" in data

    def test_code_runner_tool_no_api_key(self):
        """Code runner tool returns error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            result = kimi_code_runner_tool("print('hello')")
            data = json.loads(result)
            assert "error" in data

    @patch("tools.kimi_formula_tools.KimiFormulaClient.execute_tool")
    def test_fetch_tool_success(self, mock_execute):
        """Test fetch tool with successful execution."""
        mock_execute.return_value = {
            "status": "success",
            "result": "# Example Domain\n\nThis domain is for use in examples."
        }

        with patch.dict(os.environ, {"KIMI_CN_API_KEY": "sk-test"}):
            result = kimi_fetch_tool("https://example.com")
            data = json.loads(result)
            assert data["status"] == "success"
            assert "Example Domain" in data["result"]

    @patch("tools.kimi_formula_tools.KimiFormulaClient.execute_tool")
    def test_convert_tool_success(self, mock_execute):
        """Test convert tool with successful execution."""
        mock_execute.return_value = {
            "status": "success",
            "result": "328.084 feet"
        }

        with patch.dict(os.environ, {"KIMI_CN_API_KEY": "sk-test"}):
            result = kimi_convert_tool(100, "meters", "feet")
            data = json.loads(result)
            assert data["status"] == "success"


class TestFormulaRegistry:
    """Test formula registry constants."""
    
    def test_formula_uris(self):
        """Test that all formula URIs are properly defined."""
        expected_formulas = [
            "web_search",
            "fetch",
            "convert",
            "date",
            "base64",
            "quickjs",
            "code_runner",
            "excel"
        ]
        
        for formula in expected_formulas:
            assert formula in FORMULAS
            assert FORMULAS[formula].startswith("moonshot/")
            assert FORMULAS[formula].endswith(":latest")


class TestIntegration:
    """Integration tests with real API (marked as slow)."""
    
    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.getenv("KIMI_CN_API_KEY") and not os.getenv("KIMI_API_KEY") and not os.getenv("MOONSHOT_API_KEY"),
        reason="No API key available"
    )
    def test_live_formula_web_search(self):
        """Test real formula web search API call."""
        result = kimi_formula_web_search("What is the capital of France?")

        assert result
        assert "Paris" in result

    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.getenv("KIMI_CN_API_KEY") and not os.getenv("KIMI_API_KEY") and not os.getenv("MOONSHOT_API_KEY"),
        reason="No API key available"
    )
    def test_live_fetch(self):
        """Test real fetch API call."""
        result = kimi_fetch_tool("https://example.com")
        data = json.loads(result)

        assert "error" not in data
        assert data.get("status") == "success"
