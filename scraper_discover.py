"""MyFans ランキングスクレイパー
日間・週間・月間・年間のクリエイターランキングからユーザーを収集
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from scrapling import StealthyFetcher
from utils import load_cookies

# ランキング種別 → 全件ページURL
RANKING_URLS = {
    'daily': '/ranking/creators/all?term=daily',
    'weekly': '/ranking/creators/all?term=weekly',
    'monthly': '/ranking/creators/all?term=monthly',
    'yearly': '/ranking/creators/all?term=yearly',
}

# ユーザープロフィールリンクでないパスの一覧
EXCLUDE_PREFIXES = [
    '/posts/', '/ranking/', '/s/', '/feature/', '/genres',
    '/account', '/feed', '/en/', '/ja/', '/search',
]


def _click_age_gate(page):
    """年齢確認ダイアログを突破"""
    try:
        buttons = page.locator('button')
        for i in range(buttons.count()):
            if 'はい' in buttons.nth(i).inner_text():
                buttons.nth(i).click()
                page.wait_for_timeout(2000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(1000)
                return
    except Exception:
        pass


def _extract_usernames(page) -> list[str]:
    """ページ内の全ユーザープロフィールリンクからユーザー名を抽出（出現順）"""
    usernames = []
    links = page.locator('a')
    for i in range(links.count()):
        try:
            href = links.nth(i).get_attribute('href') or ''
            if (href.startswith('/')
                    and not any(href.startswith(p) for p in EXCLUDE_PREFIXES)
                    and len(href) > 1
                    and '?' not in href
                    and '#' not in href
                    and '/' not in href.lstrip('/')):
                username = href.lstrip('/')
                if username and username not in usernames:
                    usernames.append(username)
        except Exception:
            pass
    return usernames


def _scrape_single_term(term: str, limit: int | None) -> list[dict]:
    """1つのランキング種別を1ブラウザで全ページ取得（スレッドで実行される）"""
    fetcher = StealthyFetcher()
    cookies = load_cookies('myfans')
    base_url = RANKING_URLS[term]
    all_usernames = []

    def action(page):
        nonlocal all_usernames
        page_num = 0

        while True:
            page_num += 1
            url = f'{base_url}&page={page_num}'
            print(f'  [{term}] Page {page_num}')

            page.evaluate(f"window.location.href = '{url}'")
            page.wait_for_timeout(2000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(1000)

            if page_num == 1:
                _click_age_gate(page)

            for _ in range(3):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(500)

            page_users = _extract_usernames(page)
            new_count = 0
            for u in page_users:
                if u not in all_usernames:
                    all_usernames.append(u)
                    new_count += 1

            print(f'    [{term}] +{new_count} users (total: {len(all_usernames)})')

            if new_count == 0:
                break

            if limit and len(all_usernames) >= limit:
                all_usernames = all_usernames[:limit]
                print(f'    [{term}] Reached limit ({limit})')
                break

    fetcher.fetch(
        'https://myfans.jp',
        headless=True,
        timeout=600000,
        page_action=action,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )

    entries = []
    for idx, username in enumerate(all_usernames):
        entries.append({
            'username': username,
            'rank': idx + 1,
            'rank_as': term,
        })

    print(f'  [{term}] Done: {len(entries)} users')
    return entries


def discover_from_rankings(terms: list[str], limit: int | None = None) -> list[dict]:
    """指定されたランキング種別からユーザーを並列収集

    各termは別ブラウザで並列実行される。
    """
    valid_terms = [t for t in terms if t in RANKING_URLS]
    if not valid_terms:
        return []

    print(f'  Launching {len(valid_terms)} browser(s) in parallel...')

    all_entries = []

    if len(valid_terms) == 1:
        # 1種別のみなら直列
        all_entries = _scrape_single_term(valid_terms[0], limit)
    else:
        # 複数種別は並列
        with ThreadPoolExecutor(max_workers=len(valid_terms)) as executor:
            futures = {
                executor.submit(_scrape_single_term, term, limit): term
                for term in valid_terms
            }
            for future in as_completed(futures):
                term = futures[future]
                try:
                    entries = future.result()
                    all_entries.extend(entries)
                except Exception as e:
                    print(f'  [{term}] Failed: {e}')

    print(f'\n  === Discovery complete: {len(all_entries)} entries ===')
    return all_entries


if __name__ == '__main__':
    import sys
    terms = [a for a in sys.argv[1:] if a in RANKING_URLS]
    numbers = [a for a in sys.argv[1:] if a.isdigit()]
    limit = int(numbers[0]) if numbers else None

    if not terms:
        print('Usage: python scraper_discover.py <daily|weekly|monthly|yearly> [件数]')
        sys.exit(1)

    entries = discover_from_rankings(terms, limit)
    print(f'\nTotal: {len(entries)} entries')
    for e in entries[:20]:
        print(f'  #{e["rank"]} [{e["rank_as"]}] {e["username"]}')
    if len(entries) > 20:
        print(f'  ... and {len(entries) - 20} more')
