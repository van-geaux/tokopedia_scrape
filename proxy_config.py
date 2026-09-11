"""Adaptive direct/proxy HTTP transport with retry and backoff."""
from __future__ import annotations

import os
import time
from functools import lru_cache
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import OpenerDirector, ProxyHandler, Request, build_opener

DEFAULT_CONFIG = {
    'proxy': {
        'enabled': False,
        'scheme': 'http',
        'host': '',
        'port': '',
        'cooldown_seconds': 1800,
        'trigger_statuses': [429, 503, 504],
    },
    'retry': {
        'max_attempts': 6,
        'initial_delay_seconds': 2.0,
        'max_delay_seconds': 30.0,
    },
    'request': {
        'timeout_seconds': 60,
        'delay_between_requests_seconds': 0.5,
    },
}


# Minimal YAML support is intentionally avoided, PyYAML handles quoting and lists.
def load_dotenv(path: Path = Path('.env')) -> None:
    """Load KEY=VALUE entries without overriding process environment."""
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


def _merge(base: dict, override: dict) -> dict:
    result = {key: value.copy() if isinstance(value, dict) else value for key, value in base.items()}
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = {**result[key], **value}
        else:
            result[key] = value
    return result


@lru_cache(maxsize=4)
def load_config(path_string: str = 'config.yml') -> dict:
    path = Path(path_string)
    if not path.is_file():
        return _merge(DEFAULT_CONFIG, {})
    try:
        import yaml
        loaded = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except ImportError as exc:
        raise RuntimeError('PyYAML is required when config.yml exists') from exc
    if not isinstance(loaded, dict):
        raise ValueError('config.yml must contain a YAML mapping')
    return _merge(DEFAULT_CONFIG, loaded)


def config_value(section: str, key: str, default=None, config_path: str = 'config.yml'):
    return load_config(config_path).get(section, {}).get(key, default)


def _proxy_url(config: dict) -> str | None:
    load_dotenv()
    settings = config.get('proxy', {})
    if not settings.get('enabled', False):
        return None
    host = str(settings.get('host', '') or '').strip()
    port = str(settings.get('port', '') or '').strip()
    if not host or not port:
        raise ValueError('proxy.enabled is true, but proxy.host or proxy.port is missing')
    scheme = str(settings.get('scheme', 'http') or 'http').strip()
    username = os.getenv('PROXY_USERNAME', '')
    password = os.getenv('PROXY_PASSWORD', '')
    auth = ''
    if username or password:
        if not username or not password:
            raise ValueError('PROXY_USERNAME and PROXY_PASSWORD must be configured together')
        auth = f'{quote(username, safe="")}:{quote(password, safe="")}@'
    return f'{scheme}://{auth}{host}:{port}'


def build_http_opener(use_proxy: bool = False, config_path: str = 'config.yml') -> OpenerDirector:
    configured_proxy = _proxy_url(load_config(config_path)) if use_proxy else None
    if not configured_proxy:
        return build_opener()
    return build_opener(ProxyHandler({'http': configured_proxy, 'https': configured_proxy}))


class AdaptiveTransport:
    def __init__(self):
        self.proxy_until = 0.0
        self.lock = Lock()

    def proxy_active(self, config: dict) -> bool:
        with self.lock:
            return bool(config['proxy'].get('enabled')) and time.monotonic() < self.proxy_until

    def activate_proxy(self, config: dict) -> None:
        if not config['proxy'].get('enabled'):
            return
        cooldown = float(config['proxy'].get('cooldown_seconds', 1800))
        with self.lock:
            self.proxy_until = time.monotonic() + max(0.0, cooldown)

    def open_with_retry(self, request: Request, timeout: int, config_path: str = 'config.yml'):
        config = load_config(config_path)
        retry = config['retry']
        max_attempts = max(1, int(retry.get('max_attempts', 6)))
        initial_delay = max(0.0, float(retry.get('initial_delay_seconds', 2)))
        max_delay = min(30.0, max(0.0, float(retry.get('max_delay_seconds', 30))))
        trigger_statuses = {int(code) for code in config['proxy'].get('trigger_statuses', [429, 503, 504])}

        for attempt in range(1, max_attempts + 1):
            use_proxy = self.proxy_active(config)
            opener = build_http_opener(use_proxy=use_proxy, config_path=config_path)
            try:
                response = opener.open(request, timeout=timeout)
                # A successful direct request after cooldown keeps transport direct.
                return response
            except HTTPError as exc:
                if exc.code in trigger_statuses:
                    self.activate_proxy(config)
                elif exc.code not in {408, 425, 500, 502} or attempt == max_attempts:
                    raise
                if attempt == max_attempts:
                    raise
            except (URLError, TimeoutError, OSError):
                if attempt == max_attempts:
                    raise
            if attempt == max_attempts:
                raise RuntimeError('request retry loop ended unexpectedly')
            wait_seconds = min(initial_delay * (2 ** (attempt - 1)), max_delay)
            time.sleep(wait_seconds)
        raise RuntimeError('request retry loop ended unexpectedly')


_transport = AdaptiveTransport()


def open_url_with_retry(request: Request, timeout: int, config_path: str = 'config.yml'):
    return _transport.open_with_retry(request, timeout, config_path)
