"""MyFans APIエンドポイント調査
ブラウザのネットワークリクエストをキャプチャして、APIパターンを記録する
"""
import json
from scrapling import StealthyFetcher
from utils import load_cookies

fetcher = StealthyFetcher()


def capture_network():
    cookies = load_cookies('myfans')
    captured = []

    def action(page):
        # ネットワークリクエストを記録
        def on_request(request):
            url = request.url
            # 静的ファイルとトラッキングを除外
            if any(x in url for x in ['_next/static', '.js', '.css', '.woff', '.png', '.jpg',
                                       'google', 'gtm', 'analytics', 'favicon', '.svg']):
                return
            captured.append({
                'type': 'request',
                'method': request.method,
                'url': url,
                'headers': dict(request.headers) if request.headers else {},
            })

        def on_response(response):
            url = response.url
            if any(x in url for x in ['_next/static', '.js', '.css', '.woff', '.png', '.jpg',
                                       'google', 'gtm', 'analytics', 'favicon', '.svg']):
                return
            body = ''
            content_type = response.headers.get('content-type', '')
            if 'json' in content_type:
                try:
                    body = response.json()
                except Exception:
                    try:
                        body = response.text()[:500]
                    except Exception:
                        pass

            captured.append({
                'type': 'response',
                'status': response.status,
                'url': url,
                'content_type': content_type,
                'body_preview': body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)[:500],
            })

        page.on('request', on_request)
        page.on('response', on_response)

        # 1. 年齢確認
        print('=== Age gate ===')
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

        # 2. ランキングページ
        print('\n=== Ranking page ===')
        captured.clear()
        page.evaluate("window.location.href = '/ranking/creators/all?term=daily&page=1'")
        page.wait_for_timeout(5000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)

        # 年齢確認（再表示される場合）
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

        print(f'  Captured {len(captured)} network events')
        for c in captured:
            if c['type'] == 'request':
                print(f'  >> {c["method"]} {c["url"]}')
            else:
                print(f'  << {c["status"]} {c["url"]} [{c["content_type"]}]')
                if c.get('body_preview'):
                    print(f'     Body: {c["body_preview"][:200]}')

        # 3. プロフィールページ
        print('\n=== Profile page (fanzazz) ===')
        captured.clear()
        page.evaluate("window.location.href = '/fanzazz'")
        page.wait_for_timeout(5000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)

        print(f'  Captured {len(captured)} network events')
        for c in captured:
            if c['type'] == 'request':
                print(f'  >> {c["method"]} {c["url"]}')
            else:
                print(f'  << {c["status"]} {c["url"]} [{c["content_type"]}]')
                if c.get('body_preview'):
                    print(f'     Body: {c["body_preview"][:200]}')

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
    capture_network()
