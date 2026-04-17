"""Toolset definitions for Hermes Agent.

This module defines the available toolsets and their composition.
"""

# Core tools available in all configurations
_HERMES_CORE_TOOLS = [
    # Existing core tools would be listed here
    # "file_read",
    # "file_write",
    # "bash",
    # ...
    
    # Kimi web search tools
    "kimi_web_search",
    "kimi_fetch",
]

# Toolset definitions
TOOLSETS = {
    "core": {
        "description": "Core Hermes tools",
        "tools": _HERMES_CORE_TOOLS,
        "includes": []
    },
    
    # Kimi toolsets
    "kimi_search": {
        "description": "Kimi AI web search tools",
        "tools": ["kimi_web_search"],
        "includes": []
    },
    
    "kimi_utility": {
        "description": "Kimi formula utility tools",
        "tools": [
            "kimi_fetch",
            "kimi_convert",
            "kimi_quickjs",
            "kimi_code_runner",
            "kimi_excel",
            "kimi_base64",
            "kimi_date"
        ],
        "includes": []
    },
    
    "kimi_all": {
        "description": "All Kimi tools (search + utility)",
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
        "includes": []
    },
    
    # Web tools collection
    "web": {
        "description": "Web-related tools including search and fetch",
        "tools": [
            "kimi_web_search",
            "kimi_fetch"
        ],
        "includes": []
    },
    
    # Utility tools collection
    "utility": {
        "description": "Utility tools for code execution, conversion, etc.",
        "tools": [
            "kimi_convert",
            "kimi_quickjs",
            "kimi_code_runner",
            "kimi_excel",
            "kimi_base64",
            "kimi_date"
        ],
        "includes": []
    }
}


def get_toolset(name: str) -> dict:
    """Get a toolset by name.
    
    Args:
        name: Toolset name
        
    Returns:
        Toolset definition or empty dict if not found
    """
    return TOOLSETS.get(name, {"tools": [], "includes": []})


def expand_toolset(name: str, visited: set = None) -> list:
    """Expand a toolset to get all included tools.
    
    Args:
        name: Toolset name
        visited: Set of already visited toolsets (for recursion detection)
        
    Returns:
        List of tool names
    """
    if visited is None:
        visited = set()
    
    if name in visited:
        return []
    
    visited.add(name)
    toolset = get_toolset(name)
    tools = list(toolset.get("tools", []))
    
    # Recursively include other toolsets
    for included in toolset.get("includes", []):
        tools.extend(expand_toolset(included, visited))
    
    return list(dict.fromkeys(tools))  # Remove duplicates while preserving order


def list_toolsets() -> list:
    """List all available toolset names.
    
    Returns:
        List of toolset names
    """
    return list(TOOLSETS.keys())
