"""MyFans ランキングスクレイパー
日間・週間・月間・年間のクリエイターランキングからユーザーを収集
"""
from scrapling import StealthyFetcher
from utils import load_cookies

fetcher = StealthyFetcher()

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
                page.wait_for_timeout(3000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)
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


def _scrape_ranking(page, term: str, limit: int | None) -> list[dict]:
    """1つのランキング種別からユーザーを収集

    フロー:
    1. /ranking/creators にアクセス（初回のみ）
    2. 「クリエイターランキングをもっと見る」リンクをクリック
       → /ranking/creators/all?term=xxx に遷移
    3. 全件ページでページネーション（「次へ」ボタン）
    """
    all_url = RANKING_URLS[term]
    print(f'\n  [{term}] Navigating to {all_url}...')

    # 全件ページへ直接遷移
    page.evaluate(f"window.location.href = '{all_url}'")
    page.wait_for_timeout(5000)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(3000)

    # 年齢確認（ページ遷移後に再表示される可能性）
    _click_age_gate(page)

    print(f'    URL: {page.url}')

    # ページネーションで全ページ取得
    all_usernames = []
    page_num = 0

    while True:
        page_num += 1

        # スクロールして全件表示
        for _ in range(5):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(1000)

        # ユーザー抽出
        page_users = _extract_usernames(page)
        new_count = 0
        for u in page_users:
            if u not in all_usernames:
                all_usernames.append(u)
                new_count += 1

        print(f'    Page {page_num}: +{new_count} users (total: {len(all_usernames)})')

        # limit に達したら終了
        if limit and len(all_usernames) >= limit:
            all_usernames = all_usernames[:limit]
            print(f'    Reached limit ({limit})')
            break

        # 新規ユーザーが0件ならページが変わっていない
        if new_count == 0 and page_num > 1:
            break

        # 「次へ」ボタンを探す
        next_btn = page.locator('button:has-text("次へ")')
        if next_btn.count() == 0:
            break

        try:
            next_btn.first.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
        except Exception:
            break

    # 順位を振ってエントリを作成
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
    """指定されたランキング種別からユーザーを収集

    Args:
        terms: ランキング種別のリスト (例: ["daily", "monthly"])
        limit: 各ランキングの取得件数上限（Noneなら全件）

    Returns:
        list[dict]: [{"username": "xxx", "rank": 1, "rank_as": "daily"}, ...]
    """
    cookies = load_cookies('myfans')
    all_entries = []

    def action_scrape(page):
        nonlocal all_entries

        # まずトップページで年齢確認を突破
        _click_age_gate(page)

        # まずランキングページに遷移して年齢確認を確実に突破
        page.evaluate("window.location.href = '/ranking/creators'")
        page.wait_for_timeout(5000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)
        _click_age_gate(page)

        print(f'  Base ranking page: {page.url}')

        # 各ランキング種別を順次巡回
        for term in terms:
            if term not in RANKING_URLS:
                print(f'  Unknown term: {term}, skipping')
                continue
            try:
                entries = _scrape_ranking(page, term, limit)
                all_entries.extend(entries)
            except Exception as e:
                print(f'  [{term}] Failed: {e}')
                import traceback
                traceback.print_exc()

    fetcher.fetch(
        'https://myfans.jp',
        headless=True,
        timeout=600000,
        page_action=action_scrape,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )

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
