"""MyFans ユーザー自動発見スクレイパー
ランキング・ジャンル・ピックアップ・フィードからユーザー名を自動収集
"""
from scrapling import StealthyFetcher
from utils import load_cookies

fetcher = StealthyFetcher()

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
    """ページ内の全ユーザープロフィールリンクからユーザー名を抽出"""
    usernames = []
    links = page.locator('a')
    for i in range(links.count()):
        try:
            href = links.nth(i).get_attribute('href') or ''
            if (href.startswith('/')
                    and not any(href.startswith(p) for p in EXCLUDE_PREFIXES)
                    and len(href) > 1
                    and '?' not in href
                    and '/' not in href.lstrip('/')):
                username = href.lstrip('/')
                if username and username not in usernames:
                    usernames.append(username)
        except Exception:
            pass
    return usernames


def _paginate_and_collect(page, found: set, max_pages: int = 100):
    """現在のページからユーザーを抽出し、ページネーションで全ページを巡回"""
    for page_num in range(1, max_pages + 1):
        # スクロールして全件表示
        for _ in range(5):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(1000)

        # ユーザー抽出
        users = _extract_usernames(page)
        new_count = 0
        for u in users:
            if u not in found:
                found.add(u)
                new_count += 1

        if page_num == 1 or new_count > 0:
            print(f'    Page {page_num}: +{new_count} users (total: {len(found)})')

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


def _discover_from_ranking(page, found: set):
    """ランキングからユーザーを収集"""
    print('\n  [1/4] Ranking...')
    try:
        page.evaluate("window.location.href = '/ranking/creators/all?term=monthly'")
        page.wait_for_timeout(5000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)
        _click_age_gate(page)

        before = len(found)
        _paginate_and_collect(page, found)
        print(f'  [1/4] Ranking done: +{len(found) - before} users')
    except Exception as e:
        print(f'  [1/4] Ranking failed: {e}')


def _discover_from_genres(page, found: set):
    """ジャンル検索からユーザーを収集（全ジャンル巡回）"""
    print('\n  [2/4] Genres...')
    try:
        page.evaluate("window.location.href = '/genres'")
        page.wait_for_timeout(5000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)
        _click_age_gate(page)

        # ジャンルリンクを収集
        genre_links = []
        links = page.locator('a')
        for i in range(links.count()):
            try:
                href = links.nth(i).get_attribute('href') or ''
                if href.startswith('/genres/') and href not in genre_links:
                    genre_links.append(href)
            except Exception:
                pass

        print(f'    Found {len(genre_links)} genres')

        # 各ジャンルページを巡回
        for idx, genre_href in enumerate(genre_links):
            genre_name = genre_href.split('/')[-1]
            print(f'    Genre [{idx+1}/{len(genre_links)}]: {genre_name}')
            try:
                page.evaluate(f"window.location.href = '{genre_href}'")
                page.wait_for_timeout(3000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)

                before = len(found)
                _paginate_and_collect(page, found)
                print(f'      +{len(found) - before} users')
            except Exception as e:
                print(f'      Failed: {e}')

        print(f'  [2/4] Genres done: total {len(found)} users')
    except Exception as e:
        print(f'  [2/4] Genres failed: {e}')


def _discover_from_feature(page, found: set):
    """ピックアップ/特集からユーザーを収集"""
    print('\n  [3/4] Features...')
    try:
        page.evaluate("window.location.href = '/feature/'")
        page.wait_for_timeout(5000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)
        _click_age_gate(page)

        # 特集ページリンクを収集
        feature_links = []
        links = page.locator('a')
        for i in range(links.count()):
            try:
                href = links.nth(i).get_attribute('href') or ''
                if (href.startswith('/feature/')
                        and href != '/feature/'
                        and href not in feature_links):
                    feature_links.append(href)
            except Exception:
                pass

        print(f'    Found {len(feature_links)} feature pages')

        # 各特集ページを巡回
        for idx, feat_href in enumerate(feature_links):
            feat_name = feat_href.split('/')[-1]
            print(f'    Feature [{idx+1}/{len(feature_links)}]: {feat_name}')
            try:
                page.evaluate(f"window.location.href = '{feat_href}'")
                page.wait_for_timeout(3000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)

                # スクロールしてユーザーリンクを収集
                for _ in range(5):
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    page.wait_for_timeout(1000)

                before = len(found)
                users = _extract_usernames(page)
                for u in users:
                    found.add(u)
                print(f'      +{len(found) - before} users')
            except Exception as e:
                print(f'      Failed: {e}')

        print(f'  [3/4] Features done: total {len(found)} users')
    except Exception as e:
        print(f'  [3/4] Features failed: {e}')


def _discover_from_feed(page, found: set):
    """フィードからユーザーを収集（無限スクロール対応）"""
    print('\n  [4/4] Feed...')
    try:
        page.evaluate("window.location.href = '/feed'")
        page.wait_for_timeout(5000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)
        _click_age_gate(page)

        no_new_count = 0
        scroll_round = 0
        while no_new_count < 5:
            scroll_round += 1
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(2000)

            before = len(found)
            users = _extract_usernames(page)
            for u in users:
                found.add(u)

            new_count = len(found) - before
            if new_count == 0:
                no_new_count += 1
            else:
                no_new_count = 0

            if scroll_round % 5 == 0:
                print(f'    Scroll {scroll_round}: total {len(found)} users')

        print(f'  [4/4] Feed done: total {len(found)} users')
    except Exception as e:
        print(f'  [4/4] Feed failed: {e}')


def discover_usernames() -> list[str]:
    """MyFansサイトの複数ソースからユーザー名を自動収集

    Returns:
        list[str]: 発見されたユーザー名のソート済みリスト
    """
    cookies = load_cookies('myfans')
    found = set()

    def action_discover(page):
        _click_age_gate(page)
        _discover_from_ranking(page, found)
        _discover_from_genres(page, found)
        _discover_from_feature(page, found)
        _discover_from_feed(page, found)

    fetcher.fetch(
        'https://myfans.jp',
        headless=True,
        timeout=600000,
        page_action=action_discover,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )

    print(f'\n  === Discovery complete: {len(found)} unique users ===')
    return sorted(list(found))


if __name__ == '__main__':
    print('Discovering users from MyFans...')
    usernames = discover_usernames()
    print(f'\nTotal: {len(usernames)} users')
    for u in usernames[:20]:
        print(f'  {u}')
    if len(usernames) > 20:
        print(f'  ... and {len(usernames) - 20} more')
