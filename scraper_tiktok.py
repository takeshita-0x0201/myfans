"""TikTok プロフィール スクレイパー"""
import re
from datetime import datetime
from scrapling import StealthyFetcher
from utils import load_cookies, parse_count, is_within_30d

fetcher = StealthyFetcher()


def scrape_tiktok_profile(url: str) -> dict:
    """TikTokプロフィールからデータを取得"""
    data = {
        'tiktok_followers': '',
        'tiktok_posts': '',
        'tiktok_last_30d_posts': '',
        'tiktok_latest_post_date': '',
        'tiktok_first_post_date': '',
    }

    if not url or url == 'N/A':
        return data

    cookies = load_cookies('tiktok')
    post_dates = []

    def action_scrape(page):
        nonlocal post_dates
        page.wait_for_timeout(3000)

        # === フォロワー数 ===
        try:
            follower_el = page.locator('[data-e2e="followers-count"]')
            if follower_el.count() > 0:
                val = follower_el.first.inner_text().strip()
                if '万' in val:
                    data['tiktok_followers'] = int(float(val.replace('万', '')) * 10000)
                elif '億' in val:
                    data['tiktok_followers'] = int(float(val.replace('億', '')) * 100000000)
                else:
                    data['tiktok_followers'] = parse_count(val) or ''
        except Exception:
            pass

        # フォールバック: strong要素から（フォロー中, フォロワー, いいね の順）
        if not data['tiktok_followers']:
            try:
                strongs = page.locator('strong')
                texts = []
                for i in range(min(strongs.count(), 5)):
                    texts.append(strongs.nth(i).inner_text().strip())
                # TikTok以外のstrongをスキップ（最初の2つが"TikTok"の場合）
                stat_texts = [t for t in texts if t != 'TikTok']
                if len(stat_texts) >= 2:
                    val = stat_texts[1]  # 2番目がフォロワー
                    if '万' in val:
                        data['tiktok_followers'] = int(float(val.replace('万', '')) * 10000)
                    else:
                        data['tiktok_followers'] = parse_count(val) or ''
            except Exception:
                pass

        # === 投稿数: 動画サムネイルをカウント ===
        try:
            items = page.locator('[data-e2e="user-post-item"]')
            count = items.count()
            for _ in range(10):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(1500)
                new_count = page.locator('[data-e2e="user-post-item"]').count()
                if new_count == count:
                    break
                count = new_count
            if count > 0:
                data['tiktok_posts'] = count
        except Exception:
            pass

        # === 最新動画の日付を取得 ===
        # プロフィールに戻してから最初の動画をクリック
        try:
            page.evaluate('window.scrollTo(0, 0)')
            page.wait_for_timeout(1000)
            video_links = page.locator('[data-e2e="user-post-item"] a')
            if video_links.count() > 0:
                video_links.first.click()
                page.wait_for_timeout(5000)

                # 動画詳細ページから日付を取得（YYYY-M-D 形式）
                body = page.locator('body').inner_text()
                dates_found = re.findall(r'(\d{4})-(\d{1,2})-(\d{1,2})', body)
                for y, m, d in dates_found:
                    try:
                        dt = datetime(int(y), int(m), int(d))
                        if 2020 <= dt.year <= 2030:
                            post_dates.append(dt.strftime('%Y-%m-%d'))
                    except ValueError:
                        pass

                # 戻る
                page.go_back()
                page.wait_for_timeout(3000)
        except Exception:
            pass

        # === 最古の動画の日付を取得 ===
        try:
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(2000)
            video_links = page.locator('[data-e2e="user-post-item"] a')
            total = video_links.count()
            if total > 1:
                video_links.nth(total - 1).click()
                page.wait_for_timeout(5000)

                body = page.locator('body').inner_text()
                dates_found = re.findall(r'(\d{4})-(\d{1,2})-(\d{1,2})', body)
                for y, m, d in dates_found:
                    try:
                        dt = datetime(int(y), int(m), int(d))
                        if 2020 <= dt.year <= 2030:
                            post_dates.append(dt.strftime('%Y-%m-%d'))
                    except ValueError:
                        pass
        except Exception:
            pass

    try:
        page = fetcher.fetch(
            url,
            headless=True,
            timeout=90000,
            page_action=action_scrape,
            network_idle=True,
            cookies=cookies,
        )
    except Exception as e:
        print(f'  TikTok scrape error for {url}: {e}')
        return data

    if post_dates:
        unique_dates = sorted(set(post_dates))
        data['tiktok_latest_post_date'] = unique_dates[-1]
        data['tiktok_first_post_date'] = unique_dates[0]
        data['tiktok_last_30d_posts'] = sum(1 for d in unique_dates if is_within_30d(d))

    return data


if __name__ == '__main__':
    result = scrape_tiktok_profile('https://www.tiktok.com/@_57391')
    for k, v in result.items():
        print(f'{k}: {v}')
