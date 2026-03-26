"""ランキングページのデバッグ用スクリプト
クリエイタータブクリック後のページ構造を確認する
"""
from scrapling import StealthyFetcher
from utils import load_cookies

fetcher = StealthyFetcher()


def debug_ranking():
    cookies = load_cookies('myfans')

    def action(page):
        # 1. 年齢確認突破
        print('=== Step 1: Age gate ===')
        try:
            buttons = page.locator('button')
            for i in range(buttons.count()):
                text = buttons.nth(i).inner_text()
                if 'はい' in text:
                    print(f'  Clicking: {text}')
                    buttons.nth(i).click()
                    page.wait_for_timeout(3000)
                    page.wait_for_load_state('networkidle')
                    page.wait_for_timeout(2000)
                    break
        except Exception as e:
            print(f'  Error: {e}')

        # 2. ランキングナビ
        print('\n=== Step 2: Ranking nav ===')
        ranking_nav = page.locator('text=ランキング')
        if ranking_nav.count() > 0:
            ranking_nav.first.click()
            page.wait_for_timeout(5000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
        print(f'  URL: {page.url}')

        # 3. クリエイターリンク
        print('\n=== Step 3: Creator link ===')
        creator_link = page.locator('a[href*="/ranking/creators"]')
        print(f'  Creator links: {creator_link.count()}')
        if creator_link.count() > 0:
            creator_link.first.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
        print(f'  URL: {page.url}')

        # 4. クリエイターボタンをクリック
        print('\n=== Step 4: Creator tab button ===')
        creator_btn = page.locator('button:has-text("クリエイター")')
        print(f'  "クリエイター" buttons: {creator_btn.count()}')
        if creator_btn.count() > 0:
            creator_btn.first.click()
            page.wait_for_timeout(5000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(3000)
        print(f'  URL: {page.url}')

        # 5. クリエイターランキングのページ分析
        print('\n=== Step 5: Creator ranking page analysis ===')

        # リンク一覧
        links = page.locator('a')
        link_count = links.count()
        print(f'  Total links: {link_count}')
        print('  --- User links (not /posts/) ---')
        user_links = []
        for i in range(link_count):
            try:
                href = links.nth(i).get_attribute('href') or ''
                if (href.startswith('/')
                        and not href.startswith('/posts/')
                        and not href.startswith('/ranking/')
                        and not href.startswith('/s/')
                        and not href.startswith('/feature/')
                        and not href.startswith('/genres')
                        and not href.startswith('/account')
                        and not href.startswith('/feed')
                        and not href.startswith('/en/')
                        and not href.startswith('/ja/')
                        and len(href) > 1
                        and '?' not in href
                        and '#' not in href
                        and '/' not in href.lstrip('/')):
                    username = href.lstrip('/')
                    text = links.nth(i).inner_text()[:40].replace('\n', ' ')
                    if username not in user_links:
                        user_links.append(username)
                        print(f'    {len(user_links)}. /{username} - "{text}"')
            except Exception:
                pass
        print(f'  Total user links: {len(user_links)}')

        # ボタン一覧
        btns = page.locator('button')
        print(f'\n  Total buttons: {btns.count()}')
        for i in range(min(btns.count(), 20)):
            try:
                text = btns.nth(i).inner_text()[:40].replace('\n', ' ')
                print(f'    [{i}] "{text}"')
            except Exception:
                pass

        # 「もっと見る」リンク
        print('\n  --- "もっと見る" links ---')
        more = page.locator('a:has-text("もっと見る")')
        for i in range(more.count()):
            try:
                href = more.nth(i).get_attribute('href') or ''
                print(f'    [{i}] href="{href}"')
            except Exception:
                pass

        more_btn = page.locator('button:has-text("もっと見る")')
        print(f'  "もっと見る" buttons: {more_btn.count()}')

        # HTML保存
        html = page.content()
        with open('page_creator_ranking.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print('\n  HTML saved to page_creator_ranking.html')

    fetcher.fetch(
        'https://myfans.jp',
        headless=True,
        timeout=120000,
        page_action=action,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )


if __name__ == '__main__':
    debug_ranking()
