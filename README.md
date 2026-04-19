# Hermes Agent Kimi (Moonshot) Plugin

A Hermes Agent plugin providing advanced web search (via Moonshot Formula `web_search` tool) and official Moonshot Formula tools powered by Kimi/Moonshot AI.

Inspired by [OpenClaw's builtin Moonshot Plugin with Kimi `$web_search` support](https://github.com/openclaw/openclaw/blob/main/extensions/moonshot/src/kimi-web-search-provider.ts)

## Features

### Web Search (Formula Tool)
- Formula-based forced tool call workflow for guaranteed search execution
- Direct call to `moonshot/web-search:latest` formula endpoint
- Multi-turn conversation handling with pre-populated search results
- Customizable output formatting with multiple styles:
  - `detailed`: Structured markdown with sections and citations
  - `brief`: Concise answers with sources
  - `markdown`: Full markdown documents
  - `json`: JSON schema output (enables `response_format: json_object`)
  - `academic`: APA-style citations
- AI-synthesized answers with proper citations and sources
- Configurable tool name prefix (default: `kimi_`)
- Full system prompt override support (env var or file)
- Detailed JSONL transcript logging for debugging and auditing

### Formula Tools (Official Moonshot Formulas)
- **`fetch`**: Fetch URL content and convert to clean markdown
- **`convert`**: Comprehensive unit conversions (length, mass, temperature, currency, volume, area, etc.)
- **`quickjs`**: Safe JavaScript execution using QuickJS engine
- **`code_runner`**: Sandboxed Python code execution
- **`excel`**: Analyze and query Excel/CSV files
- **`base64`**: Base64 encode/decode operations
- **`date`**: Advanced date/time calculations and formatting

All tools include comprehensive error handling, input validation, and transcript logging.

### API Debugging
- **`api-debugger.sh`**: Shell script for debugging formula tool calls interactively

  Usage:
  ```bash
  cd tools && ./api-debugger.sh
  ```
  Supports interactive testing of formula tools with customizable prompts and arguments.

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

This plugin requires access to Moonshot API for chat and formula tools. Kimi Code API currently does not support the formula tools.

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
- `json` (enables `response_format: json_object`)
- `markdown`
- `academic`

These affect how the agent formats the final search results. When `json` format is selected, JSON mode is automatically enabled for structured output.

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
{"registered_name": "kimi_web_search", "session_id": "5dca2c76-17e1-4aff-8af8-01518db58b92", "task_id": "20260420_014017_43213d", "timestamp": "2026-04-19T17:40:24.542618+00:00", "tool_args": {"format_style": "detailed", "model": "kimi-k2.5", "query": "kimi k2.6-code-preview", "system_prompt": "You are a search result formatting agent. Format the provided web search results as structured markdown strictly following the syntax below, and DO NOT ADD YOUR OWN DESCRIPTION, OPINION OR THOUGHTS.\n\n```markdown\n# [Search Result Title 1](url-of-search-result-1)\n\n> Summary of Search Result 1\n\n* Detailed Search Result 1, paragraph 1\n* Detailed Search Result 1, paragraph 2\n\n---\n\n# [<Search Result Title 2>](url-of-search-result-2)\n\n> Summary of Search Result 2\n\n* Detailed Search Result 2, paragraph 1\n* Detailed Search Result 2, paragraph 2\n* Detailed Search Result 2, paragraph 3\n```"}, "tool_name": "web_search", "type": "metadata"}
{"formula_uri": "moonshot/web-search:latest", "payload": {"arguments": "{\"query\": \"kimi k2.6-code-preview\"}", "name": "web_search"}, "timestamp": "2026-04-19T17:40:24.542957+00:00", "type": "formula_request"}
{"response": {"access_token_id": "ak-deadbeef", "context": {"encrypted_output": "----MOONSHOT ENCRYPTED BEGIN----jtMnIdZdeh8tafe3HEle15GtcDzDylElrLqVoS----MOONSHOT ENCRYPTED END----", "input": "{\"name\":\"web_search\",\"arguments\":\"{\\\"query\\\": \\\"kimi k2.6-code-preview\\\"}\"}", "references": {"tool_call": {"function": {"arguments": "{\"query\": \"kimi k2.6-code-preview\"}", "name": "web_search"}, "type": "function"}}}, "created_at": 1776620424, "formula": "moonshot/web-search:latest", "id": "fiber-deadbeef", "lambda_id": "lambda-deadbeef", "object": "fiber", "organization_id": "org-deadbeef", "project_id": "proj-deadbeef", "status": "succeeded"}, "timestamp": "2026-04-19T17:40:29.998744+00:00", "type": "formula_response"}
{"payload": {"messages": [{"content": "You are a search result formatting agent. Format the provided web search results as structured markdown strictly following the syntax below, and DO NOT ADD YOUR OWN DESCRIPTION, OPINION OR THOUGHTS.\n\n```markdown\n# [Search Result Title 1](url-of-search-result-1)\n\n> Summary of Search Result 1\n\n* Detailed Search Result 1, paragraph 1\n* Detailed Search Result 1, paragraph 2\n\n---\n\n# [<Search Result Title 2>](url-of-search-result-2)\n\n> Summary of Search Result 2\n\n* Detailed Search Result 2, paragraph 1\n* Detailed Search Result 2, paragraph 2\n* Detailed Search Result 2, paragraph 3\n```", "role": "system"}, {"content": "kimi k2.6-code-preview", "role": "user"}, {"content": "", "role": "assistant", "tool_calls": [{"function": {"arguments": "{\"query\": \"kimi k2.6-code-preview\", \"classes\": [\"all\"]}", "name": "web_search"}, "id": "web_search:0", "type": "function"}]}, {"content": "----MOONSHOT ENCRYPTED BEGIN----jtMnIdZdeh8tafe3HEle15GtcDzDylElrLqVoS----MOONSHOT ENCRYPTED END----", "role": "tool", "tool_call_id": "web_search:0"}], "model": "kimi-k2.5", "thinking": {"type": "disabled"}, "tools": [{"function": {"description": "用于信息检索的网络搜索", "name": "web_search", "parameters": {"properties": {"classes": {"description": "要关注的搜索领域。如果未指定，则默认为 'all'。", "items": {"enum": ["all", "academic", "social", "library", "finance", "code", "ecommerce", "medical"], "type": "string"}, "type": "array"}, "query": {"description": "要搜索的内容", "type": "string"}}, "required": ["query"], "type": "object"}}, "type": "function"}]}, "timestamp": "2026-04-19T17:40:29.999002+00:00", "type": "chat_request"}
{"response": {"choices": [{"finish_reason": "stop", "index": 0, "message": {"content": "```markdown\n# [Kimi K2.6 Code Preview Benchmark Results, Specs & Pricing](https://www.datalearner.com/en/ai-models/pretrained-models/kimi-k2.6-code-preview)\n\n> Kimi K2.6 Code Preview是月之暗面（Moonshot AI）在Kimi K2系列基础上推出的下一代代码与智能体（Agent）模型，目前处于内测阶段，尚未正式发布。该模型采用混合专家（MoE）架构，总参数量为1万亿（1T），激活参数量为320亿（32B），上下文长度为256K tokens。\n\n* 2026年4月13日，月之暗面通过官方邮件首次确认Beta测试者所使用的模型为K2.6-code-preview，并表示团队正在根据测试反馈进行最终调整，该模型即将面向所有用户开放。\n* Kimi K2系列采用MoE架构，包含384个专家，每个token激活8个专家，系列模型知识截止时间为2025年4月。\n* Kimi K2.5于2026年1月底发布，在原K2基础上加强了多模态能力，并推出了多智能体集群（Agent Swarm）功能，K2.5在SWE-bench Verified基准测试中取得76.8%的得分。\n* K2系列在15.5万亿token上进行训练，团队设计了MuonClip优化器以解决MoE架构训练中常见的注意力爆炸与损失尖峰问题。\n\n---\n\n# [Kimi K2.6-code-preview即将上线：月之暗面编程模型小幅升级预览](https://unifuncs.com/s/XrojHS6o)\n\n> 月之暗面旗下AI编程工具Kimi Code向Beta测试者发送邮件，宣布抢先体验计划本期已结束，并首次确认测试者使用的模型为K2.6-code-preview。\n\n* 根据社区讨论，K2.6-code-preview在测试期间展现出推理深度提升的特征，相较于K2.5，逻辑推理能力有可感知的增强。\n* Agent规划能力得到优化，工具调用与任务拆解更加精准。\n* 此前Beta测试者已注意到内测模型性能较K2.5有明显提升，尤其在推理深度和Agent规划能力方面，但在控制台中仍显示为K2.5。\n```", "role": "assistant"}}], "created": 1776620430, "id": "chatcmpl-deadbeef", "model": "kimi-k2.5", "object": "chat.completion", "usage": {"cached_tokens": 256, "completion_tokens": 476, "prompt_tokens": 1501, "prompt_tokens_details": {"cached_tokens": 256}, "total_tokens": 1977}}, "timestamp": "2026-04-19T17:40:42.423888+00:00", "type": "chat_response"}

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
    "fiber_id": "fiber-deadbeef",
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
- [KIMI API Documentation](https://platform.kimi.com/docs/guide/use-official-tools/)
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
