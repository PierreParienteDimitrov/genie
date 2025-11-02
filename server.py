from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from llm import ask_qwen
from agent import ask_with_tools
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

@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Genie Local API"}

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
def ask(prompt: str = Query(..., min_length=1), use_tools: bool = Query(True, description="Enable automatic tool use")):
    """
    Ask the LLM a question. 
    With use_tools=True (default), the LLM can automatically use Reddit search and web fetch tools.
    With use_tools=False, it just queries the LLM directly without tools.
    """
    try:
        if use_tools:
            resp = ask_with_tools(prompt)
        else:
            resp = ask_qwen(prompt)
        return {"response": resp, "tools_used": use_tools}
    except Exception as e:
        logger.exception("ask failed")
        raise HTTPException(status_code=502, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


