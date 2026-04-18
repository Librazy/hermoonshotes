"""Tests for Kimi API configuration resolver."""

import os
import pytest
from unittest.mock import patch

from tools.kimi_api_config import (
    resolve_api_config,
    check_moonshot_available,
    get_api_key,
    get_base_url,
    DEFAULT_MOONSHOT_CN_URL,
    DEFAULT_MOONSHOT_AI_URL,
    KIMI_CODE_API_PREFIX,
)


class TestResolveApiConfig:
    """Test API configuration resolution logic."""

    def test_step_0_both_moonshot_vars_set(self):
        """Step 0: If both MOONSHOT_API_KEY and MOONSHOT_BASE_URL are set, use them."""
        env = {
            "MOONSHOT_API_KEY": "sk-moonshot",
            "MOONSHOT_BASE_URL": "https://api.moonshot.ai/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            key, url, warning = resolve_api_config()
            assert key == "sk-moonshot"
            assert url == "https://api.moonshot.ai/v1"
            assert warning is None

    def test_step_1a_kimi_cn_api_key(self):
        """Step 1a: KIMI_CN_API_KEY sets default endpoint to moonshot.cn."""
        env = {
            "KIMI_CN_API_KEY": "sk-cn-key",
        }
        with patch.dict(os.environ, env, clear=True):
            key, url, warning = resolve_api_config()
            assert key == "sk-cn-key"
            assert url == DEFAULT_MOONSHOT_CN_URL
            assert warning is None

    def test_step_1b_kimi_api_key_moonshot(self):
        """Step 1b: KIMI_API_KEY without sk-kimi- prefix uses moonshot.ai."""
        env = {
            "KIMI_API_KEY": "sk-regular-key",
        }
        with patch.dict(os.environ, env, clear=True):
            key, url, warning = resolve_api_config()
            assert key == "sk-regular-key"
            assert url == DEFAULT_MOONSHOT_AI_URL
            assert warning is None

    def test_step_1c_kimi_api_key_code_api(self):
        """Step 1c: KIMI_API_KEY with sk-kimi- prefix returns warning."""
        env = {
            "KIMI_API_KEY": "sk-kimi-code-key",
        }
        with patch.dict(os.environ, env, clear=True):
            key, url, warning = resolve_api_config()
            assert key is None
            assert url is None
            assert warning is not None
            assert "sk-kimi-" in warning
            assert "MOONSHOT_API_KEY" in warning

    def test_step_2b_moonshot_base_url_override(self):
        """Step 2b: MOONSHOT_BASE_URL overrides default endpoint."""
        env = {
            "KIMI_CN_API_KEY": "sk-cn-key",
            "MOONSHOT_BASE_URL": "https://custom.moonshot.cn/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            key, url, warning = resolve_api_config()
            assert key == "sk-cn-key"
            assert url == "https://custom.moonshot.cn/v1"
            assert warning is None

    def test_step_2c_kimi_base_url_used(self):
        """Step 2c: KIMI_BASE_URL is used if not Kimi Code API."""
        env = {
            "KIMI_CN_API_KEY": "sk-cn-key",
            "KIMI_BASE_URL": "https://api.moonshot.cn/staging/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            key, url, warning = resolve_api_config()
            assert key == "sk-cn-key"
            assert url == "https://api.moonshot.cn/staging/v1"
            assert warning is None

    def test_step_2c_kimi_base_url_kimi_code_ignored(self):
        """Step 2c: KIMI_BASE_URL starting with Kimi Code prefix is ignored."""
        env = {
            "KIMI_API_KEY": "sk-regular-key",
            "KIMI_BASE_URL": "https://api.kimi.com/coding/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            key, url, warning = resolve_api_config()
            assert key == "sk-regular-key"
            # Should use default endpoint, not KIMI_BASE_URL
            assert url == DEFAULT_MOONSHOT_AI_URL
            assert warning is None

    def test_moonshot_api_key_without_base_url(self):
        """MOONSHOT_API_KEY without MOONSHOT_BASE_URL returns warning."""
        env = {
            "MOONSHOT_API_KEY": "sk-moonshot",
        }
        with patch.dict(os.environ, env, clear=True):
            key, url, warning = resolve_api_config()
            assert key is None
            assert url is None
            assert warning is not None
            assert "MOONSHOT_BASE_URL" in warning

    def test_no_api_key(self):
        """No API key configured returns None values."""
        with patch.dict(os.environ, {}, clear=True):
            key, url, warning = resolve_api_config()
            assert key is None
            assert url is None
            assert warning is None

    def test_priority_kimi_cn_over_kimi(self):
        """KIMI_CN_API_KEY has priority over KIMI_API_KEY."""
        env = {
            "KIMI_CN_API_KEY": "sk-cn-key",
            "KIMI_API_KEY": "sk-regular-key",
        }
        with patch.dict(os.environ, env, clear=True):
            key, url, warning = resolve_api_config()
            assert key == "sk-cn-key"
            assert url == DEFAULT_MOONSHOT_CN_URL
            assert warning is None

    def test_moonshot_vars_override_kimi_cn(self):
        """MOONSHOT_API_KEY and MOONSHOT_BASE_URL override everything."""
        env = {
            "MOONSHOT_API_KEY": "sk-moonshot",
            "MOONSHOT_BASE_URL": "https://api.moonshot.ai/v1",
            "KIMI_CN_API_KEY": "sk-cn-key",
            "KIMI_API_KEY": "sk-regular-key",
        }
        with patch.dict(os.environ, env, clear=True):
            key, url, warning = resolve_api_config()
            assert key == "sk-moonshot"
            assert url == "https://api.moonshot.ai/v1"
            assert warning is None

    def test_moonshot_base_url_wins_over_kimi_base_url(self):
        """When both MOONSHOT_BASE_URL and KIMI_BASE_URL are set, MOONSHOT_BASE_URL wins."""
        env = {
            "KIMI_CN_API_KEY": "sk-cn-key",
            "MOONSHOT_BASE_URL": "https://custom.moonshot.ai/v1",
            "KIMI_BASE_URL": "https://api.moonshot.cn/staging/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            key, url, warning = resolve_api_config()
            assert key == "sk-cn-key"
            assert url == "https://custom.moonshot.ai/v1"
            assert warning is None


class TestCheckMoonshotAvailable:
    """Test check_moonshot_available function."""

    def test_available_with_valid_config(self):
        """Returns True with valid configuration."""
        env = {
            "KIMI_CN_API_KEY": "sk-cn-key",
        }
        with patch.dict(os.environ, env, clear=True):
            assert check_moonshot_available() is True

    def test_unavailable_with_kimi_code_key(self):
        """Returns False with Kimi Code API key (warning)."""
        env = {
            "KIMI_API_KEY": "sk-kimi-code-key",
        }
        with patch.dict(os.environ, env, clear=True):
            assert check_moonshot_available() is False

    def test_unavailable_without_key(self):
        """Returns False without any API key."""
        with patch.dict(os.environ, {}, clear=True):
            assert check_moonshot_available() is False

    def test_unavailable_moonshot_key_without_base_url(self):
        """Returns False when MOONSHOT_API_KEY set without MOONSHOT_BASE_URL."""
        env = {
            "MOONSHOT_API_KEY": "sk-moonshot",
        }
        with patch.dict(os.environ, env, clear=True):
            assert check_moonshot_available() is False


class TestGetApiKey:
    """Test get_api_key function."""

    def test_returns_resolved_key(self):
        """Returns resolved API key."""
        env = {
            "KIMI_CN_API_KEY": "sk-cn-key",
        }
        with patch.dict(os.environ, env, clear=True):
            assert get_api_key() == "sk-cn-key"

    def test_returns_none_when_not_configured(self):
        """Returns None when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_api_key() is None


class TestGetBaseUrl:
    """Test get_base_url function."""

    def test_returns_resolved_url(self):
        """Returns resolved base URL."""
        env = {
            "KIMI_CN_API_KEY": "sk-cn-key",
        }
        with patch.dict(os.environ, env, clear=True):
            assert get_base_url() == DEFAULT_MOONSHOT_CN_URL

    def test_returns_none_when_not_configured(self):
        """Returns None when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_base_url() is None
