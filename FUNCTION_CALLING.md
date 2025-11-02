# How Function Calling Works in Genie

## The Problem You Identified

You asked: **"If I write 'search the web for apples', how does Ollama understand it needs to use the search tool?"**

The original implementation (`llm.py`) had **no automatic tool use** - it just sent prompts directly to Ollama without giving it access to tools. The LLM couldn't decide to use tools on its own.

## The Solution: Function Calling

I've added `agent.py` which implements **function calling** (also called "tool use"). This allows the LLM to:

1. **See available tools** (Reddit search, web fetch)
2. **Decide when to use them** based on the user's prompt
3. **Execute tools automatically** and get results
4. **Use results in its response**

## How It Works

### Step-by-Step Flow

```
1. User: "search the web for apples"
   ↓
2. agent.py sends to Ollama:
   - The user's prompt
   - List of available tools (reddit_search, web_fetch)
   ↓
3. Ollama analyzes the prompt and decides:
   "User wants to search → I should call web_fetch tool"
   ↓
4. Ollama returns: tool_call request
   {
     "tool_calls": [{
       "function": {
         "name": "web_fetch",
         "arguments": {"url": "https://..."}
       }
     }]
   }
   ↓
5. agent.py executes the tool:
   - Calls web_fetch() from web_tools.py
   - Gets the web content
   ↓
6. agent.py sends results back to Ollama:
   "Here's what I found on the web about apples..."
   ↓
7. Ollama generates final response using the tool results
   ↓
8. User gets: "I searched the web and found that apples..."
```

## MCP vs Native Function Calling

### Your Question About MCP

**MCP (Model Context Protocol)** is a standardized protocol for tool/function calling, but **it's not required**. 

Ollama supports function calling natively via:
- `/api/chat` endpoint
- `tools` parameter (JSON schema)
- `tool_calls` in responses

### When You Might Use MCP

MCP is useful if:
- You want a standardized protocol across different LLM providers
- You're building complex multi-agent systems
- You need tool discovery/routing across services
- You want to integrate with MCP-compatible tools

### Our Approach

We use **Ollama's native function calling** because:
- Simpler (no extra protocol layer)
- Direct integration with Ollama
- Works well for local setups
- Less overhead

## Usage

### Automatic Tool Use (Default)

```bash
curl "http://localhost:8000/ask?prompt=search%20reddit%20for%20python%20tutorials"
```

The LLM will:
1. See the prompt mentions "reddit"
2. Automatically call `reddit_search("python tutorials")`
3. Return results in its response

### Disable Tool Use

```bash
curl "http://localhost:8000/ask?prompt=hello&use_tools=false"
```

This uses the simple `llm.py` approach without tools.

## Technical Details

The `agent.py` module:
- Defines tools in JSON Schema format
- Implements an agent loop (LLM → tool → LLM → response)
- Handles tool execution and error handling
- Supports multiple tool calls in one conversation

## Comparison

| Feature | `llm.py` (simple) | `agent.py` (function calling) |
|---------|-------------------|-------------------------------|
| Tool access | ❌ No | ✅ Yes |
| Automatic tool use | ❌ No | ✅ Yes |
| LLM decides tools | ❌ No | ✅ Yes |
| Agent loop | ❌ No | ✅ Yes |
| Complexity | Simple | More complex |

## Future: MCP Integration

If you want MCP support, you could:
1. Create an MCP server that wraps `web_tools.py`
2. Use an MCP client library
3. Route between MCP tools and direct function calls

But for now, native Ollama function calling is simpler and works great!

