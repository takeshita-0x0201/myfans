"""MyFans APIレスポンスの全フィールドを確認"""
import json
from scrapling import StealthyFetcher
from utils import load_cookies

fetcher = StealthyFetcher()


def capture_full_responses():
    cookies = load_cookies('myfans')
    responses = {}

    def action(page):
        def on_response(response):
            url = response.url
            if 'api.myfans.jp' not in url:
                return
            # 主要APIのみキャプチャ
            key_patterns = [
                'ranking/creators/all',
                'show_by_username',
                '/plans',
                '/posts?',
                'ranking_orders',
                'api/v1/users/',
            ]
            if not any(p in url for p in key_patterns):
                return
            try:
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type:
                    body = response.json()
                    responses[url] = body
            except Exception:
                pass

        page.on('response', on_response)

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

        # ランキングページ
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

        # プロフィールページ
        page.evaluate("window.location.href = '/fanzazz'")
        page.wait_for_timeout(5000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)

    fetcher.fetch(
        'https://myfans.jp',
        headless=True,
        timeout=120000,
        page_action=action,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )

    # レスポンスを出力
    for url, body in responses.items():
        print(f'\n{"="*80}')
        print(f'URL: {url}')
        print(f'{"="*80}')
        # data配列の場合は最初の1件のみ表示
        if isinstance(body, dict) and 'data' in body and isinstance(body['data'], list):
            print(f'Total items: {len(body["data"])}')
            if body['data']:
                print(f'First item keys: {list(body["data"][0].keys())}')
                print(json.dumps(body['data'][0], indent=2, ensure_ascii=False)[:2000])
        elif isinstance(body, list):
            print(f'Array length: {len(body)}')
            if body:
                print(json.dumps(body[0] if len(body) == 1 else body, indent=2, ensure_ascii=False)[:2000])
        else:
            print(json.dumps(body, indent=2, ensure_ascii=False)[:2000])

    # JSONファイルにも保存
    with open('api_responses.json', 'w', encoding='utf-8') as f:
        json.dump(responses, f, indent=2, ensure_ascii=False)
    print(f'\n\nSaved to api_responses.json')


if __name__ == '__main__':
    capture_full_responses()
