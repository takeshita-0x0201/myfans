"""Instagram プロフィール スクレイパー"""
import re
import time
from datetime import datetime
from scrapling import StealthyFetcher
from utils import load_cookies, parse_count, is_within_30d

fetcher = StealthyFetcher()


def _make_empty_ig_data() -> dict:
    """空のデータテンプレートを生成"""
    return {
        'instagram_followers': '',
        'instagram_posts': '',
        'instagram_last_30d_posts': '',
        'instagram_latest_post_date': '',
        'instagram_first_post_date': '',
        'instagram_status': '',
    }


def _scrape_ig_page(page, url: str) -> dict:
    """pageオブジェクトで1URL分を処理"""
    data = _make_empty_ig_data()
    post_dates = []

    # ページ遷移
    page.evaluate(f"window.location.href = '{url}'")
    page.wait_for_timeout(3000)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    body_text = page.locator('body').inner_text()
    body_lower = body_text.lower()

    # ログインページにリダイレクトされた場合
    if 'login' in page.url or ('log in' in body_lower and 'followers' not in body_lower):
        data['instagram_status'] = 'login_required'
        print(f'    Instagram: login required')
        return data

    # ページが存在しない / アカウント凍結・削除
    if "this page isn't available" in body_text or 'ページがありません' in body_text:
        data['instagram_status'] = 'not_available'
        print(f'    Instagram: not available (suspended/deleted/not found)')
        return data

    # 非公開アカウント
    if 'this account is private' in body_lower or '非公開' in body_text:
        data['instagram_status'] = 'private'
        print(f'    Instagram: private account')
        # 非公開でもフォロワー数は取得できる場合がある（以下で取得を続行）

    # 正常
    if not data['instagram_status']:
        data['instagram_status'] = 'ok'

    # フォロワー数: "XXX followers" パターン（bodyテキストから）
    m = re.search(r'([\d,.]+[KMkm]?)\s*followers', body_text, re.I)
    if m:
        data['instagram_followers'] = parse_count(m.group(1)) or ''

    # 投稿数: "XXX posts" パターン
    m = re.search(r'([\d,.]+[KMkm]?)\s*posts', body_text, re.I)
    if m:
        data['instagram_posts'] = parse_count(m.group(1)) or ''

    # 日本語フォールバック
    if not data['instagram_followers']:
        m = re.search(r'([\d,.]+[KMkm万億]?)\s*人のフォロワー', body_text)
        if m:
            val = m.group(1)
            if '万' in val:
                data['instagram_followers'] = int(float(val.replace('万', '')) * 10000)
            else:
                data['instagram_followers'] = parse_count(val) or ''

    if not data['instagram_posts']:
        m = re.search(r'([\d,.]+[KMkm万]?)\s*件の投稿', body_text)
        if m:
            data['instagram_posts'] = parse_count(m.group(1)) or ''

    # 投稿の日付取得: time タグ
    time_els = page.locator('time[datetime]')
    for i in range(min(time_els.count(), 30)):
        try:
            dt_str = time_els.nth(i).get_attribute('datetime')
            if dt_str:
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                post_dates.append(dt.strftime('%Y-%m-%d'))
        except Exception:
            pass

    # スクロールしてさらに読み込む
    for _ in range(3):
        prev_count = len(post_dates)
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(2000)
        new_time_els = page.locator('time[datetime]')
        for i in range(new_time_els.count()):
            try:
                dt_str = new_time_els.nth(i).get_attribute('datetime')
                if dt_str:
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    post_dates.append(dt.strftime('%Y-%m-%d'))
            except Exception:
                pass
        if len(post_dates) == prev_count:
            break

    if post_dates:
        unique_dates = sorted(set(post_dates), reverse=True)
        data['instagram_latest_post_date'] = unique_dates[0]
        data['instagram_last_30d_posts'] = sum(1 for d in unique_dates if is_within_30d(d))
        data['instagram_first_post_date'] = unique_dates[-1]

    return data


def scrape_all_instagram(urls: list[str]) -> dict[str, dict]:
    """全URLを1ブラウザセッションでスクレイピング"""
    if not urls:
        return {}

    cookies = load_cookies('instagram')
    results = {}

    def page_action(page):
        for idx, url in enumerate(urls):
            print(f'  [{idx+1}/{len(urls)}] Instagram: {url}')
            try:
                data = _scrape_ig_page(page, url)
                results[url] = data
                print(f'    -> followers={data["instagram_followers"]} posts={data["instagram_posts"]} status={data["instagram_status"]}')
            except Exception as e:
                print(f'    -> ERROR: {e}')
                results[url] = _make_empty_ig_data()
            time.sleep(2)

    try:
        fetcher.fetch(
            urls[0],
            headless=True,
            timeout=60000 + len(urls) * 30000,
            page_action=page_action,
            network_idle=True,
            cookies=cookies,
        )
    except Exception as e:
        print(f'  Instagram browser error: {e}')
        for url in urls:
            if url not in results:
                results[url] = _make_empty_ig_data()

    return results


def scrape_instagram_profile(url: str) -> dict:
    """Instagramプロフィールからデータを取得（後方互換）"""
    if not url or url == 'N/A':
        return _make_empty_ig_data()

    results = scrape_all_instagram([url])
    return results.get(url, _make_empty_ig_data())


if __name__ == '__main__':
    # テスト: 存在するアカウント
    result = scrape_instagram_profile('https://www.instagram.com/mizukawasumireworld')
    for k, v in result.items():
        print(f'{k}: {v}')
