"""MyFans 月間クリエイターランキング スクレイパー"""
import re
import time
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


def scrape_monthly_creator_ranking() -> dict[str, int]:
    """月間クリエイター総合ランキングを取得

    Returns:
        dict: {username: rank} の辞書
    """
    cookies = load_cookies('myfans')
    ranking = {}

    def action_navigate_and_scrape(page):
        nonlocal ranking
        _click_age_gate(page)

        # 下部ナビの「ランキング」をクリック
        ranking_nav = page.locator('text=ランキング')
        if ranking_nav.count() > 0:
            ranking_nav.first.click()
            page.wait_for_timeout(5000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

        print(f'  URL after nav click: {page.url}')

        # 「クリエイター」タブに切り替え（投稿ランキングではなく）
        # ランキングページには投稿ランキングとクリエイターランキングがある
        # クリエイターランキングのリンクをクリック
        creator_link = page.locator('a[href*="/ranking/creators"]')
        if creator_link.count() > 0:
            creator_link.first.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

        print(f'  URL after creator tab: {page.url}')

        # 「月間」に切り替え
        # term パラメータ: daily, weekly, monthly
        monthly_link = page.locator('a[href*="term=monthly"]')
        if monthly_link.count() > 0:
            monthly_link.first.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
        else:
            # ボタンやタブとして存在する場合
            tabs = page.locator('button, [role="tab"], div[class*="cursor"]')
            for i in range(tabs.count()):
                try:
                    text = tabs.nth(i).inner_text().strip()
                    if '月間' in text or 'Monthly' in text:
                        tabs.nth(i).click()
                        page.wait_for_timeout(3000)
                        page.wait_for_load_state('networkidle')
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    pass

        print(f'  URL final: {page.url}')

        # スクロールして全ランキングを読み込み
        for _ in range(10):
            prev_count = page.locator('a').count()
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(2000)
            if page.locator('a').count() == prev_count:
                break

        # 「もっと見る」ボタンがあればクリック
        more_btn = page.locator('text=もっと見る')
        while more_btn.count() > 0:
            try:
                more_btn.first.click()
                page.wait_for_timeout(3000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)
                # さらにスクロール
                for _ in range(5):
                    prev_count = page.locator('a').count()
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    page.wait_for_timeout(2000)
                    if page.locator('a').count() == prev_count:
                        break
                more_btn = page.locator('text=もっと見る')
            except Exception:
                break

        # ランキングデータを抽出
        # ユーザーリンク (/{username}) を順番に取得
        links = page.locator('a')
        link_count = links.count()
        seen_usernames = set()
        rank_counter = 0

        for i in range(link_count):
            try:
                href = links.nth(i).get_attribute('href') or ''
                # ユーザーページリンクの判定: /username 形式で
                # /posts/, /ranking/, /s/, /feature/, /genres, /account, /feed は除外
                if (href.startswith('/')
                    and not any(href.startswith(p) for p in ['/posts/', '/ranking/', '/s/', '/feature/', '/genres', '/account', '/feed', '/en/'])
                    and len(href) > 1
                    and '?' not in href):
                    username = href.lstrip('/')
                    if username and username not in seen_usernames and not username.startswith('http'):
                        seen_usernames.add(username)
                        rank_counter += 1
                        ranking[username] = rank_counter
            except Exception:
                pass

        print(f'  Extracted {len(ranking)} creators from ranking')

    page = fetcher.fetch(
        'https://myfans.jp',
        headless=True,
        timeout=120000,
        page_action=action_navigate_and_scrape,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )

    return ranking


if __name__ == '__main__':
    print('Scraping monthly creator ranking...')
    ranking = scrape_monthly_creator_ranking()
    print(f'\nTotal: {len(ranking)} creators')
    for username, rank in sorted(ranking.items(), key=lambda x: x[1])[:30]:
        print(f'  #{rank}: {username}')
