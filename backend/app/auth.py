"""Single API key auth dependency. Import and use as Depends(require_api_key).

If MCFD_API_KEY env var is not set or empty: auth is disabled (dev mode).
If set: all requests must include X-API-Key header matching the env var.
"""
import os
from fastapi import Header, HTTPException

API_KEY = os.getenv("MCFD_API_KEY", "")


def require_api_key(x_api_key: str = Header(default="")):
    if not API_KEY:
        return  # Dev mode — no key configured, allow all
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
