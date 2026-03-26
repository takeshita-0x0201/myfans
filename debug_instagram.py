"""Instagram ページ状態の調査"""
from scrapling import StealthyFetcher
from utils import load_cookies

fetcher = StealthyFetcher()

# テスト用URL: 存在しない/凍結/非公開/正常 それぞれ
TEST_URLS = [
    'https://www.instagram.com/__072q',           # 先ほど page not found だったアカウント
    'https://www.instagram.com/this_user_surely_does_not_exist_12345',  # 存在しないアカウント
    'https://www.instagram.com/instagram',         # 正常な公開アカウント
]


def debug_instagram():
    cookies = load_cookies('instagram')

    for url in TEST_URLS:
        print(f'\n{"="*60}')
        print(f'Testing: {url}')
        print(f'{"="*60}')

        def action(page, test_url=url):
            page.wait_for_timeout(5000)

            # URL確認（リダイレクトされた場合）
            print(f'  Final URL: {page.url}')
            print(f'  Title: {page.title()}')

            body_text = page.locator('body').inner_text()

            # 主要なキーワードをチェック
            keywords = [
                "this page isn't available",
                "ページがありません",
                "Sorry, this page",
                "ログイン",
                "Log in",
                "Log In",
                "Sign up",
                "Create an account",
                "suspended",
                "凍結",
                "violat",
                "規約",
                "This account has been",
                "is private",
                "非公開",
                "private",
                "restricted",
                "制限",
                "Content Unavailable",
                "followers",
                "posts",
            ]

            print(f'\n  --- Keyword check ---')
            for kw in keywords:
                if kw.lower() in body_text.lower():
                    print(f'    FOUND: "{kw}"')

            # body_text の先頭500文字を出力
            print(f'\n  --- Body text (first 500 chars) ---')
            clean = body_text[:500].replace('\n', ' | ')
            print(f'    {clean}')

            # HTMLを保存
            html = page.content()
            username = test_url.rstrip('/').split('/')[-1]
            filename = f'page_ig_{username}.html'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f'\n  HTML saved to {filename}')

        try:
            fetcher.fetch(
                url,
                headless=True,
                timeout=60000,
                page_action=action,
                network_idle=True,
                cookies=cookies,
            )
        except Exception as e:
            print(f'  ERROR: {e}')


if __name__ == '__main__':
    debug_instagram()
