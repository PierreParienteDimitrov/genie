# 🧞 Genie — Local AI Assistant (cleaned & improved)

This guide shows a robust, repeatable local setup that combines:

- Ollama (Qwen) as a local LLM backend
- Open WebUI as the chat interface (Docker)
- A small FastAPI "Genie" server to expose tools (search, fetch) to the model
- A short `genie` launcher to start the pieces locally

This version adds explicit prerequisites, safer example code (error handling, validation), and verification/troubleshooting steps.

## 🚀 Architecture (quick)

```
Web UI (Docker)
    ↓
Genie API (FastAPI)  ← web tools (reddit, fetch)
    ↓
Ollama (Qwen) localhost:11434
```

## 📁 Suggested repo layout

```
genie/
 ├── server.py          # FastAPI app (example)
 ├── llm.py             # Ollama / Qwen client (example)
 ├── web_tools.py       # Reddit + web fetch helpers (example)
 ├── config.yaml        # optional runtime settings
 ├── requirements.txt   # pinned deps
 ├── start_genie.sh     # recommended launcher script
 └── venv/              # (optional) local virtualenv
```

## ✅ Prerequisites (explicit)

- macOS (this guide). Ensure you have:
  - Docker (and Docker Desktop) installed and running
  - Ollama installed (https://ollama.ai) - CLI available as `ollama`
  - Python 3.10+ (brew or installer)
  - Git (optional for cloning)

Install Python and create the virtualenv (example):

```bash
brew install python
python3 -m venv venv
source venv/bin/activate
```

Create a `requirements.txt` and install:

```text
fastapi==0.115.0
uvicorn[standard]==0.32.0
requests==2.32.3
pyyaml==6.0.2
pydantic==2.9.2
```

Then:

```bash
pip install -r requirements.txt
```

Notes about Ollama & Qwen:

- Ensure Ollama daemon is running. You can verify with `ollama status` or `curl http://localhost:11434` (depends on your Ollama install).
- Pull the model you intend to use if needed, for example:

```bash
# example; check Ollama docs for exact model names and availability
ollama pull qwen2.5:7b-instruct
```

## Configuration: `config.yaml`

Create a `config.yaml` file in your project root to customize settings:

```yaml
# Ollama configuration
ollama_url: "http://localhost:11434/api/generate"
model: "qwen2.5:7b-instruct" # Change to your preferred model
timeout: 60 # Request timeout in seconds

# API server configuration
api_host: "0.0.0.0"
api_port: 8000

# Web tools configuration
web_fetch_max_bytes: 200000 # Maximum bytes to fetch per URL
reddit_search_limit: 5 # Number of Reddit posts to return
```

The `llm.py` module will automatically load this file if it exists, otherwise it uses sensible defaults.

## Example: `server.py` (safer)

This example includes basic validation and error handling.

```python
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from llm import ask_qwen
from web_tools import reddit_search, web_fetch
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('genie.log')
    ]
)

app = FastAPI(title="Genie Local API")
logger = logging.getLogger("genie")

class FetchRequest(BaseModel):
    url: HttpUrl

@app.get("/search_reddit")
def search_reddit(query: str = Query(..., min_length=1)):
    try:
        posts = reddit_search(query)
        return {"query": query, "results": posts}
    except Exception as e:
        logger.exception("reddit_search failed")
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/fetch_url")
def fetch_url(req: FetchRequest):
    try:
        content = web_fetch(str(req.url))
        return {"url": str(req.url), "content": content[:4000]}
    except Exception as e:
        logger.exception("fetch_url failed")
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/ask")
def ask(prompt: str = Query(..., min_length=1)):
    try:
        resp = ask_qwen(prompt)
        return {"response": resp}
    except Exception as e:
        logger.exception("ask_qwen failed")
        raise HTTPException(status_code=502, detail=str(e))
```

Notes:

- Use `HttpUrl` (pydantic) to validate fetch URLs. For stricter SSRF protection, validate that the hostname isn't a private IP range.
- Return 502 when upstream calls fail so errors are transparent to the client.

## Example: `llm.py` (more robust)

This example tolerates different Ollama response shapes and surfaces clear errors. It reads configuration from `config.yaml` if available.

```python
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
```

## Example: `web_tools.py` (safer)

**⚠️ Note:** Reddit's public JSON API is deprecated and rate-limited. For production use, consider Reddit's official OAuth API. This example uses the public endpoint with error handling.

```python
import requests
from requests.utils import quote
import logging
from urllib.parse import urlparse

logger = logging.getLogger("genie")

HEADERS = {"User-Agent": "genie-agent/1.0 (+https://example.local)"}

# Simple SSRF protection: block private/local IPs
def is_private_ip(hostname: str) -> bool:
    """Check if hostname resolves to a private IP address."""
    try:
        import socket
        ip = socket.gethostbyname(hostname)
        addr = ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except (socket.gaierror, ValueError):
        return False

def reddit_search(query: str, limit: int = 5) -> list:
    """
    Search Reddit posts.
    Note: Reddit's public JSON API is deprecated and may be rate-limited.
    For production, use Reddit's OAuth API.
    """
    url = f"https://www.reddit.com/search.json?q={quote(query)}&limit={limit}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        posts = []
        for c in data.get("data", {}).get("children", []):
            d = c.get("data", {})
            posts.append({
                "title": d.get("title"),
                "author": d.get("author"),
                "permalink": "https://reddit.com" + d.get("permalink", ""),
                "selftext": d.get("selftext", "")[:500],  # Limit text length
            })
        return posts
    except requests.RequestException as e:
        logger.warning(f"Reddit search failed: {e}")
        return []
    except (KeyError, ValueError) as e:
        logger.warning(f"Failed to parse Reddit response: {e}")
        return []

def web_fetch(url: str, max_bytes: int = 200_000) -> str:
    """
    Fetch content from a URL with size limits and basic SSRF protection.
    """
    parsed = urlparse(url)
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are allowed")

    # Basic SSRF protection
    hostname = parsed.hostname
    if hostname and is_private_ip(hostname):
        raise ValueError(f"Private IP addresses are not allowed: {hostname}")

    try:
        r = requests.get(url, headers=HEADERS, timeout=10, stream=True, allow_redirects=True)
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "").lower()

        # Skip binary content types
        if content_type and not any(ct in content_type for ct in ["text", "json", "xml", "html"]):
            logger.warning(f"Skipping non-text content type: {content_type}")
            return f"[Content type {content_type} not processed]"

        chunks = []
        total = 0
        for chunk in r.iter_content(chunk_size=8192):
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                logger.warning(f"Content truncated at {max_bytes} bytes")
                break
            chunks.append(chunk)

        content = b"".join(chunks).decode(errors="replace")
        return content
    except requests.RequestException as e:
        logger.error(f"web_fetch request failed: {e}")
        raise RuntimeError(f"web_fetch failed: {e}")
    except ValueError as e:
        raise  # Re-raise validation errors
```

## Launcher / `genie` command (recommended approach)

Instead of putting a long startup routine inside `~/.zshrc`, create a small `start_genie.sh` script in your repo and call it from `~/.zshrc` (or create a small executable in `~/bin`). This avoids environment differences when spawning background processes from shell init.

Example `start_genie.sh` (place in your project directory):

```bash
#!/usr/bin/env bash
set -euo pipefail
# Adjust this path to your project location
REPO_DIR="${GENIE_DIR:-/Users/pierrepariente/Desktop/Code/genie}"
cd "$REPO_DIR" || { echo "Error: Cannot cd to $REPO_DIR" >&2; exit 1; }

# Activate venv if exists
if [ -f "$REPO_DIR/venv/bin/activate" ]; then
  # shellcheck disable=SC1090
  source "$REPO_DIR/venv/bin/activate"
fi

# Start FastAPI using the venv uvicorn binary to ensure correct environment
if ! pgrep -f "uvicorn server:app" >/dev/null; then
  echo "Starting Genie API..."
  nohup "$REPO_DIR/venv/bin/uvicorn" server:app --host 0.0.0.0 --port 8000 > "$REPO_DIR/genie.log" 2>&1 &
else
  echo "Genie API already running"
fi

# Start Open WebUI container if not running
if docker ps --format '{{.Names}}' | grep -q '^open-webui$'; then
  echo "Open WebUI already running"
else
  docker start open-webui 2>/dev/null || docker run -d \
    -p 3000:8080 \
    --add-host=host.docker.internal:host-gateway \
    -v ollama:/root/.ollama \
    -v open-webui:/app/backend/data \
    --name open-webui \
    --restart always \
    ghcr.io/open-webui/open-webui:ollama
fi

open "http://localhost:3000"
echo "Genie started. Local API: http://localhost:8000"
```

Then add a tiny shim in your `~/.zshrc`:

```bash
genie() { /Users/pierrepariente/Desktop/Code/genie/start_genie.sh; }
```

Or set `GENIE_DIR` environment variable and use:

```bash
genie() { "${GENIE_DIR:-/Users/pierrepariente/Desktop/Code/genie}"/start_genie.sh; }
```

## Connect Open WebUI → Genie tools

In Open WebUI Settings → Connections → Tools (or Custom API), add tool endpoints such as:

- GET http://host.docker.internal:8000/search_reddit
- POST http://host.docker.internal:8000/fetch_url (JSON body: {"url": "https://..."})

Provide names/descriptions so the model can call them.

## Verification & quick checks

After starting everything, verify:

```bash
# Ollama (or check the Ollama CLI)
curl -sS http://localhost:11434/ || echo "Ollama not responding"

# Genie API
curl -sS "http://localhost:8000/ask?prompt=hello" || echo "Genie API not responding"

# WebUI: open browser to
# http://localhost:3000
```

## Troubleshooting (common)

- Ollama model missing: run `ollama pull <model>` or check `ollama ls`.
- Port conflicts: ensure ports 11434 (Ollama), 8000 (Genie), 3000 (Open WebUI) are free.
- Docker issues: check `docker ps` and container logs (`docker logs open-webui`).
- API errors: check `genie.log` in the project directory and the FastAPI exception logs.
- Reddit search failing: Reddit's public JSON API is deprecated and rate-limited. Consider using Reddit's official OAuth API for production.

## Security & privacy notes

- This setup is intended for local/personal use. If you expose these services beyond localhost, add auth and rate-limiting.
- Be cautious when fetching arbitrary URLs (SSRF risk). Add hostname/IP allowlist if needed.

## Optional: docker-compose sketch

If you want a single `docker compose up` workflow, you can create a `docker-compose.yml` that runs Open WebUI and optionally the Genie API (packaged in a container). I can provide a safe example on request.

## Next steps I can do for you

- Add a `requirements.txt` file and `start_genie.sh` in your repo and wire up the `genie` command.
- Produce a `docker-compose.yml` that runs Open WebUI + Ollama (if supported) + a containerized Genie API.
- Hardening: add SSRF protection, caching, and a small test suite for the API endpoints.

If you'd like I can now apply the small edits into this workspace (`requirements.txt`, `start_genie.sh`, or updated `genie_local_ai_setup.md`) — tell me which and I'll add them and run quick validations.
