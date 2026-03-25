"""X (Twitter) プロフィール スクレイパー"""
import re
import time
from datetime import datetime
from scrapling import StealthyFetcher
from utils import load_cookies, parse_count, parse_relative_date, is_within_30d

fetcher = StealthyFetcher()


def scrape_x_profile(url: str) -> dict:
    """Xプロフィールページからデータを取得"""
    data = {
        'x_followers': '',
        'x_posts': '',
        'x_last_30d_posts': '',
        'x_latest_post_date': '',
        'x_first_post_date': '',
    }

    if not url or url == 'N/A':
        return data

    cookies = load_cookies('x')
    post_dates = []

    def action_scrape(page):
        nonlocal post_dates
        page.wait_for_timeout(3000)

        # センシティブコンテンツ警告を突破
        try:
            yes_btn = page.locator('text=Yes, view profile')
            if yes_btn.count() > 0:
                yes_btn.first.click()
                page.wait_for_timeout(3000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)
        except Exception:
            pass
        # 日本語版
        try:
            yes_btn = page.locator('text=プロフィールを表示')
            if yes_btn.count() > 0:
                yes_btn.first.click()
                page.wait_for_timeout(3000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)
        except Exception:
            pass

        # フォロワー数: "X Followers" or "Xフォロワー"
        # Twitterは aria-label や data-testid で構造化されている
        try:
            # followers リンクを探す
            follower_link = page.locator('a[href$="/verified_followers"]')
            if follower_link.count() == 0:
                follower_link = page.locator('a[href$="/followers"]')

            if follower_link.count() > 0:
                text = follower_link.first.inner_text().strip()
                # "123.4K Followers" or "12.3万 フォロワー"
                m = re.search(r'([\d,.]+[KMkm万億]?)\s*(Follower|フォロワー)', text, re.I)
                if m:
                    val = m.group(1)
                    if '万' in val:
                        data['x_followers'] = int(float(val.replace('万', '')) * 10000)
                    elif '億' in val:
                        data['x_followers'] = int(float(val.replace('億', '')) * 100000000)
                    else:
                        data['x_followers'] = parse_count(val) or ''
                else:
                    # 数値だけ抽出
                    nums = re.findall(r'[\d,.]+[KMkm]?', text)
                    if nums:
                        data['x_followers'] = parse_count(nums[0]) or ''
        except Exception:
            pass

        # 投稿数: bodyテキストから "X,XXX posts" or "Xポスト" パターン
        try:
            body_text = page.locator('body').inner_text()
            m = re.search(r'([\d,.]+[KMkm万]?)\s*(posts?|ポスト|件のポスト)', body_text, re.I)
            if m:
                val = m.group(1)
                if '万' in val:
                    data['x_posts'] = int(float(val.replace('万', '')) * 10000)
                else:
                    data['x_posts'] = parse_count(val) or ''
        except Exception:
            pass

        # 投稿日付の取得（タイムラインから）
        try:
            # timeタグからdatetime属性を取得
            time_els = page.locator('time[datetime]')
            time_count = time_els.count()
            for i in range(min(time_count, 30)):
                try:
                    dt_str = time_els.nth(i).get_attribute('datetime')
                    if dt_str:
                        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                        post_dates.append(dt.strftime('%Y-%m-%d'))
                except Exception:
                    pass

            # もっとスクロールして投稿を読み込む
            for _ in range(5):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(2000)
                time_els = page.locator('time[datetime]')
                new_count = time_els.count()
                for i in range(time_count, min(new_count, 60)):
                    try:
                        dt_str = time_els.nth(i).get_attribute('datetime')
                        if dt_str:
                            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                            post_dates.append(dt.strftime('%Y-%m-%d'))
                    except Exception:
                        pass
                if new_count == time_count:
                    break
                time_count = new_count
        except Exception:
            pass

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
        print(f'  X scrape error for {url}: {e}')
        return data

    # 投稿日付の集計
    if post_dates:
        unique_dates = sorted(set(post_dates), reverse=True)
        data['x_latest_post_date'] = unique_dates[0]
        data['x_last_30d_posts'] = sum(1 for d in unique_dates if is_within_30d(d))
        # 最古は取得したうちの最後（スクロール限界あり）
        data['x_first_post_date'] = unique_dates[-1]

    return data


if __name__ == '__main__':
    result = scrape_x_profile('https://twitter.com/_072q')
    for k, v in result.items():
        print(f'{k}: {v}')
