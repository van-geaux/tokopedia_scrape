"""Optional authenticated HTTP/HTTPS proxy configuration."""
from __future__ import annotations

import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import OpenerDirector, ProxyHandler, Request, build_opener

DEFAULT_MAX_ATTEMPTS = 6
DEFAULT_RETRY_DELAY = 2.0
MAX_RETRY_DELAY = 30.0
RETRYABLE_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504}


def load_dotenv(path: Path = Path('.env')) -> None:
    """Load simple KEY=VALUE entries without overriding process environment."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


def proxy_url() -> str | None:
    load_dotenv()
    direct_url = os.getenv('PROXY_URL', '').strip()
    if direct_url:
        return direct_url

    host = os.getenv('PROXY_HOST', '').strip()
    port = os.getenv('PROXY_PORT', '').strip()
    if not host and not port:
        return None
    if not host or not port:
        raise ValueError('PROXY_HOST and PROXY_PORT must be configured together')

    scheme = os.getenv('PROXY_SCHEME', 'http').strip() or 'http'
    username = os.getenv('PROXY_USERNAME', '')
    password = os.getenv('PROXY_PASSWORD', '')
    auth = ''
    if username or password:
        if not username or not password:
            raise ValueError('PROXY_USERNAME and PROXY_PASSWORD must be configured together')
        auth = f'{quote(username, safe="")}:{quote(password, safe="")}@'
    return f'{scheme}://{auth}{host}:{port}'


def build_http_opener() -> OpenerDirector:
    configured_proxy = proxy_url()
    if not configured_proxy:
        return build_opener()
    return build_opener(ProxyHandler({
        'http': configured_proxy,
        'https': configured_proxy,
    }))


def open_url(opener: OpenerDirector, request: Request, timeout: int):
    return opener.open(request, timeout=timeout)


def open_url_with_retry(
    request: Request,
    timeout: int,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    retry_delay: float = DEFAULT_RETRY_DELAY,
):
    """Open a URL with exponential backoff, capped at 30 seconds per wait."""
    if max_attempts < 1:
        raise ValueError('max_attempts must be at least 1')
    opener = build_http_opener()
    for attempt in range(1, max_attempts + 1):
        try:
            return opener.open(request, timeout=timeout)
        except HTTPError as exc:
            retryable = exc.code in RETRYABLE_HTTP_STATUS
            if not retryable or attempt == max_attempts:
                raise
        except (URLError, TimeoutError, OSError):
            if attempt == max_attempts:
                raise
        wait_seconds = min(retry_delay * (2 ** (attempt - 1)), MAX_RETRY_DELAY)
        time.sleep(wait_seconds)
    raise RuntimeError('request retry loop ended unexpectedly')
