"""Instagram プロフィール スクレイパー"""
import re
from datetime import datetime
from scrapling import StealthyFetcher
from utils import load_cookies, parse_count, is_within_30d

fetcher = StealthyFetcher()


def scrape_instagram_profile(url: str) -> dict:
    """Instagramプロフィールからデータを取得"""
    data = {
        'instagram_followers': '',
        'instagram_posts': '',
        'instagram_last_30d_posts': '',
        'instagram_latest_post_date': '',
        'instagram_first_post_date': '',
    }

    if not url or url == 'N/A':
        return data

    cookies = load_cookies('instagram')
    post_dates = []

    def action_scrape(page):
        nonlocal post_dates
        page.wait_for_timeout(5000)

        body_text = page.locator('body').inner_text()

        # ページが存在しない場合
        if "this page isn't available" in body_text or 'ページがありません' in body_text:
            print(f'  Instagram: page not found')
            return

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

    try:
        page = fetcher.fetch(
            url,
            headless=True,
            timeout=60000,
            page_action=action_scrape,
            network_idle=True,
            cookies=cookies,
        )
    except Exception as e:
        print(f'  Instagram scrape error for {url}: {e}')
        return data

    if post_dates:
        unique_dates = sorted(set(post_dates), reverse=True)
        data['instagram_latest_post_date'] = unique_dates[0]
        data['instagram_last_30d_posts'] = sum(1 for d in unique_dates if is_within_30d(d))
        data['instagram_first_post_date'] = unique_dates[-1]

    return data


if __name__ == '__main__':
    # テスト: 存在するアカウント
    result = scrape_instagram_profile('https://www.instagram.com/mizukawasumireworld')
    for k, v in result.items():
        print(f'{k}: {v}')
