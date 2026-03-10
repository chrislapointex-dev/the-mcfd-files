from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
import threading


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: dict = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        with self._lock:
            self._store[key] = [t for t in self._store[key] if t > cutoff]
            if len(self._store[key]) >= self.max_requests:
                return False
            self._store[key].append(now)
            return True


# Public endpoints: 60 req/min/IP
public_limiter = RateLimiter(max_requests=60, window_seconds=60)

# View counter: 5 req/min/IP (prevent inflation)
view_limiter = RateLimiter(max_requests=5, window_seconds=60)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_public(request: Request):
    if not public_limiter.is_allowed(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")


def rate_limit_view(request: Request):
    if not view_limiter.is_allowed(get_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many view events.")
