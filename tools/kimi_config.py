"""Kimi Tools Configuration.

This module provides configuration management for Kimi tools,
including prefix control and system prompt overrides.
"""

import json
import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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


class KimiToolsConfig:
    """Configuration manager for Kimi tools.
    
    Supports:
    - Prefix control (kimi prefix, no prefix, or custom prefix)
    - System prompt override
    - Environment variable based configuration
    - JSON configuration file support
    """
    
    # Environment variable names
    ENV_PREFIX = "KIMI_TOOLS_PREFIX"
    ENV_SYSTEM_PROMPT = "KIMI_TOOLS_SYSTEM_PROMPT"
    ENV_SYSTEM_PROMPT_FILE = "KIMI_TOOLS_SYSTEM_PROMPT_FILE"
    ENV_CONFIG_FILE = "KIMI_TOOLS_CONFIG_FILE"
    
    # Default prefix options
    PREFIX_KIMI = "kimi_"      # Default: kimi_web_search, kimi_fetch, etc.
    PREFIX_NONE = ""           # No prefix: web_search, fetch, etc.
    
    def __init__(self):
        self._config_cache: Optional[Dict[str, Any]] = None
        self._system_prompt_cache: Optional[str] = None
    
    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from file if specified."""
        config_file = os.getenv(self.ENV_CONFIG_FILE)
        if not config_file:
            return {}
        
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in config file: {e}")
            return {}
    
    def get_config(self) -> Dict[str, Any]:
        """Get merged configuration from all sources.
        
        Priority (highest to lowest):
        1. Environment variables
        2. Config file
        3. Defaults
        """
        if self._config_cache is not None:
            return self._config_cache
        
        # Start with defaults
        config = {
            "prefix": self.PREFIX_KIMI,
            "system_prompt": None,
            "system_prompt_file": None,
        }
        
        # Override with config file
        file_config = self._load_config_file()
        config.update(file_config)
        
        # Override with environment variables
        if os.getenv(self.ENV_PREFIX):
            config["prefix"] = os.getenv(self.ENV_PREFIX)
        if os.getenv(self.ENV_SYSTEM_PROMPT):
            config["system_prompt"] = os.getenv(self.ENV_SYSTEM_PROMPT)
        if os.getenv(self.ENV_SYSTEM_PROMPT_FILE):
            config["system_prompt_file"] = os.getenv(self.ENV_SYSTEM_PROMPT_FILE)
        
        self._config_cache = config
        return config
    
    def get_prefix(self) -> str:
        """Get the tool name prefix.
        
        Returns:
            Prefix string (e.g., "kimi_", "", or custom)
        """
        config = self.get_config()
        prefix = config.get("prefix", self.PREFIX_KIMI)
        
        # Handle special values
        if prefix.lower() == "none" or prefix.lower() == "null":
            return ""
        
        return prefix
    
    def apply_prefix(self, name: str) -> str:
        """Apply prefix to a tool name.
        
        Args:
            name: Base tool name (e.g., "web_search")
            
        Returns:
            Prefixed name (e.g., "kimi_web_search" or "web_search")
        """
        prefix = self.get_prefix()
        if not prefix:
            return name
        
        # Ensure prefix ends with underscore if not empty
        if prefix and not prefix.endswith("_"):
            prefix = prefix + "_"
        
        # Don't double-prefix if already prefixed
        if name.startswith(prefix):
            return name
        
        return prefix + name
    
    def get_system_prompt(self, format_style: str = "detailed") -> str:
        """Get system prompt for search.
        
        Priority (highest to lowest):
        1. Environment variable KIMI_TOOLS_SYSTEM_PROMPT
        2. File specified by KIMI_TOOLS_SYSTEM_PROMPT_FILE
        3. Config file system_prompt
        4. Config file system_prompt_file
        5. Default prompts
        
        Args:
            format_style: Output format style (detailed, brief, structured, academic)
            
        Returns:
            System prompt string
        """
        # Check cache first
        if self._system_prompt_cache is not None:
            return self._system_prompt_cache
        
        config = self.get_config()
        
        # 1. Direct environment variable
        env_prompt = os.getenv(self.ENV_SYSTEM_PROMPT)
        if env_prompt:
            logger.debug("Using system prompt from environment variable")
            self._system_prompt_cache = env_prompt
            return env_prompt
        
        # 2. File from environment variable
        env_prompt_file = os.getenv(self.ENV_SYSTEM_PROMPT_FILE)
        if env_prompt_file:
            try:
                with open(env_prompt_file, 'r') as f:
                    prompt = f.read()
                    logger.debug(f"Using system prompt from file: {env_prompt_file}")
                    self._system_prompt_cache = prompt
                    return prompt
            except FileNotFoundError:
                logger.warning(f"System prompt file not found: {env_prompt_file}")
            except IOError as e:
                logger.warning(f"Error reading system prompt file: {e}")
        
        # 3. Config file system_prompt
        if config.get("system_prompt"):
            logger.debug("Using system prompt from config file")
            self._system_prompt_cache = config["system_prompt"]
            return config["system_prompt"]
        
        # 4. Config file system_prompt_file
        if config.get("system_prompt_file"):
            try:
                with open(config["system_prompt_file"], 'r') as f:
                    prompt = f.read()
                    logger.debug(f"Using system prompt from config file path: {config['system_prompt_file']}")
                    self._system_prompt_cache = prompt
                    return prompt
            except FileNotFoundError:
                logger.warning(f"System prompt file not found: {config['system_prompt_file']}")
            except IOError as e:
                logger.warning(f"Error reading system prompt file: {e}")
        
        # 5. Default prompts
        if format_style in DEFAULT_SYSTEM_PROMPTS:
            return DEFAULT_SYSTEM_PROMPTS[format_style]
        
        return DEFAULT_SYSTEM_PROMPTS["detailed"]
    
    def get_available_format_styles(self) -> List[str]:
        """Get list of available format styles.
        
        Returns:
            List of format style names
        """
        return list(DEFAULT_SYSTEM_PROMPTS.keys())
    
    def clear_cache(self):
        """Clear configuration cache.
        
        Call this if configuration changes at runtime.
        """
        self._config_cache = None
        self._system_prompt_cache = None


# Global configuration instance
_config = KimiToolsConfig()


def get_config() -> KimiToolsConfig:
    """Get the global configuration instance."""
    return _config


def get_prefixed_name(name: str) -> str:
    """Convenience function to get prefixed tool name.
    
    Args:
        name: Base tool name
        
    Returns:
        Prefixed tool name
    """
    return _config.apply_prefix(name)


def get_system_prompt(format_style: str = "detailed") -> str:
    """Convenience function to get system prompt.
    
    Args:
        format_style: Output format style
        
    Returns:
        System prompt string
    """
    return _config.get_system_prompt(format_style)
