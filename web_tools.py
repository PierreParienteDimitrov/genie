import requests
from requests.utils import quote
import logging
from urllib.parse import urlparse
from ipaddress import ip_address

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

