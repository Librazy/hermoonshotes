# Hermes Agent Kimi Plugin

A Hermes Agent plugin providing web search and formula tools powered by Moonshot/Kimi AI.

## Features

### Builtin Web Search (`$web_search`)
- Native Kimi web search with customizable output formatting
- Supports multiple output styles: detailed, brief, structured, academic
- Returns AI-synthesized answers with citations
- Configurable tool name prefix
- Custom system prompt override support

### Formula Tools
- **fetch**: Fetch and extract content from URLs (markdown-formatted)
- **convert**: Unit conversion (length, mass, temperature, currency, etc.)
- **quickjs**: Execute JavaScript code safely using QuickJS engine
- **code_runner**: Execute Python code in sandboxed environment
- **excel**: Analyze Excel/CSV file content
- **base64**: Base64 encode/decode data
- **date**: Date and time operations

## Installation

1. Copy the plugin files to your Hermes Agent installation:
   ```bash
   cp -r tools/ /path/to/hermes/
   cp toolsets.py /path/to/hermes/
   cp -r hermes_cli/ /path/to/hermes/
   ```

2. Install dependencies:
   ```bash
   pip install httpx
   ```

3. Set up your API key:
   ```bash
   export MOONSHOT_API_KEY="sk-..."
   ```

## Configuration

### Environment Variables

#### API Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `MOONSHOT_API_KEY` | API key for Moonshot/Kimi | Yes |
| `MOONSHOT_BASE_URL` | API base URL override | No (default: https://api.moonshot.cn/v1) |

#### Tool Naming Prefix Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `KIMI_TOOLS_PREFIX` | Tool name prefix | `kimi` |

The prefix controls how tools are named when registered:

- **`kimi`** (default): Tools are named `kimi_web_search`, `kimi_fetch`, etc.
- **`none`**: Safe tools have no prefix, while search falls back to `web_search_kimi`: `web_search_kimi`, `fetch`, etc.
- **Custom**: Any custom prefix: e.g., `my_` produces `my_web_search`, `my_fetch`, etc.

Examples:
```bash
# Default kimi prefix
export KIMI_TOOLS_PREFIX="kimi"
# Tools: kimi_web_search, kimi_fetch, kimi_convert, ...

# No prefix
export KIMI_TOOLS_PREFIX="none"
# Tools: web_search_kimi, fetch, convert, ...

# Custom prefix
export KIMI_TOOLS_PREFIX="my"
# Tools: my_web_search, my_fetch, my_convert, ...
```

#### System Prompt Configuration

| Variable | Description |
|----------|-------------|
| `KIMI_TOOLS_SYSTEM_PROMPT` | Direct custom system prompt string |
| `KIMI_TOOLS_SYSTEM_PROMPT_FILE` | Path to file containing custom system prompt |
| `KIMI_TOOLS_CONFIG_FILE` | Path to JSON configuration file |
| `KIMI_TOOLS_VERBOSE` | Save JSON tool transcripts under `sessions/moonshot` |

The system prompt controls how the search results are formatted. You can override the default prompts:

```bash
# Direct system prompt
export KIMI_TOOLS_SYSTEM_PROMPT="You are a helpful assistant. Provide concise answers with sources."

# System prompt from file
export KIMI_TOOLS_SYSTEM_PROMPT_FILE="/path/to/prompt.txt"

# Or use one of the built-in format styles via the tool parameter
# format_style: detailed | brief | structured | academic

# Save transcripts for every Moonshot tool call
export KIMI_TOOLS_VERBOSE="all"

# Or only save selected unprefixed tool names
export KIMI_TOOLS_VERBOSE="web_search,fetch,date"
```

#### Config File

You can also use a JSON configuration file:

```bash
export KIMI_TOOLS_CONFIG_FILE="/path/to/kimi-config.json"
```

Example config file:
```json
{
  "prefix": "my",
  "system_prompt": "Custom system prompt for all searches",
  "system_prompt_file": "/path/to/alternative-prompt.txt"
}
```

Configuration priority (highest to lowest):
1. Environment variables (`KIMI_TOOLS_PREFIX`, `KIMI_TOOLS_SYSTEM_PROMPT`)
2. Config file specified by `KIMI_TOOLS_CONFIG_FILE`
3. Default values

### Toolsets

The plugin provides several toolsets:

- `kimi_search`: Web search only (`kimi_web_search`)
- `kimi_utility`: Utility tools only (`kimi_fetch`, `kimi_convert`, etc.)
- `kimi_all`: All Kimi tools
- `web`: Web-related tools (`kimi_web_search`, `kimi_fetch`)
- `utility`: Utility tools collection

Note: Toolset names are fixed, but individual tool names within them follow the `KIMI_TOOLS_PREFIX` setting.

## Usage

### CLI Usage

```bash
# Search with default (detailed) format
hermes chat -q "kimi_web_search: latest developments in quantum computing"

# Search with brief format
hermes chat -q "Use kimi_web_search with format_style=brief to find the weather in Tokyo"

# Search with custom system prompt
hermes chat -q "Use kimi_web_search with system_prompt='Provide only bullet points' to search for Python tips"

# Fetch URL content
hermes chat -q "kimi_fetch: https://news.ycombinator.com"

# Unit conversion
hermes chat -q "kimi_convert: 5 feet to meters"

# Execute code
hermes chat -q "kimi_code_runner: print([x**2 for x in range(10)])"
```

With custom prefix (e.g., `KIMI_TOOLS_PREFIX=none`):
```bash
hermes chat -q "web_search_kimi: latest AI news"
hermes chat -q "fetch: https://example.com"
```

### Programmatic Usage

```python
from tools.kimi_builtin_search import kimi_builtin_search
from tools.kimi_config import get_config

# Search with default config
result = kimi_builtin_search(
    query="machine learning trends 2024",
    format_style="structured"
)
print(result)

# Search with custom system prompt
result = kimi_builtin_search(
    query="Python best practices",
    system_prompt="Provide answers in markdown bullet points only."
)

# Fetch
from tools.kimi_formula_tools import kimi_fetch_tool
result = kimi_fetch_tool("https://docs.python.org/3/")
print(json.loads(result))

# Check current prefix configuration
config = get_config()
print(f"Current prefix: {config.get_prefix()}")
print(f"Prefixed name: {config.apply_prefix('web_search')}")
```

## Architecture

The plugin follows the same architectural pattern used by OpenClaw's Moonshot plugin:

- **Decoupled**: Web search works independently of the LLM provider
- **Pluggable**: Tools register via Hermes registry, auto-discovered at startup
- **Configurable**: Supports API keys via env vars or config files
- **Fallback Chain**: Multiple credential sources with clear priority

### File Structure

```
hermes/
├── tools/
│   ├── registry.py              # Tool registry (existing)
│   ├── kimi_config.py           # Configuration management
│   ├── kimi_builtin_search.py   # Builtin $web_search implementation
│   └── kimi_formula_tools.py    # Formula tools wrapper
├── toolsets.py                  # Toolset definitions
├── hermes_cli/
│   └── config.py               # Environment variable configuration
└── tests/
    └── tools/
        ├── test_kimi_tools.py  # Unit tests for tools
        └── test_kimi_config.py # Unit tests for configuration
```

## Testing

Run unit tests:

```bash
# Run all tests
pytest tests/tools/

# Run with verbose output
pytest tests/tools/ -v

# Run specific test file
pytest tests/tools/test_kimi_config.py -v

# Run integration tests (requires API key)
export MOONSHOT_API_KEY="sk-..."
pytest tests/tools/ -v -m slow
```

## API Reference

### Kimi Builtin Search

```python
kimi_builtin_search(
    query: str,                    # Search query
    model: str = "kimi-k2.5",      # Model to use
    format_style: str = "detailed", # Output format
    system_prompt: Optional[str] = None  # Custom system prompt override
) -> str  # JSON string with results
```

### Configuration

```python
from tools.kimi_config import get_config

config = get_config()

# Get current prefix
prefix = config.get_prefix()  # e.g., "kimi_" or ""

# Apply prefix to tool name
full_name = config.apply_prefix("web_search")  # e.g., "kimi_web_search"

# Get system prompt
prompt = config.get_system_prompt("detailed")

# Get available format styles
styles = config.get_available_format_styles()
# ["detailed", "brief", "structured", "academic"]

# Clear cache if config changes at runtime
config.clear_cache()
```

### Formula Tools

```python
# Fetch URL content
kimi_fetch_tool(url: str) -> str

# Unit conversion
kimi_convert_tool(value: float, from_unit: str, to_unit: str) -> str

# Execute JavaScript
kimi_quickjs_tool(code: str) -> str

# Execute Python
kimi_code_runner_tool(code: str, language: str = "python") -> str

# Analyze Excel/CSV
kimi_excel_tool(file_content: str, operation: str = "analyze") -> str

# Base64 encode/decode
kimi_base64_tool(data: str, operation: str = "encode") -> str

# Date operations
kimi_date_tool(operation: str = "now", format: str = "iso") -> str
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "API key not configured" | Missing env var | Set `MOONSHOT_API_KEY` |
| "tool_calls not found" | Invalid request format | Check system prompt and thinking settings |
| "Max rounds exceeded" | Loop detection failed | Check API response format |
| Empty results | Search returned no hits | Try different query |
| Tool not found | Prefix mismatch | Check `KIMI_TOOLS_PREFIX` setting |

## License

MIT License

## References

- [Moonshot AI Platform](https://platform.moonshot.cn/)
- [Kimi API Documentation](https://platform.kimi.com/docs/)
- [Hermes Agent Documentation](https://github.com/chaitin/hermes)
- [OpenClaw Moonshot Plugin](../moonshot/) (Reference implementation)
