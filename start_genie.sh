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

