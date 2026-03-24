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

        try:
            # TikTokプロフィール: フォロワー数
            # data-e2e="followers-count" 属性
            follower_el = page.locator('[data-e2e="followers-count"]')
            if follower_el.count() > 0:
                text = follower_el.first.inner_text().strip()
                val = text
                # TikTokは "12.3万" や "1.2M" 形式
                if '万' in val:
                    data['tiktok_followers'] = int(float(val.replace('万', '')) * 10000)
                elif '億' in val:
                    data['tiktok_followers'] = int(float(val.replace('億', '')) * 100000000)
                else:
                    data['tiktok_followers'] = parse_count(val) or ''

            # いいね数 (参考)
            # data-e2e="likes-count"

            # 動画数（プロフィールヘッダーにはないが、投稿タブに件数がある場合）
            # h2[data-e2e="user-tab-title"] or similar
            tab_els = page.locator('[data-e2e="videos-tab"]')
            if tab_els.count() > 0:
                text = tab_els.first.inner_text().strip()
                m = re.search(r'(\d+)', text)
                if m:
                    data['tiktok_posts'] = int(m.group(1))
        except Exception:
            pass

        # フォロワー数が取れない場合、テキストから探す
        if not data['tiktok_followers']:
            try:
                # "123 Follower" or "123 フォロワー" パターンを探す
                strong_els = page.locator('strong')
                count = strong_els.count()
                texts = []
                for i in range(count):
                    texts.append(strong_els.nth(i).inner_text().strip())

                # strongタグが3つ: フォロー中, フォロワー, いいね の順
                if len(texts) >= 2:
                    # 2番目がフォロワー
                    val = texts[1]
                    if '万' in val:
                        data['tiktok_followers'] = int(float(val.replace('万', '')) * 10000)
                    else:
                        data['tiktok_followers'] = parse_count(val) or ''
            except Exception:
                pass

        # 投稿数: 動画サムネイル数をカウント + スクロールで全件読み込み
        if not data['tiktok_posts']:
            try:
                # data-e2e="user-post-item" が動画カード
                items = page.locator('[data-e2e="user-post-item"]')
                count = items.count()
                # スクロールして全件読み込み
                for _ in range(10):
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    page.wait_for_timeout(1500)
                    new_count = page.locator('[data-e2e="user-post-item"]').count()
                    if new_count == count:
                        break
                    count = new_count
                if count > 0:
                    data['tiktok_posts'] = count
                else:
                    # フォールバック: strong要素から再生数を持つものを数える
                    strong_els = page.locator('strong')
                    video_count = 0
                    for i in range(strong_els.count()):
                        text = strong_els.nth(i).inner_text().strip()
                        if text and text[0].isdigit() and i >= 5:
                            video_count += 1
                    if video_count > 0:
                        data['tiktok_posts'] = video_count
            except Exception:
                pass

        # 投稿日付: 各動画のリンクから取得は難しいが、
        # 個別動画ページに行かないと正確な日付は取れない
        # ここでは動画サムネイルの一覧から取得可能な情報を集める
        try:
            # 動画カード内の日付テキスト
            date_els = page.locator('[data-e2e="video-card"] [class*="date"], [data-e2e="user-post-item"]')
            for i in range(min(date_els.count(), 30)):
                try:
                    text = date_els.nth(i).inner_text().strip()
                    # "3日前" "2024-01-01" 等
                    from utils import parse_relative_date
                    parsed = parse_relative_date(text)
                    if parsed:
                        post_dates.append(parsed)
                except Exception:
                    pass
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
        print(f'  TikTok scrape error for {url}: {e}')
        return data

    if post_dates:
        unique_dates = sorted(set(post_dates), reverse=True)
        data['tiktok_latest_post_date'] = unique_dates[0]
        data['tiktok_last_30d_posts'] = sum(1 for d in unique_dates if is_within_30d(d))
        data['tiktok_first_post_date'] = unique_dates[-1]

    return data


if __name__ == '__main__':
    result = scrape_tiktok_profile('https://www.tiktok.com/@_57391')
    for k, v in result.items():
        print(f'{k}: {v}')
