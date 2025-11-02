# 🧞 Genie — Local AI Assistant

A local AI assistant setup combining Ollama (Qwen), Open WebUI, and a FastAPI server with web tools (Reddit search, URL fetching).

## Quick Start

### 1. Install Prerequisites

- **Docker** and Docker Desktop (must be running)
- **Ollama** - [Download](https://ollama.ai)
- **Python 3.10+**

### 2. Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Pull Ollama Model

```bash
ollama pull qwen2.5:7b-instruct
# Or any other model you prefer
```

### 4. Configure (Optional)

Edit `config.yaml` to customize:
- Model name
- Ollama URL
- Timeouts
- Other settings

### 5. Start Genie

```bash
./start_genie.sh
```

Or manually:

```bash
# Start the API server
uvicorn server:app --host 0.0.0.0 --port 8000

# In another terminal, start Open WebUI (if not using Docker)
# Or use the start_genie.sh script which handles both
```

## API Endpoints

- `GET /` - Health check
- `GET /ask?prompt=<your_prompt>` - Ask the LLM a question
- `GET /search_reddit?query=<search_term>` - Search Reddit
- `POST /fetch_url` - Fetch content from a URL (JSON: `{"url": "https://..."}`)

## Verification

```bash
# Check Ollama
curl http://localhost:11434/

# Check Genie API
curl "http://localhost:8000/ask?prompt=hello"

# Open WebUI
open http://localhost:3000
```

## Project Structure

```
genie/
 ├── server.py          # FastAPI application
 ├── llm.py             # Ollama/Qwen client
 ├── web_tools.py       # Reddit + web fetch tools
 ├── config.yaml        # Configuration file
 ├── requirements.txt   # Python dependencies
 ├── start_genie.sh     # Launcher script
 └── genie.log          # Application logs (created at runtime)
```

## Troubleshooting

- **Ollama not responding**: Ensure Ollama daemon is running (`ollama serve` or check Docker)
- **Port conflicts**: Ensure ports 11434 (Ollama), 8000 (Genie API), 3000 (Open WebUI) are free
- **Import errors**: Make sure virtual environment is activated and dependencies are installed
- **Model not found**: Run `ollama pull <model_name>` to download the model

## Security Notes

⚠️ This setup is for **local/personal use only**. If exposing beyond localhost:
- Add authentication
- Add rate limiting
- Review SSRF protections in `web_tools.py`

## Documentation

See `genie_local_ai_setup.cleaned.md` for detailed documentation.

