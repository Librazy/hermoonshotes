# Hermes Agent Kimi (Moonshot) Plugin

A Hermes Agent plugin providing advanced web search (Kimi's native [builtin `$web_search`](https://platform.kimi.com/docs/guide/use-web-search) integration) and official Moonshot Formula tools powered by Kimi/Moonshot AI.

Inspired by [OpenClaw's builtin Moonshot Plugin with Kimi `$web_search` support](https://github.com/openclaw/openclaw/blob/main/extensions/moonshot/src/kimi-web-search-provider.ts)

## Features

### Builtin Web Search (`$web_search`)
- Native integration with Kimi's built-in web search tool
- Multi-turn conversation handling for tool calling
- Customizable output formatting with multiple styles:
  - `detailed`: Structured markdown with sections and citations
  - `brief`: Concise answers with sources
  - `markdown`: Full markdown documents
  - `json`: JSON schema output
  - `academic`: APA-style citations
- AI-synthesized answers with proper citations and sources
- Configurable tool name prefix (default: `kimi_`)
- Full system prompt override support (env var or file)
- Transcript logging for debugging and auditing

### Formula Tools (Official Moonshot Formulas)
- **`fetch`**: Fetch URL content and convert to clean markdown
- **`convert`**: Comprehensive unit conversions (length, mass, temperature, currency, volume, area, etc.)
- **`quickjs`**: Safe JavaScript execution using QuickJS engine
- **`code_runner`**: Sandboxed Python code execution
- **`excel`**: Analyze and query Excel/CSV files
- **`base64`**: Base64 encode/decode operations
- **`date`**: Advanced date/time calculations and formatting

All tools include comprehensive error handling, input validation, and transcript logging.

## Installation

### Prerequisites
- Hermes Agent (from [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent))
- Python 3.8+ with `httpx` (usually included)
- API access to [Moonshot AI Platform](https://platform.moonshot.cn/)

### Method 1: Using Hermes Plugin Manager (Recommended)

```bash
# Install directly from GitHub repository
hermes plugins install Librazy/hermoonshotes

# After installation, enable if necessary
hermes plugins enable hermoonshotes
```

The `hermes plugins install` command will:
- Clone/copy to `~/.hermes/plugins/hermoonshotes/`
- Handle any `requires_env` prompts (if added to plugin.yaml)
- Update your Hermes configuration

### Method 2: Manual Installation

1. Create the plugin directory:
   ```bash
   mkdir -p ~/.hermes/plugins/hermoonshotes
   ```

2. Clone or copy the files:
   ```bash
   # Option A: Git clone
   git clone https://github.com/Librazy/hermoonshotes.git ~/.hermes/plugins/hermoonshotes

   # Option B: Copy from local development
   cp -r /path/to/hermoonshotes/* ~/.hermes/plugins/hermoonshotes/
   ```

3. Verify the structure:
   ```bash
   ls ~/.hermes/plugins/hermoonshotes/
   ```
   Expected files: `plugin.yaml`, `__init__.py`, `tools/`, `tests/`, `toolsets.py`, etc.

4. Enable the plugin:
   ```bash
   hermes plugins enable hermoonshotes
   ```

5. Restart your Hermes Agent session.

**Verification**:
```bash
hermes plugins list
# Look for "hermoonshotes" in the list
```

## Configuration

This plugin require access to Moonshot API for chat and formula tools. Kimi Code API currently does not support the formula tools.

### 1. API Key and Endpoint (Critical)

The plugin uses sophisticated configuration resolution in `tools/kimi_api_config.py`. Set **one** of the following:

#### Preferred Method (Most Explicit)
```bash
export MOONSHOT_API_KEY="sk-msh-XXXXXXXXXXXXXXXX"
export MOONSHOT_BASE_URL="https://api.moonshot.cn/v1"   # Chinese endpoint (recommended)
# or
# export MOONSHOT_BASE_URL="https://api.moonshot.ai/v1"  # International
```

#### Alternative Methods
```bash
# Chinese Moonshot (api.moonshot.cn)
export KIMI_CN_API_KEY="sk-..."

# International Moonshot (api.moonshot.ai) - IMPORTANT: key must NOT start with "sk-kimi-"
export KIMI_API_KEY="sk-..."
```

**Important Notes:**
- If your `KIMI_API_KEY` starts with `sk-kimi-` (Kimi Code API), the plugin will **disable itself** with a warning. Use `MOONSHOT_*` variables instead.
- `KIMI_BASE_URL` can override the base URL (must not be Kimi Code endpoint).
- The plugin checks availability automatically and logs warnings for misconfigurations.

**Test your configuration:**
```bash
cd $HERMES_HOME/plugins/hermoonshotes
python -c '
from tools.kimi_api_config import resolve_api_config, check_moonshot_available
print("Available:", check_moonshot_available())
key, url, warning = resolve_api_config()
print("Key:", "SET" if key else "MISSING")
print("URL:", url)
print("Warning:", warning)
'
```

### 2. Tool Prefix Configuration (`KIMI_TOOLS_PREFIX`)

Controls the names under which tools are registered:

```bash
# Default (recommended)
export KIMI_TOOLS_PREFIX="kimi_"
# Results in: kimi_web_search, kimi_fetch, kimi_convert, etc.

# No prefix (uses fallback for web_search to avoid conflict)
export KIMI_TOOLS_PREFIX="none"
# or export KIMI_TOOLS_PREFIX=""

# Custom prefix
export KIMI_TOOLS_PREFIX="moonshot_"
```

**Behavior when no prefix:**
- `web_search` → becomes `web_search_kimi` (avoids conflict with Hermes builtin)
- Other tools keep their base names (`fetch`, `convert`, etc.)

See `tools/kimi_config.py` for full logic including config file support.

### 3. System Prompt and Output Formatting

Customize the web search behavior:

```bash
# Direct prompt override
export KIMI_TOOLS_SYSTEM_PROMPT="Your custom instructions here..."

# Or use a file
export KIMI_TOOLS_SYSTEM_PROMPT_FILE="/path/to/custom-prompt.txt"
```

**Supported format styles** (passed to `get_system_prompt(style)`):
- `detailed` (default)
- `brief`
- `json`
- `markdown`
- `academic`

These affect how Kimi formats the final search results.

**Config File Support:**
Create a JSON config:
```json
{
  "prefix": "kimi_",
  "system_prompt": "Custom prompt overriding defaults..."
}
```
Then:
```bash
export KIMI_TOOLS_CONFIG_FILE="~/.config/hermes/kimi-tools.json"
```

### 4. Toolsets

The plugin ships with predefined toolsets in `toolsets.py` for easy selection in Hermes configs:

- `kimi_all`: All search + utility tools
- `kimi_search`: Web search only
- `kimi_utility`: Formula tools (fetch, convert, etc.)
- `web`: Web tools (`kimi_web_search` + `kimi_fetch`)
- `utility`: Utility tools only

Use these in your Hermes `config.yaml` or via CLI if supported.

## Usage Examples

After setup, the tools integrate seamlessly into your agent, and it will automatically call the tools when needed. 

```
────────────────────────────────────────
● Search online for user review of kimi k2.6-code-preview

Initializing agent...
────────────────────────────────────────


┌─ Reasoning ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
I'll search online for user reviews of the Kimi K2.6 Code Preview model.
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
  ┊ ⚡ preparing kimi_web_search…
  ┊ ⚡ kimi_web_ kimi k2.6 code preview user review  22.2s

┌─ Reasoning ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
I have successfully searched for user reviews of the Kimi K2.6 Code Preview model
. The search results provide a comprehensive overview of the model's release, technical
 improvements, performance benchmarks, pricing, and user feedback. I will now synthes
ize this information into a clear and concise summary for the user.
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

╭─ ⚕ Hermes ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
    Based on my search, here's a summary of user reviews and feedback for Kimi K2.6 Code Preview:
    
    ## Overall Reception
    
    Kimi K2.6 Code Preview was quietly released on April 13-14, 2026, and has received **generally positive reviews** from users. Many developers consider it a strong alternative to Claude Sonnet 4.6, with performance scores reaching the same level (89 points) in independent testing by Versun - a 6-point improvement over K2.5's 83 points.
```


**Debugging transcripts**: Tool calls are logged to `$HERMES_HOME/sessions/moonshot` (or configured path) for review if `KIMI_TOOLS_VERBOSE=true` is set.

<details>

<summary>Example of web_search transcripts (excerpted)</summary>

```web_search.jsonl
{"registered_name": "kimi_web_search", "session_id": "67263e8c-b339-4005-a0d5-7b40c9445b7f", "task_id": "20260418_223001_b7ad0b", "timestamp": "2026-04-18T14:30:24.777070+00:00", "tool_args": {"format_style": "detailed", "model": "kimi-k2.5", "query": "kimi k2.6 code preview user review", "system_prompt": "You are a tool call agent to perform `$web_search` toolcall using the given user message. Output a structured markdown strictly following the syntax below, and DO NOT ADD YOUR OWN DESCRIPTION, OPINION OR THOUGHTS.\n\n```makrdown\n# [Search Result Title 1](url-of-search-result-1)\n\n> Summary of Search Result 1\n\n* Detailed Search Result 1, paragraph 1\n* Detailed Search Result 1, paragraph 2\n\n---\n\n# [<Search Result Title 2>](url-of-search-result-2)\n\n> Summary of Search Result 2\n\n* Detailed Search Result 2, paragraph 1\n* Detailed Search Result 2, paragraph 2\n* Detailed Search Result 2, paragraph 3\n```"}, "tool_name": "web_search", "type": "metadata"}
{"messages": [{"content": "You are a tool call agent to perform `$web_search` toolcall using the given user message. Output a structured markdown strictly following the syntax below, and DO NOT ADD YOUR OWN DESCRIPTION, OPINION OR THOUGHTS.\n\n```makrdown\n# [Search Result Title 1](url-of-search-result-1)\n\n> Summary of Search Result 1\n\n* Detailed Search Result 1, paragraph 1\n* Detailed Search Result 1, paragraph 2\n\n---\n\n# [<Search Result Title 2>](url-of-search-result-2)\n\n> Summary of Search Result 2\n\n* Detailed Search Result 2, paragraph 1\n* Detailed Search Result 2, paragraph 2\n* Detailed Search Result 2, paragraph 3\n```", "role": "system"}, {"content": "kimi k2.6 code preview user review", "role": "user"}], "round": 1, "timestamp": "2026-04-18T14:30:24.777471+00:00", "type": "request"}
{"response": {"choices": [{"finish_reason": "tool_calls", "index": 0, "message": {"content": "", "role": "assistant", "tool_calls": [{"function": {"arguments": "{\"search_result\":{\"search_id\":\"e4b4d48269e395874f50a5000170f68f\"},\"usage\":{\"total_tokens\":7946}}", "name": "$web_search"}, "id": "t-web_search-69e395879d68", "type": "builtin_function"}]}}], "created": 1776522631, "id": "chatcmpl-69e395879d681300011c987c", "model": "kimi-k2.5", "object": "chat.completion", "usage": {"completion_tokens": 1, "prompt_tokens": 178, "total_tokens": 179}}, "round": 1, "timestamp": "2026-04-18T14:30:31.304201+00:00", "type": "response"}
{"messages": [{"content": "", "role": "assistant", "tool_calls": [{"function": {"arguments": "{\"search_result\":{\"search_id\":\"e4b4d48269e395874f50a5000170f68f\"},\"usage\":{\"total_tokens\":7946}}", "name": "$web_search"}, "id": "t-web_search-69e395879d68", "type": "builtin_function"}]}, {"content": "{\"search_result\":{\"search_id\":\"e4b4d48269e395874f50a5000170f68f\"},\"usage\":{\"total_tokens\":7946}}", "role": "tool", "tool_call_id": "t-web_search-69e395879d68"}], "round": 2, "timestamp": "2026-04-18T14:30:31.304382+00:00", "type": "request"}
{"response": {"choices": [{"finish_reason": "stop", "index": 0, "message": {"content": "# [Kimi K2.6 Code Preview 正式发布：万亿参数编程大模型上线](https://www.yumiok.com/archives/6077.html)\n\n> 月之暗面于2026年4月14日正式发布Kimi K2.6-code-preview，这是专为编程场景优化的万亿参数大模型。相比上一代K2.5，该模型在推理深度、代理规划质量以及多步工具调用可靠性上均有显著提升，独立评测显示编程能力评分达到89分，已达到Sonnet 4.6水平。\n\n* **性能提升**：K2.6-code-preview基于K2.5万亿参数架构，通过高质量代码数据微调和编程任务强化学习机制实现升级。在开发者Versun的独立评测中，模型得分从K2.5的83分提升至89分，提升6分。\n* **技术改进**：引入多步代理规划能力，模型可自主决策调用终端、代码搜索引擎等外部工具；对推理深度进行专项优化，思维链展现出接近顶级模型的风格。\n* **用户反馈**：从实际使用反馈来看，用户对K2.6-code-preview的评价普遍积极，指令遵循能力表现稳定，代码生成质量有明显提升。有开发者表示配合Kimi Coding Plan套餐使用，提供了强大且性价比突出的选择。\n* **定价策略**：体验该模型需订阅Kimi会员计划（Code Plan），起步价39元/月，相比海外竞品定价务实。\n\n---\n\n# [Kimi K2.6-code-preview 低調發布：萬億參數編程大模型實測達 Sonnet 4.6 水平](https://www.techritual.com/2026/04/14/507442/)\n\n> 月之暗面Kimi K2.6-code-preview低調發布，這是一款專為AI編程優化的萬億參數大模型。體驗此模型需Kimi會員帳戶，每日起價39元人民幣。從網絡測試反饋來看，此模型基於K2.5萬億參數基礎改進，主要優化聚焦AI編程。\n\n* **發布方式**：K2.6-code-preview低調發布，先前測試未大肆宣傳，這兩天才見相關討論。Kimi官方亦未大力宣傳，目前官網尚未見明顯升級標示。\n* **性能規格**：K2.5在SWE-Bench Verified榜單評分為76.8%，LiveCodeBench達85%；K2.6-code-preview在Versun自測中得分89分，比K2.5的83分提升6分。\n* **實測水平**：大V Versun評測顯示，K2.6-code-preview被網友評為Sonnet 4.6水準，已屬強勁。提升方向涵蓋推理深度、代理規劃質量及多步工具調用可靠性，有測試者指其思維鏈有Opus風格。\n* **用戶反饋**：已上線用戶反饋正面，指指令遵循能力行，表現不俗。搭配Kimi Coding Plan套餐，至少為AI編程提供強大且性價比高的選擇。\n\n---\n\n......", "role": "assistant"}}], "created": 1776522632, "id": "chatcmpl-69e3958768e1808dabfa692d", "model": "kimi-k2.5", "object": "chat.completion", "usage": {"completion_tokens": 1971, "prompt_tokens": 8182, "total_tokens": 10153}}, "round": 2, "timestamp": "2026-04-18T14:30:46.955420+00:00", "type": "response"}
```

</details>

<details>

<summary>Example of base64 transcripts</summary>

```base64.json
{
  "metadata": {},
  "registered_name": "base64",
  "request": {
    "api_tool_name": "base64_encode",
    "arguments": {
      "data": "阿里千问开源 Qwen3.6-35B-A3B：350亿总参数仅激活30亿，主打智能体编程能力",
      "encoding": "utf-8"
    },
    "formula_uri": "moonshot/base64:latest"
  },
  "response": {
    "fiber_id": "fiber-f9joui8sm8pi159nayg1",
    "result": "6Zi/6YeM5Y2D6Zeu5byA5rqQIFF3ZW4zLjYtMzVCLUEzQu+8mjM1MOS6v+aAu+WPguaVsOS7hea/gOa0uzMw5Lq/77yM5Li75omT5pm66IO95L2T57yW56iL6IO95Yqb",
    "status": "success"
  },
  "saved_at": "2026-04-18T10:32:32.368662+00:00",
  "task_id": "20260418_183223_0f7899",
  "tool_name": "base64"
}
```

</details>

## Troubleshooting

**Common Issues:**

1. **"Tool not available" or missing from list**
   - Run the API config test above
   - Check `hermes plugins list`
   - Ensure `MOONSHOT_API_KEY` (or equivalent) is set **before** starting Hermes
   - Check logs for warnings about KIMI_API_KEY prefix

2. **API Errors / Rate Limits**
   - Verify your API key has sufficient quota on [platform.moonshot.cn](https://platform.moonshot.cn/)
   - Check base URL matches your key type

3. **Plugin not loading**
   - Check `~/.hermes/config.yaml` for disabled plugins list
   - Run `hermes plugins enable hermoonshotes`
   - Verify Python imports work (no missing deps)

4. **System prompt not taking effect**
   - Set `KIMI_TOOLS_SYSTEM_PROMPT` *before* starting Hermes (caching is used)

## Development & Testing

```bash
# Run tests
cd ~/.hermes/plugins/hermoonshotes
pytest tests/

# Test specific components
python -m pytest tests/tools/test_kimi_api_config.py -q
```

## References

- [Moonshot AI Platform](https://platform.moonshot.cn/)
- [KIMK API Documentation](https://platform.kimi.com/docs/guide/use-official-tools/)
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
