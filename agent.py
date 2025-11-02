"""
Agent module that handles function calling with Ollama.
This enables the LLM to automatically decide when to use tools based on the prompt.
"""
import requests
import json
from typing import Any, Dict, List, Optional
import yaml
import os
import logging

from web_tools import reddit_search, web_fetch

logger = logging.getLogger("genie")

# Load config
def load_config():
    config_path = "config.yaml"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            logger.warning(f"Failed to load config.yaml: {e}, using defaults")
    return {}

_config = load_config()
OLLAMA_CHAT_URL = _config.get("ollama_chat_url", "http://localhost:11434/api/chat")
MODEL = _config.get("model", "qwen2.5:7b-instruct")
TIMEOUT = _config.get("timeout", 60)

# Define available tools for the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "reddit_search",
            "description": "Search Reddit for posts matching a query. Use this when the user asks about Reddit posts, discussions, or content on Reddit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find Reddit posts about"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch content from a URL. Use this when the user asks to fetch, retrieve, or read content from a website or URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch content from"
                    }
                },
                "required": ["url"]
            }
        }
    }
]

# Tool execution functions
TOOL_FUNCTIONS = {
    "reddit_search": lambda args: reddit_search(args.get("query", ""), args.get("limit", 5)),
    "web_fetch": lambda args: web_fetch(args.get("url", ""))
}

def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """Execute a tool function with the provided arguments."""
    if tool_name not in TOOL_FUNCTIONS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    logger.info(f"Executing tool: {tool_name} with args: {arguments}")
    try:
        result = TOOL_FUNCTIONS[tool_name](arguments)
        return result
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {"error": str(e)}

def chat_with_tools(messages: List[Dict[str, str]], max_iterations: int = 5) -> str:
    """
    Chat with Ollama using function calling.
    Handles the agent loop: LLM decides to call tools, tools execute, results fed back.
    """
    iterations = 0
    
    while iterations < max_iterations:
        iterations += 1
        
        # Prepare the request to Ollama
        request_data = {
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "stream": False
        }
        
        try:
            response = requests.post(
                OLLAMA_CHAT_URL,
                json=request_data,
                timeout=TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Ollama request failed: {e}")
        
        # Extract the assistant's message
        assistant_message = data.get("message", {})
        content = assistant_message.get("content", "")
        tool_calls = assistant_message.get("tool_calls", [])
        
        # Add assistant's response to messages
        messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls if tool_calls else None
        })
        
        # If no tool calls, we're done - return the final answer
        if not tool_calls:
            return content
        
        # Execute tools and add results to messages
        tool_results = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            tool_args_raw = tool_call.get("function", {}).get("arguments", "{}")
            
            # Parse arguments (Ollama sometimes returns string, sometimes dict)
            if isinstance(tool_args_raw, str):
                try:
                    tool_args = json.loads(tool_args_raw)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse tool arguments: {tool_args_raw}")
                    tool_args = {}
            else:
                tool_args = tool_args_raw
            
            # Execute the tool
            tool_result = execute_tool(tool_name, tool_args)
            
            # Add tool result to messages
            tool_results.append({
                "role": "tool",
                "content": json.dumps(tool_result, default=str),
                "name": tool_name
            })
        
        # Add tool results to messages for next iteration
        messages.extend(tool_results)
        
        # Continue the loop to let LLM process tool results
    
    # If we hit max iterations, return what we have
    return messages[-1].get("content", "Maximum iterations reached. Please try again.")

def ask_with_tools(prompt: str) -> str:
    """
    Ask the LLM a question with automatic tool use.
    The LLM will decide whether to use tools based on the prompt.
    """
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant with access to tools. When users ask you to search, fetch, or retrieve information from the web or Reddit, use the appropriate tools."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    return chat_with_tools(messages)

