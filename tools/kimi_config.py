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
    "detailed": """You are a search result formatting agent. Format the provided web search results as structured markdown strictly following the syntax below, and DO NOT ADD YOUR OWN DESCRIPTION, OPINION OR THOUGHTS.

```markdown
# [Search Result Title 1](url-of-search-result-1)

> Summary of Search Result 1

* Detailed Search Result 1, paragraph 1
* Detailed Search Result 1, paragraph 2

---

# [<Search Result Title 2>](url-of-search-result-2)

> Summary of Search Result 2

* Detailed Search Result 2, paragraph 1
* Detailed Search Result 2, paragraph 2
* Detailed Search Result 2, paragraph 3
```""",

    "brief": """You are a search result formatting agent. Format the provided web search results as a concise answer with sources, and DO NOT ADD YOUR OWN DESCRIPTION, OPINION OR THOUGHTS.""",

    "markdown": """You are a search result formatting agent. Format the provided web search results as a structured markdown document with links, and DO NOT ADD YOUR OWN DESCRIPTION, OPINION OR THOUGHTS.""",

    # The kimi API don't support `response_format: {type: "json_schema"}` yet, so we use `json_object` and specify the schema in the system prompt instead.
    "json": """You are a search result formatting agent. Format the provided web search results as JSON strictly valid against the schema below, and DO NOT ADD YOUR OWN DESCRIPTION, OPINION OR THOUGHTS.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "description": "List of search results",
      "items": {
        "type": "object",
        "description": "Single search result item",
        "properties": {
          "index": {
            "type": "integer",
            "description": "Index number of the search result",
            "minimum": 0
          },
          "url": {
            "type": "string",
            "format": "uri",
            "description": "URL of the search result"
          },
          "title": {
            "type": "string",
            "description": "Title of the search result"
          },
          "content": {
            "type": "array",
            "description": "Detailed content text of the search result",
            "items": {
              "type": "string",
              "description": "Content text fragment"
            },
            "minItems": 0
          }
        },
        "required": [
          "index",
          "url",
          "title",
          "content"
        ],
        "additionalProperties": false
      }
    }
  },
  "required": [
    "results"
  ]
}
```

For example:
```json
{
  "results": [
    {
      "index": 0,
      "url": "https://www.example.com",
      "title": "Example Title",
      "content": ["Example Content"]
    },
    {
      "index": 1,
      "url": "https://www.foo.com",
      "title": "Foo Title",
      "content": ["Example Content Bar", "Example Content Baz"]
    }
  ]
}
```
""",

    "academic": """You are a search result formatting agent. Format the provided web search results as an academic answer with APA citations, and DO NOT ADD YOUR OWN OPINION OR THOUGHTS.""",
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
    SEARCH_FALLBACK_NAME = "web_search_kimi"
    
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
            if name == "web_search":
                # Hermes already has a built-in ``web_search`` tool, so keep
                # unprefixed names for safe tools and use a collision-free
                # fallback name for Moonshot search.
                return self.SEARCH_FALLBACK_NAME
            return name
        
        # Ensure prefix ends with underscore if not empty
        if prefix and not prefix.endswith("_"):
            prefix = prefix + "_"
        
        # Don't double-prefix if already prefixed
        if name.startswith(prefix):
            return name
        
        return prefix + name
    
    def get_system_prompt(self, format_style: str = "json") -> str:
        """Get system prompt for search.
        
        Priority (highest to lowest):
        1. Environment variable KIMI_TOOLS_SYSTEM_PROMPT
        2. File specified by KIMI_TOOLS_SYSTEM_PROMPT_FILE
        3. Config file system_prompt
        4. Config file system_prompt_file
        5. Default prompts
        
        Args:
            format_style: Output format style (detailed, brief, markdown, json, academic)

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
        
        return DEFAULT_SYSTEM_PROMPTS["json"]
    
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
