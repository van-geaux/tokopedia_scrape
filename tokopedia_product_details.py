#!/usr/bin/env python3
"""Scrape detailed product data from Tokopedia product URLs."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request

from proxy_config import build_http_opener

# Customize these variables, or override them with command-line arguments.
INPUT_JSON = Path('products.json')
OUTPUT_JSON = Path('product-details.json')
DELAY = 0.5


def fetch(url: str, timeout: int = 60) -> str:
    request = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36',
        'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
    })
    with build_http_opener().open(request, timeout=timeout) as response:
        return response.read().decode('utf-8', 'replace')


def resolve(cache: dict, value):
    if isinstance(value, dict):
        return cache.get(value.get('id', ''), value)
    return value


def parse_cache(source: str) -> dict:
    marker = 'window.__cache='
    if marker not in source:
        raise ValueError('Tokopedia product cache was not found')
    start = source.index(marker) + len(marker)
    cache, _ = json.JSONDecoder().raw_decode(source[start:])
    root = cache.get('ROOT_QUERY', {})
    main_key = next((key for key in root if key.startswith('pdpMainInfo(')), None)
    if not main_key:
        raise ValueError('Tokopedia product detail payload was not found')
    main_ref = root[main_key]
    return cache, resolve(cache, main_ref)


def parse_number(value):
    if value in (None, ''):
        return None
    match = re.search(r'[-+]?\d+(?:[.,]\d+)?', str(value))
    if not match:
        return None
    return float(match.group().replace(',', '.'))


def parse_int(value):
    number = parse_number(value)
    return int(number) if number is not None else None


def component(main: dict, cache: dict, name: str) -> dict | None:
    for ref in main.get('components', []):
        item = resolve(cache, ref)
        if item.get('name') == name:
            data = item.get('data', [])
            return resolve(cache, data[0]) if data else None
    return None


def parse_product(source: str, url: str) -> dict:
    cache, main = parse_cache(source)
    main_data = resolve(cache, main.get('data', {}))
    basic = resolve(cache, main_data.get('basicInfo', {}))
    content = component(main, cache, 'product_content') or {}
    detail = component(main, cache, 'product_detail') or {}

    price = resolve(cache, content.get('price', {}))
    campaign = resolve(cache, content.get('campaign', {}))
    stock = resolve(cache, content.get('stock', {}))
    tx_stats = resolve(cache, basic.get('txStats', {}))
    stats = resolve(cache, basic.get('stats', {}))

    details = []
    for item_ref in detail.get('content', []):
        item = resolve(cache, item_ref)
        if item.get('title'):
            details.append({
                'title': item.get('title'),
                'value': item.get('subtitle', ''),
            })

    rating_root = next(
        (value for key, value in cache.get('ROOT_QUERY', {}).items()
         if key.startswith('productrevGetProductRatingAndTopics(')),
        None,
    )
    rating_data = resolve(cache, rating_root or {})
    rating = resolve(cache, rating_data.get('rating', {}))
    review_by_star = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0}
    for rating_ref in rating.get('detail', []):
        rating_item = resolve(cache, rating_ref)
        star = str(rating_item.get('rate', ''))
        if star in review_by_star:
            review_by_star[star] = parse_int(rating_item.get('totalReviews')) or 0

    current_price = parse_int(price.get('value'))
    campaign_price = parse_int(campaign.get('discountedPrice'))
    discounted_price = campaign_price if campaign.get('isActive') else None
    if discounted_price is None and price.get('slashPriceFmt') and current_price is not None:
        discounted_price = current_price

    return {
        'name': content.get('name') or basic.get('url', '').rsplit('/', 1)[-1],
        'link': url,
        'sold': parse_int(tx_stats.get('countSold')),
        'star': parse_number(stats.get('rating')),
        'price': current_price,
        'discounted_price': discounted_price,
        'product_detail_items': details,
        'available_stock': parse_int(stock.get('value')),
        'total_review_by_star': review_by_star,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=INPUT_JSON)
    parser.add_argument('--output', type=Path, default=OUTPUT_JSON)
    parser.add_argument('--delay', type=float, default=DELAY)
    args = parser.parse_args()
    products = json.loads(args.input.read_text(encoding='utf-8'))
    results = []
    failures = []
    for index, product in enumerate(products, start=1):
        url = product['link']
        try:
            result = parse_product(fetch(url), url)
            results.append(result)
            print(f'[{index}/{len(products)}] OK', file=sys.stderr)
        except Exception as exc:
            failures.append({'link': url, 'error': str(exc)})
            print(f'[{index}/{len(products)}] ERROR {exc}', file=sys.stderr)
        if index < len(products):
            time.sleep(args.delay)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {len(results)} products to {args.output}', file=sys.stderr)
    if failures:
        print(f'Failures: {len(failures)}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
