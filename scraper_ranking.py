"""MyFans 月間クリエイターランキング スクレイパー"""
import re
from scrapling import StealthyFetcher
from utils import load_cookies

fetcher = StealthyFetcher()


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


def _extract_ranking_from_page(page) -> list[tuple[int, str]]:
    """現在表示中のランキングページからユーザーリンクを順位付きで抽出"""
    exclude_prefixes = ['/posts/', '/ranking/', '/s/', '/feature/', '/genres',
                        '/account', '/feed', '/en/', '/ja/']
    results = []
    links = page.locator('a')
    for i in range(links.count()):
        try:
            href = links.nth(i).get_attribute('href') or ''
            if (href.startswith('/')
                and not any(href.startswith(p) for p in exclude_prefixes)
                and len(href) > 1
                and '?' not in href
                and '/' not in href.lstrip('/')):
                username = href.lstrip('/')
                if username and username not in [u for _, u in results]:
                    results.append((0, username))  # rank は後で振り直す
        except Exception:
            pass
    return results


def scrape_monthly_creator_ranking() -> dict[str, int]:
    """月間クリエイター総合ランキングを取得（ページネーション対応）

    Returns:
        dict: {username: rank} の辞書
    """
    cookies = load_cookies('myfans')
    all_usernames = []  # 順番通りのリスト

    def action_scrape(page):
        nonlocal all_usernames
        _click_age_gate(page)

        # 1. ランキングページまで遷移
        ranking_nav = page.locator('text=ランキング')
        if ranking_nav.count() > 0:
            ranking_nav.first.click()
            page.wait_for_timeout(5000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

        creator_link = page.locator('a[href*="/ranking/creators"]')
        if creator_link.count() > 0:
            creator_link.first.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

        monthly_btn = page.locator('text=月間')
        if monthly_btn.count() > 0:
            monthly_btn.first.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

        # 2. 総合クリエイターランキング全件ページへ
        page.evaluate("window.location.href = '/ranking/creators/all?term=monthly'")
        page.wait_for_timeout(5000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)

        print(f'  Ranking URL: {page.url}')

        # 3. ページネーションで全ページ取得
        page_num = 1
        while True:
            # スクロールして全件表示
            for _ in range(5):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(1000)

            # 現在のページからユーザーを抽出
            page_users = _extract_ranking_from_page(page)
            new_count = 0
            for _, username in page_users:
                if username not in all_usernames:
                    all_usernames.append(username)
                    new_count += 1

            print(f'  Page {page_num}: +{new_count} users (total: {len(all_usernames)})')

            # 「次へ」ボタンを探してクリック
            next_btn = page.locator('button:has-text("次へ")')
            if next_btn.count() == 0:
                break

            try:
                next_btn.first.click()
                page.wait_for_timeout(3000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)
                page_num += 1
            except Exception:
                break

            # 安全弁
            if page_num > 20:
                break

    page = fetcher.fetch(
        'https://myfans.jp',
        headless=True,
        timeout=180000,
        page_action=action_scrape,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )

    # 順位を振る（リストの順番 = ランキング順位）
    ranking = {username: idx + 1 for idx, username in enumerate(all_usernames)}
    print(f'  Total: {len(ranking)} creators in monthly ranking')

    return ranking


if __name__ == '__main__':
    print('Scraping monthly creator ranking...')
    ranking = scrape_monthly_creator_ranking()
    print(f'\nTotal: {len(ranking)} creators')
    for username, rank in sorted(ranking.items(), key=lambda x: x[1]):
        print(f'  #{rank}: {username}')
