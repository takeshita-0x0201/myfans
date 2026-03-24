"""共通ユーティリティ"""
import json
import re
import os
from datetime import datetime, timedelta

COOKIES_DIR = os.path.join(os.path.dirname(__file__), 'cookies')


def load_cookies(service: str) -> list[dict]:
    """CookieファイルをScrapling/Playwright形式で読み込む"""
    path = os.path.join(COOKIES_DIR, f'{service}.json')
    with open(path, 'r') as f:
        raw = json.load(f)

    cookies = []
    for c in raw:
        cookie = {
            'name': c['name'],
            'value': c['value'],
            'domain': c['domain'],
            'path': c.get('path', '/'),
        }
        if c.get('secure'):
            cookie['secure'] = True
        if c.get('httpOnly'):
            cookie['httpOnly'] = True
        if 'sameSite' in c:
            samesite_map = {
                'no_restriction': 'None',
                'lax': 'Lax',
                'strict': 'Strict',
                'unspecified': 'Lax',
            }
            cookie['sameSite'] = samesite_map.get(c['sameSite'], 'Lax')
        cookies.append(cookie)
    return cookies


def parse_count(text: str) -> int | None:
    """K/M表記の数値をintに変換 (例: '111.9K' -> 111900, '1.2M' -> 1200000)"""
    if not text:
        return None
    text = text.strip().replace(',', '').replace(' ', '')

    # 純粋な数値
    if text.isdigit():
        return int(text)

    # K/M表記
    m = re.match(r'^([\d.]+)\s*([KMkm])$', text)
    if m:
        num = float(m.group(1))
        unit = m.group(2).upper()
        if unit == 'K':
            return int(num * 1000)
        elif unit == 'M':
            return int(num * 1000000)

    # 数値のみ抽出
    m = re.search(r'[\d,.]+', text)
    if m:
        return int(m.group().replace(',', ''))

    return None


def parse_relative_date(text: str, base_date: datetime = None) -> str | None:
    """相対日付を絶対日付に変換 (例: '3日前' -> '2026-03-22')"""
    if not base_date:
        base_date = datetime.now()

    text = text.strip()

    # 「X時間前」
    m = re.search(r'(\d+)\s*時間前', text)
    if m:
        return (base_date - timedelta(hours=int(m.group(1)))).strftime('%Y-%m-%d')

    # 「X日前」
    m = re.search(r'(\d+)\s*日前', text)
    if m:
        return (base_date - timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d')

    # 「Xか月前」「Xヶ月前」
    m = re.search(r'(\d+)\s*[かヶケ]?月前', text)
    if m:
        return (base_date - timedelta(days=int(m.group(1)) * 30)).strftime('%Y-%m-%d')

    # 「X年前」
    m = re.search(r'(\d+)\s*年前', text)
    if m:
        return (base_date - timedelta(days=int(m.group(1)) * 365)).strftime('%Y-%m-%d')

    # 絶対日付 (YYYY/MM/DD or YYYY-MM-DD)
    m = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', text)
    if m:
        return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'

    return None


def is_within_30d(date_str: str, base_date: datetime = None) -> bool:
    """日付が直近30日以内か判定"""
    if not date_str:
        return False
    if not base_date:
        base_date = datetime.now()
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        return (base_date - d).days <= 30
    except ValueError:
        return False
