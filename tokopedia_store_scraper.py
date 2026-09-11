#!/usr/bin/env python3
"""Scrape product cards from a public Tokopedia shop product page."""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request

from proxy_config import config_value, open_url_with_retry

# Customize these values for another Tokopedia store or run configuration.
STORE_URL = 'https://www.tokopedia.com/enchenmenscare/product'
PAGES = 1
OUTPUT_JSON = Path('products.json')
DELAY = float(config_value('request', 'delay_between_requests_seconds', 0.5))

CARD_RE = re.compile(r'<a\b(?=[^>]*\bclass="[^"]*Ui5-[^"]*")(?=[^>]*\bhref="([^"]+)")[^>]*>(.*?)</a>', re.I | re.S)
NAME_RE = re.compile(r'<span\b[^>]*\bclass="[^"]*\+tnoq[^\"]*"[^>]*>(.*?)</span>', re.I | re.S)
PRICE_RE = re.compile(r'<div\b[^>]*\bclass="[^"]*urMO[^\"]*"[^>]*>(.*?)</div>', re.I | re.S)
RATING_RE = re.compile(r'<span\b[^>]*\bclass="[^"]*_2NfJ[^\"]*"[^>]*>(.*?)</span>', re.I | re.S)
SOLD_RE = re.compile(r'<span\b[^>]*\bclass="[^"]*u6Sfj[^\"]*"[^>]*>(.*?)</span>', re.I | re.S)
TAG_RE = re.compile(r'<[^>]+>')
SPACE_RE = re.compile(r'\s+')


def clean(value: str) -> str:
    return SPACE_RE.sub(' ', html.unescape(TAG_RE.sub(' ', value))).strip()


def parse_price(value: str) -> int | None:
    digits = re.sub(r'[^0-9]', '', clean(value))
    return int(digits) if digits else None


def parse_sold(value: str) -> int | None:
    text = clean(value).lower().replace(',', '.').strip()
    match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(rb|jt|k|m)?', text)
    if not match:
        return None
    number = float(match.group(1))
    multiplier = {'k': 1_000, 'rb': 1_000, 'jt': 1_000_000, 'm': 1_000_000}.get(match.group(2), 1)
    return int(number * multiplier)


def parse_rating(value: str) -> float | None:
    match = re.search(r'\d+(?:[\.,]\d+)?', clean(value))
    return float(match.group().replace(',', '.')) if match else None


def shop_base(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or parsed.netloc not in {'www.tokopedia.com', 'tokopedia.com'}:
        raise ValueError('url must be a Tokopedia shop product URL')
    parts = [part for part in parsed.path.split('/') if part]
    if len(parts) < 2 or parts[1] != 'product':
        raise ValueError('url must look like https://www.tokopedia.com/<shop>/product')
    return f'https://www.tokopedia.com/{parts[0]}/product'


def fetch(url: str, timeout: int | None = None) -> str:
    if timeout is None:
        timeout = int(config_value('request', 'timeout_seconds', 60))
    request = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36',
        'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
    })
    with open_url_with_retry(request, timeout=timeout) as response:
        return response.read().decode('utf-8', 'replace')


def parse_cache_page(source: str) -> list[dict]:
    """Extract the full page-size result from Tokopedia's SSR Apollo cache."""
    marker = 'window.__cache='
    if marker not in source:
        return []
    try:
        start = source.index(marker) + len(marker)
        cache, _ = json.JSONDecoder().raw_decode(source[start:])
        root = cache.get('ROOT_QUERY', {})
        query_key = next((key for key in root if key.startswith('GetShopProduct(')), None)
        if not query_key:
            return []
        query_ref = root[query_key]
        query = cache.get(query_ref.get('id', ''), query_ref)
        products = []
        for product_ref in query.get('data', []):
            product = cache.get(product_ref.get('id', ''), product_ref)
            price_ref = product.get('price', {})
            price = cache.get(price_ref.get('id', ''), price_ref)
            stats_ref = product.get('stats', {})
            stats = cache.get(stats_ref.get('id', ''), stats_ref)
            sold = None
            for label_ref in product.get('label_groups', []):
                label = cache.get(label_ref.get('id', ''), label_ref)
                if label.get('position') == 'ri_product_credibility':
                    sold = parse_sold(label.get('title', ''))
                    break
            products.append({
                'name': product.get('name', ''),
                'link': product.get('product_url', ''),
                'price': parse_price(price.get('text_idr', '')),
                'sold': sold,
                'star': parse_rating(stats.get('averageRating', '')),
            })
        return [product for product in products if product['name'] and product['link']]
    except (ValueError, json.JSONDecodeError, StopIteration, AttributeError, TypeError):
        return []


def parse_page(source: str) -> list[dict]:
    cached_products = parse_cache_page(source)
    if cached_products:
        return cached_products
    products = []
    for match in CARD_RE.finditer(source):
        link = html.unescape(match.group(1))
        body = match.group(2)
        name_match = NAME_RE.search(body)
        if not name_match:
            continue
        price_match = PRICE_RE.search(body)
        rating_match = RATING_RE.search(body)
        sold_match = SOLD_RE.search(body)
        products.append({
            'name': clean(name_match.group(1)),
            'link': link,
            'price': parse_price(price_match.group(1)) if price_match else None,
            'sold': parse_sold(sold_match.group(1)) if sold_match else None,
            'star': parse_rating(rating_match.group(1)) if rating_match else None,
        })
    return products


def scrape(shop_url: str, pages: int = 1, delay: float = DELAY) -> list[dict]:
    base = shop_base(shop_url)
    results, seen = [], set()
    for page in range(1, pages + 1):
        url = base if page == 1 else f'{base}/page/{page}'
        for item in parse_page(fetch(url)):
            if item['link'] not in seen:
                seen.add(item['link'])
                results.append(item)
        if page < pages:
            time.sleep(delay)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs='?', default=STORE_URL, help='Tokopedia shop product URL')
    parser.add_argument('--pages', type=int, default=PAGES, help='number of pages to combine into one JSON file')
    parser.add_argument('--output', type=Path, default=OUTPUT_JSON, help='single JSON output file')
    parser.add_argument('--csv', type=Path, help='optional CSV output file')
    args = parser.parse_args()
    if args.pages < 1:
        parser.error('--pages must be at least 1')
    try:
        products = scrape(args.url, args.pages)
    except Exception as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    # `products` already contains the deduplicated results from every page.
    # Write that complete collection once, after pagination finishes.
    args.output.write_text(json.dumps(products, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.csv:
        with args.csv.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=['name', 'link', 'price', 'sold', 'star'])
            writer.writeheader()
            writer.writerows(products)
    print(f'Fetched {len(products)} products into {args.output}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
