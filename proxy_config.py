"""Optional authenticated HTTP/HTTPS proxy configuration."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import OpenerDirector, ProxyHandler, Request, build_opener


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
