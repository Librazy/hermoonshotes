"""Hermes CLI configuration.

This module defines environment variable configurations for the Hermes CLI,
including optional API keys and their associated tools.
"""

# Required environment variables
REQUIRED_ENV_VARS = []

# Optional environment variables with metadata for setup wizard
OPTIONAL_ENV_VARS = {
    "MOONSHOT_API_KEY": {
        "description": "Moonshot/Kimi API key for web search and formula tools",
        "prompt": "Moonshot API key (get from https://platform.moonshot.cn/)",
        "url": "https://platform.moonshot.cn/",
        "tools": [
            "kimi_web_search",
            "kimi_fetch",
            "kimi_convert",
            "kimi_quickjs",
            "kimi_code_runner",
            "kimi_excel",
            "kimi_base64",
            "kimi_date"
        ],
        "password": True,
    },
    "MOONSHOT_BASE_URL": {
        "description": "Moonshot API base URL override",
        "prompt": "Moonshot API base URL (optional)",
        "default": "https://api.moonshot.cn/v1",
        "tools": [
            "kimi_web_search",
            "kimi_fetch",
            "kimi_convert",
            "kimi_quickjs",
            "kimi_code_runner",
            "kimi_excel",
            "kimi_base64",
            "kimi_date"
        ],
        "password": False,
    },
    # Tool naming prefix configuration
    "KIMI_TOOLS_PREFIX": {
        "description": "Tool name prefix (e.g., 'kimi' for kimi_web_search, 'none' for web_search_kimi + unprefixed helpers, or custom)",
        "prompt": "Tool name prefix (kimi/none/custom)",
        "default": "kimi",
        "tools": [
            "kimi_web_search",
            "kimi_fetch",
            "kimi_convert",
            "kimi_quickjs",
            "kimi_code_runner",
            "kimi_excel",
            "kimi_base64",
            "kimi_date"
        ],
        "password": False,
    },
    "KIMI_TOOLS_VERBOSE": {
        "description": "Save Moonshot tool transcripts under sessions/moonshot. Use 1/true/all for all tools, or a comma-separated list of unprefixed tool names like web_search,fetch",
        "prompt": "Transcript capture setting (optional)",
        "default": None,
        "tools": [
            "kimi_web_search",
            "kimi_fetch",
            "kimi_convert",
            "kimi_quickjs",
            "kimi_base64",
            "kimi_date"
        ],
        "password": False,
    },
    # System prompt configuration
    "KIMI_TOOLS_SYSTEM_PROMPT": {
        "description": "Custom system prompt to override default search output format",
        "prompt": "Custom system prompt (optional, overrides default formats)",
        "default": None,
        "tools": ["kimi_web_search"],
        "password": False,
    },
    "KIMI_TOOLS_SYSTEM_PROMPT_FILE": {
        "description": "Path to file containing custom system prompt",
        "prompt": "Path to system prompt file (optional)",
        "default": None,
        "tools": ["kimi_web_search"],
        "password": False,
    },
    # Config file location
    "KIMI_TOOLS_CONFIG_FILE": {
        "description": "Path to JSON configuration file for Kimi tools",
        "prompt": "Path to config file (optional)",
        "default": None,
        "tools": [
            "kimi_web_search",
            "kimi_fetch",
            "kimi_convert",
            "kimi_quickjs",
            "kimi_code_runner",
            "kimi_excel",
            "kimi_base64",
            "kimi_date"
        ],
        "password": False,
    },
}


def get_env_var_config(name: str) -> dict:
    """Get configuration for an environment variable.
    
    Args:
        name: Environment variable name
        
    Returns:
        Configuration dict or empty dict if not found
    """
    return OPTIONAL_ENV_VARS.get(name, {})


def get_tools_for_env_var(name: str) -> list:
    """Get list of tools that depend on an environment variable.
    
    Args:
        name: Environment variable name
        
    Returns:
        List of tool names
    """
    config = get_env_var_config(name)
    return config.get("tools", [])


def is_password_var(name: str) -> bool:
    """Check if an environment variable should be treated as a password.
    
    Args:
        name: Environment variable name
        
    Returns:
        True if the variable is a password
    """
    config = get_env_var_config(name)
    return config.get("password", False)


def get_all_env_vars_for_tool(tool_name: str) -> list:
    """Get all environment variables that a tool depends on.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        List of environment variable names
    """
    env_vars = []
    for env_var, config in OPTIONAL_ENV_VARS.items():
        if tool_name in config.get("tools", []):
            env_vars.append(env_var)
    return env_vars


def get_prefix_config() -> dict:
    """Get prefix configuration.
    
    Returns:
        Configuration for tool name prefix
    """
    return {
        "env_var": "KIMI_TOOLS_PREFIX",
        "default": "kimi",
        "description": "Tool name prefix configuration",
        "options": [
            {"value": "kimi", "label": "kimi_ prefix (default)", "example": "kimi_web_search"},
            {"value": "none", "label": "No prefix", "example": "web_search"},
            {"value": "custom", "label": "Custom prefix", "example": "my_web_search"},
        ]
    }


def get_system_prompt_config() -> dict:
    """Get system prompt configuration.
    
    Returns:
        Configuration for system prompt override
    """
    return {
        "direct": {
            "env_var": "KIMI_TOOLS_SYSTEM_PROMPT",
            "description": "Direct system prompt string",
        },
        "file": {
            "env_var": "KIMI_TOOLS_SYSTEM_PROMPT_FILE",
            "description": "Path to system prompt file",
        },
        "config_file": {
            "env_var": "KIMI_TOOLS_CONFIG_FILE",
            "description": "Path to JSON config file with system_prompt or system_prompt_file",
        },
        "format_styles": ["detailed", "brief", "structured", "academic"],
    }
