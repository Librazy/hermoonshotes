"""Tests for Kimi tools configuration."""

import json
import os
import pytest
import tempfile
from unittest.mock import patch

from tools.kimi_config import (
    KimiToolsConfig,
    get_config,
    get_prefixed_name,
    get_system_prompt,
    DEFAULT_SYSTEM_PROMPTS,
)


class TestKimiToolsConfig:
    """Test KimiToolsConfig class."""
    
    def test_default_prefix(self):
        """Test default prefix is 'kimi_'."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {}, clear=True):
            assert config.get_prefix() == "kimi_"
    
    def test_prefix_none(self):
        """Test prefix can be set to none."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {"KIMI_TOOLS_PREFIX": "none"}):
            assert config.get_prefix() == ""
    
    def test_prefix_null(self):
        """Test prefix can be set to null."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {"KIMI_TOOLS_PREFIX": "null"}):
            assert config.get_prefix() == ""
    
    def test_custom_prefix(self):
        """Test custom prefix."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {"KIMI_TOOLS_PREFIX": "my"}):
            assert config.get_prefix() == "my_"
    
    def test_custom_prefix_with_underscore(self):
        """Test custom prefix already has underscore."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {"KIMI_TOOLS_PREFIX": "my_"}):
            assert config.get_prefix() == "my_"
    
    def test_apply_prefix_with_default(self):
        """Test applying default prefix."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {}, clear=True):
            assert config.apply_prefix("web_search") == "kimi_web_search"
            assert config.apply_prefix("fetch") == "kimi_fetch"
    
    def test_apply_prefix_with_none(self):
        """Test applying no prefix."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {"KIMI_TOOLS_PREFIX": "none"}):
            assert config.apply_prefix("web_search") == "web_search_kimi"
            assert config.apply_prefix("fetch") == "fetch"
    
    def test_apply_prefix_with_custom(self):
        """Test applying custom prefix."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {"KIMI_TOOLS_PREFIX": "custom"}):
            assert config.apply_prefix("web_search") == "custom_web_search"
    
    def test_apply_prefix_no_double_prefix(self):
        """Test that prefix is not applied twice."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {}, clear=True):
            # Already prefixed name should not be double-prefixed
            assert config.apply_prefix("kimi_web_search") == "kimi_web_search"


class TestSystemPrompt:
    """Test system prompt configuration."""
    
    def test_default_system_prompts_exist(self):
        """Test that default system prompts are defined."""
        assert "detailed" in DEFAULT_SYSTEM_PROMPTS
        assert "brief" in DEFAULT_SYSTEM_PROMPTS
        assert "json" in DEFAULT_SYSTEM_PROMPTS
        assert "academic" in DEFAULT_SYSTEM_PROMPTS
        assert "markdown" in DEFAULT_SYSTEM_PROMPTS
    
    def test_get_system_prompt_default(self):
        """Test getting default system prompt."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {}, clear=True):
            prompt = config.get_system_prompt("json")
            assert prompt == DEFAULT_SYSTEM_PROMPTS["json"]
    
    def test_get_system_prompt_from_env(self):
        """Test getting system prompt from environment variable."""
        config = KimiToolsConfig()
        custom_prompt = "Custom system prompt for testing"
        with patch.dict(os.environ, {"KIMI_TOOLS_SYSTEM_PROMPT": custom_prompt}):
            prompt = config.get_system_prompt()
            assert prompt == custom_prompt
    
    def test_get_system_prompt_from_file(self):
        """Test getting system prompt from file."""
        config = KimiToolsConfig()
        custom_prompt = "Custom system prompt from file"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(custom_prompt)
            temp_file = f.name
        
        try:
            with patch.dict(os.environ, {"KIMI_TOOLS_SYSTEM_PROMPT_FILE": temp_file}):
                prompt = config.get_system_prompt()
                assert prompt == custom_prompt
        finally:
            os.unlink(temp_file)
    
    def test_get_system_prompt_env_overrides_file(self):
        """Test that env variable takes precedence over file."""
        config = KimiToolsConfig()
        env_prompt = "Prompt from environment"
        file_prompt = "Prompt from file"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(file_prompt)
            temp_file = f.name
        
        try:
            with patch.dict(os.environ, {
                "KIMI_TOOLS_SYSTEM_PROMPT": env_prompt,
                "KIMI_TOOLS_SYSTEM_PROMPT_FILE": temp_file
            }):
                prompt = config.get_system_prompt()
                assert prompt == env_prompt
        finally:
            os.unlink(temp_file)
    
    def test_get_system_prompt_invalid_format_style(self):
        """Test fallback to detailed for invalid format style."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {}, clear=True):
            prompt = config.get_system_prompt("invalid_style")
            assert prompt == DEFAULT_SYSTEM_PROMPTS["detailed"]


class TestConfigFile:
    """Test configuration file loading."""
    
    def test_load_config_from_file(self):
        """Test loading configuration from JSON file."""
        config = KimiToolsConfig()
        config_data = {
            "prefix": "custom",
            "system_prompt": "Custom prompt from file"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        try:
            with patch.dict(os.environ, {"KIMI_TOOLS_CONFIG_FILE": temp_file}):
                cfg = config.get_config()
                assert cfg["prefix"] == "custom"
                assert cfg["system_prompt"] == "Custom prompt from file"
        finally:
            os.unlink(temp_file)
    
    def test_env_overrides_config_file(self):
        """Test that environment variables override config file."""
        config = KimiToolsConfig()
        config_data = {"prefix": "from_file"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        try:
            with patch.dict(os.environ, {
                "KIMI_TOOLS_CONFIG_FILE": temp_file,
                "KIMI_TOOLS_PREFIX": "from_env"
            }):
                prefix = config.get_prefix()
                assert prefix == "from_env_"
        finally:
            os.unlink(temp_file)
    
    def test_missing_config_file(self):
        """Test handling of missing config file."""
        config = KimiToolsConfig()
        with patch.dict(os.environ, {"KIMI_TOOLS_CONFIG_FILE": "/nonexistent/path.json"}):
            cfg = config.get_config()
            assert cfg["prefix"] == "kimi"  # Default value


class TestConvenienceFunctions:
    """Test convenience module-level functions."""
    
    def test_get_prefixed_name_default(self):
        """Test get_prefixed_name with default prefix."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear cache to ensure fresh read
            get_config().clear_cache()
            assert get_prefixed_name("web_search") == "kimi_web_search"
    
    def test_get_prefixed_name_none(self):
        """Test get_prefixed_name with no prefix."""
        with patch.dict(os.environ, {"KIMI_TOOLS_PREFIX": "none"}):
            get_config().clear_cache()
            assert get_prefixed_name("web_search") == "web_search_kimi"
    
    def test_get_system_prompt_convenience(self):
        """Test get_system_prompt convenience function."""
        with patch.dict(os.environ, {}, clear=True):
            get_config().clear_cache()
            prompt = get_system_prompt("brief")
            assert prompt == DEFAULT_SYSTEM_PROMPTS["brief"]


class TestConfigCache:
    """Test configuration caching."""
    
    def test_config_is_cached(self):
        """Test that config is cached after first read."""
        config = KimiToolsConfig()
        
        with patch.dict(os.environ, {"KIMI_TOOLS_PREFIX": "cached"}):
            # First read
            cfg1 = config.get_config()
            # Second read should return same object (cached)
            cfg2 = config.get_config()
            assert cfg1 is cfg2
    
    def test_clear_cache(self):
        """Test clearing configuration cache."""
        config = KimiToolsConfig()
        
        with patch.dict(os.environ, {"KIMI_TOOLS_PREFIX": "original"}):
            cfg1 = config.get_config()
            config.clear_cache()
            
            with patch.dict(os.environ, {"KIMI_TOOLS_PREFIX": "changed"}):
                cfg2 = config.get_config()
                # After clearing cache, should read new value
                assert cfg2["prefix"] == "changed"


class TestFormatStyles:
    """Test format style options."""
    
    def test_get_available_format_styles(self):
        """Test getting list of available format styles."""
        config = KimiToolsConfig()
        styles = config.get_available_format_styles()
        
        assert "detailed" in styles
        assert "brief" in styles
        assert "json" in styles
        assert "academic" in styles
