"""APIリクエストのヘッダーをキャプチャ"""
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scrapling import StealthyFetcher
from utils import load_cookies

fetcher = StealthyFetcher()


def capture_headers():
    cookies = load_cookies('myfans')

    def action(page):
        def on_request(request):
            url = request.url
            if 'api.myfans.jp/api/ranking/creators' in url:
                print(f'\n=== Request to: {url} ===')
                headers = dict(request.headers)
                for k, v in sorted(headers.items()):
                    print(f'  {k}: {v}')

        page.on('request', on_request)

        # 年齢確認
        try:
            buttons = page.locator('button')
            for i in range(buttons.count()):
                if 'はい' in buttons.nth(i).inner_text():
                    buttons.nth(i).click()
                    page.wait_for_timeout(2000)
                    page.wait_for_load_state('networkidle')
                    page.wait_for_timeout(1000)
                    break
        except Exception:
            pass

        page.evaluate("window.location.href = '/ranking/creators/all?term=daily&page=1'")
        page.wait_for_timeout(5000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)

        # 年齢確認（再表示）
        try:
            buttons = page.locator('button')
            for i in range(buttons.count()):
                if 'はい' in buttons.nth(i).inner_text():
                    buttons.nth(i).click()
                    page.wait_for_timeout(2000)
                    page.wait_for_load_state('networkidle')
                    page.wait_for_timeout(2000)
                    break
        except Exception:
            pass

    fetcher.fetch(
        'https://myfans.jp',
        headless=True,
        timeout=60000,
        page_action=action,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )


if __name__ == '__main__':
    capture_headers()
