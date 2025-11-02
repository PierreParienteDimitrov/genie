import requests
from typing import Any
import yaml
import os
import logging

logger = logging.getLogger("genie")

# Load config if available, otherwise use defaults
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
OLLAMA_URL = _config.get("ollama_url", "http://localhost:11434/api/generate")
MODEL = _config.get("model", "qwen2.5:7b-instruct")
TIMEOUT = _config.get("timeout", 60)

def _extract_text(resp_json: Any) -> str:
    # Guard against different possible response shapes
    if not isinstance(resp_json, dict):
        return ""
    # Common shapes: {'response': '...'} or {'outputs': [{'content': '...'}]}
    if "response" in resp_json:
        return resp_json.get("response") or ""
    outputs = resp_json.get("outputs")
    if outputs and isinstance(outputs, list):
        first = outputs[0]
        # Ollama-like shape: {'content': '...'} sometimes nested
        if isinstance(first, dict):
            return first.get("content") or first.get("text") or ""
    # Fallbacks
    return resp_json.get("text", "") or ""

def ask_qwen(prompt: str) -> str:
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Ollama request failed: {e}")

    try:
        data = r.json()
    except ValueError:
        raise RuntimeError("Ollama returned non-JSON response")

    text = _extract_text(data)
    if not text:
        logger.warning(f"Empty response from Ollama. Raw response: {data}")
        raise RuntimeError("Ollama returned empty response")
    return text


