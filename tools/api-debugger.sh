#!/bin/bash

export QUERY="月之暗面最近有什么消息"
export FORMULA_URI="moonshot/web-search:latest"                                                                                          
export MOONSHOT_BASE_URL="https://api.moonshot.cn/v1"
export RESULT=$(curl -fSL -X POST ${MOONSHOT_BASE_URL}/formulas/${FORMULA_URI}/fibers \-H "Content-Type: application/json" \-H "Authorization: Bearer $KIMI_CN_API_KEY" \
-d '{
  "name": "web_search",
  "arguments": "{\"query\": \"'"${QUERY}"'\"}"
}')

export SEARCH_RESULT=$(echo "${RESULT}" | jq -r '.context.output // empty')

if [ -z "${SEARCH_RESULT}" ]; then
  export SEARCH_RESULT=$(echo "${RESULT}" | jq -r '.context.encrypted_output // empty')
  if [ -z "${SEARCH_RESULT}" ]; then
    echo "Failed to get search output: ${RESULT}"
    exit 1
  fi
fi

read -r -d '' MESSAGE_JSON << 'EOF'
{
  "model": "kimi-k2.5",
  "messages": [
    {
      "role": "system",
      "content": "Output the `web_search` result as a structured markdown strictly following the syntax below, and DO NOT ADD YOUR OWN DESCRIPTION, OPINION OR THOUGHTS.\n\n```makrdown\n# [Search Result Title 1](url-of-search-result-1)\n\n> Summary of Search Result 1\n\n* Detailed Search Result 1, paragraph 1\n* Detailed Search Result 1, paragraph 2\n\n---\n\n# [<Search Result Title 2>](url-of-search-result-2)\n\n> Summary of Search Result 2\n\n* Detailed Search Result 2, paragraph 1\n* Detailed Search Result 2, paragraph 2\n* Detailed Search Result 2, paragraph 3\n```"
    },
    {
      "role": "user",
      "content": "${QUERY}"
    },
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "index": 0,
          "id": "web_search:0",
          "type": "function",
          "function": {
            "name": "web_search",
            "arguments": "{\"query\": \"${QUERY}\", \"classes\": [\"all\"]}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "content": "${SEARCH_RESULT}",
      "tool_call_id": "web_search:0"
    }
  ],
  "temperature": 0.6,
  "max_tokens": 32768,
  "top_p": 0.95,
  "stream": true,
  "tools": [
    {
      "function": {
        "name": "web_search",
        "description": "用于信息检索的网络搜索",
        "parameters": {
          "properties": {
            "classes": {
              "description": "要关注的搜索领域。如果未指定，则默认为 'all'。",
              "items": {
                "enum": [
                  "all",
                  "academic",
                  "social",
                  "library",
                  "finance",
                  "code",
                  "ecommerce",
                  "medical"
                ],
                "type": "string"
              },
              "type": "array"
            },
            "query": {
              "description": "要搜索的内容",
              "type": "string"
            }
          },
          "required": [
            "query"
          ],
          "type": "object"
        }
      },
      "type": "function"
    }
  ],
  "thinking": {
    "type": "disabled"
  },
  "stream": false
}
EOF

export MESSAGE_JSON=$(echo "${MESSAGE_JSON}" | envsubst)

# echo "${MESSAGE_JSON}"
curl 'https://api.moonshot.cn/v1/chat/completions' -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $KIMI_CN_API_KEY" --data-binary "${MESSAGE_JSON}"