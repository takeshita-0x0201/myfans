"""MyFans 月間クリエイターランキング スクレイパー"""
import re
from scrapling import StealthyFetcher
from utils import load_cookies

fetcher = StealthyFetcher()

RANKING_URL = 'https://myfans.jp/ranking/creators/all?term=monthly'


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


def scrape_monthly_creator_ranking() -> dict[str, int]:
    """月間クリエイター総合ランキングを取得

    Returns:
        dict: {username: rank} の辞書
    """
    cookies = load_cookies('myfans')
    ranking = {}

    def action_scrape(page):
        nonlocal ranking
        _click_age_gate(page)

        # トップページからナビ経由で遷移
        # 1. ランキングナビをクリック
        ranking_nav = page.locator('text=ランキング')
        if ranking_nav.count() > 0:
            ranking_nav.first.click()
            page.wait_for_timeout(5000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

        # 2. クリエイタータブをクリック
        creator_link = page.locator('a[href*="/ranking/creators"]')
        if creator_link.count() > 0:
            creator_link.first.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

        # 3. 「月間」ボタンをクリック（aタグではなくbutton/div）
        monthly_btn = page.locator('text=月間')
        if monthly_btn.count() > 0:
            monthly_btn.first.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

        print(f'  Ranking URL: {page.url}')

        # スクロールして全ランキングを読み込み
        for _ in range(10):
            prev_count = page.locator('a').count()
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(2000)
            if page.locator('a').count() == prev_count:
                break

        # 「もっと見る」ボタンがあればクリック
        for _ in range(5):
            more_btn = page.locator('text=もっと見る')
            if more_btn.count() == 0:
                break
            try:
                more_btn.first.click()
                page.wait_for_timeout(3000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)
                for _ in range(5):
                    prev_count = page.locator('a').count()
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    page.wait_for_timeout(2000)
                    if page.locator('a').count() == prev_count:
                        break
            except Exception:
                break

        # ランキングデータを抽出
        links = page.locator('a')
        link_count = links.count()
        seen_usernames = set()
        rank_counter = 0
        exclude_prefixes = ['/posts/', '/ranking/', '/s/', '/feature/', '/genres',
                            '/account', '/feed', '/en/', '/ja/']

        for i in range(link_count):
            try:
                href = links.nth(i).get_attribute('href') or ''
                if (href.startswith('/')
                    and not any(href.startswith(p) for p in exclude_prefixes)
                    and len(href) > 1
                    and '?' not in href):
                    username = href.lstrip('/')
                    if username and username not in seen_usernames and '/' not in username:
                        seen_usernames.add(username)
                        rank_counter += 1
                        ranking[username] = rank_counter
            except Exception:
                pass

        print(f'  Extracted {len(ranking)} creators from monthly ranking')

    # 直接ランキングURLにアクセス（クライアントサイドルーティングなので
    # トップページ経由でナビゲーションする）
    page = fetcher.fetch(
        'https://myfans.jp',
        headless=True,
        timeout=120000,
        page_action=action_scrape,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )

    return ranking


if __name__ == '__main__':
    print('Scraping monthly creator ranking...')
    ranking = scrape_monthly_creator_ranking()
    print(f'\nTotal: {len(ranking)} creators')
    for username, rank in sorted(ranking.items(), key=lambda x: x[1]):
        print(f'  #{rank}: {username}')
