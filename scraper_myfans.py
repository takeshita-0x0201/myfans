"""MyFans ユーザープロフィール スクレイパー"""
import re
import time
from datetime import datetime
from scrapling import StealthyFetcher
from utils import load_cookies, parse_count, parse_relative_date, is_within_30d

fetcher = StealthyFetcher()


def _click_age_gate(page):
    """年齢確認ダイアログを突破"""
    try:
        buttons = page.locator('button')
        for i in range(buttons.count()):
            if 'はい' in buttons.nth(i).inner_text():
                buttons.nth(i).click()
                page.wait_for_timeout(3000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)
                return
    except Exception:
        pass


def scrape_user_profile(username: str) -> dict:
    """ユーザープロフィールをスクレイピング"""
    url = f'https://myfans.jp/{username}'
    cookies = load_cookies('myfans')

    data = {
        'scraped_at': datetime.now().strftime('%Y-%m-%d'),
        'rank': '',
        'name': '',
        'username': username,
        'myfans_url': url,
        'profile_text': '',
        'followers': '',
        'likes': '',
        'posts': '',
        'last_30d_posts': '',
        'myfans_latest_post_date': '',
        'myfans_first_post_date': '',
        'sns_x': 0, 'sns_url_x': '',
        'sns_instagram': 0, 'sns_url_instagram': '',
        'sns_tiktok': 0, 'sns_url_tiktok': '',
        'sns_others': 0, 'sns_others_name': '', 'sns_url_others': '',
    }
    for i in range(1, 10):
        data[f'plan{i}_price'] = ''
        data[f'plan{i}_posts'] = ''
    data['has_free_plan'] = 0
    data['has_trial_period'] = 0
    data['has_update_frequency'] = ''

    post_dates = []

    def action_scrape(page):
        nonlocal post_dates
        _click_age_gate(page)

        # === 表示名 ===
        title = page.title()
        if title:
            m = re.match(r'^(.+?)のプライベートSNS', title)
            if m:
                data['name'] = m.group(1)

        # === 統計情報 (投稿/いいね/フォロワー) ===
        stat_values = page.locator('.text-xl.font-bold')
        stat_labels = page.locator('.text-xxs')
        stat_nums = []
        for i in range(stat_values.count()):
            try:
                val = stat_values.nth(i).inner_text().strip()
                if val:
                    stat_nums.append(val)
            except Exception:
                pass

        label_list = []
        for i in range(stat_labels.count()):
            try:
                label_list.append(stat_labels.nth(i).inner_text().strip())
            except Exception:
                pass

        # ラベルとマッチング
        for idx, label in enumerate(label_list):
            if idx < len(stat_nums):
                if '投稿' in label:
                    data['posts'] = parse_count(stat_nums[idx]) or ''
                elif 'いいね' in label:
                    data['likes'] = parse_count(stat_nums[idx]) or ''
                elif 'フォロワー' in label:
                    data['followers'] = parse_count(stat_nums[idx]) or ''

        # === プロフィール文 ===
        bio_el = page.locator('.pb-6.font-light.text-black')
        if bio_el.count() == 0:
            bio_el = page.locator('[class*="pb-6"][class*="font-light"][class*="text-black"]')
        if bio_el.count() > 0:
            data['profile_text'] = bio_el.first.inner_text().strip()

        # === 先月の投稿数 ===
        spans = page.locator('span')
        for i in range(spans.count()):
            try:
                text = spans.nth(i).inner_text().strip()
                m = re.search(r'先月の投稿数[：:]?\s*(\d+)', text)
                if m:
                    data['last_30d_posts'] = int(m.group(1))
                    break
            except Exception:
                pass

        # === SNSリンク ===
        links = page.locator('a')
        others = []
        for i in range(links.count()):
            try:
                href = links.nth(i).get_attribute('href') or ''
            except Exception:
                continue

            if 'twitter.com' in href or 'x.com' in href:
                data['sns_x'] = 1
                data['sns_url_x'] = href
            elif 'instagram.com' in href:
                data['sns_instagram'] = 1
                data['sns_url_instagram'] = href
            elif 'tiktok.com' in href:
                data['sns_tiktok'] = 1
                data['sns_url_tiktok'] = href
            elif href.startswith('http') and 'myfans.jp' not in href:
                if 'youtube.com' in href or 'youtu.be' in href:
                    others.append(('youtube', href))
                elif 'lit.link' in href:
                    others.append(('lit.link', href))
                else:
                    others.append(('other', href))

        if others:
            data['sns_others'] = 1
            data['sns_others_name'] = others[0][0]
            data['sns_url_others'] = others[0][1]

        # === プラン情報 ===
        # 「投稿XXX件」テキストの親要素に「¥X,XXX」が含まれる
        plans = []
        all_els = page.locator('span, div')
        el_count = all_els.count()
        for i in range(el_count):
            try:
                text = all_els.nth(i).inner_text().strip()
                if text.startswith('投稿') and '件' in text and len(text) < 15:
                    parent_text = all_els.nth(i).locator('..').inner_text().strip()
                    price_m = re.search(r'¥([\d,]+)', parent_text)
                    posts_m = re.search(r'投稿\s*(\d+)\s*件', parent_text)
                    if price_m:
                        price = int(price_m.group(1).replace(',', ''))
                        posts_count = int(posts_m.group(1)) if posts_m else 0
                        if not any(p['price'] == price for p in plans):
                            plans.append({'price': price, 'posts': posts_count})
            except Exception:
                pass

        # 金額昇順ソート
        plans.sort(key=lambda p: p['price'])

        for idx, plan in enumerate(plans):
            if idx >= 9:
                break
            data[f'plan{idx+1}_price'] = plan['price']
            data[f'plan{idx+1}_posts'] = plan['posts']

        # has_free_plan
        if any(p['price'] == 0 for p in plans):
            data['has_free_plan'] = 1

        # has_trial_period
        page_text = page.locator('body').inner_text()
        if re.search(r'初月[無料半額]|トライアル|お試し|無料体験', page_text):
            data['has_trial_period'] = 1

        # === 投稿日付の取得（スワイプビュー） ===
        # 最新の投稿リンクをクリックしてスワイプビューに入り、日付を収集
        first_post = page.locator('a[href*="/posts/"]').first
        if first_post.count() > 0:
            first_post.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

            # スワイプビューで日付を収集（最新〜過去へスクロール）
            collected = set()
            for scroll_round in range(15):
                all_els = page.locator('span, div, p')
                count = all_els.count()
                found_new = False
                for i in range(count):
                    try:
                        text = all_els.nth(i).inner_text().strip()
                        if len(text) < 20 and ('日前' in text or '時間前' in text or '分前' in text or '月前' in text or '年前' in text):
                            if text not in collected:
                                collected.add(text)
                                parsed = parse_relative_date(text)
                                if parsed:
                                    post_dates.append(parsed)
                                    found_new = True
                    except Exception:
                        pass

                # 次の投稿へスワイプ（下スクロール or スワイプ）
                # スワイプビューではスクロールで次の投稿に進む
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(800)

            # 戻る
            try:
                page.go_back()
                page.wait_for_timeout(2000)
            except Exception:
                pass

        # === 最古の投稿日付を取得 ===
        # 「古い順」に切り替えて最初の投稿日付を取得
        try:
            select = page.locator('.MuiSelect-select')
            if select.count() > 0:
                select.first.click()
                page.wait_for_timeout(1000)
                items = page.locator('[role="option"], .MuiMenuItem-root, li')
                for i in range(items.count()):
                    try:
                        text = items.nth(i).inner_text().strip()
                        if '古い' in text:
                            items.nth(i).click()
                            page.wait_for_timeout(3000)
                            page.wait_for_load_state('networkidle')
                            page.wait_for_timeout(2000)

                            # 最古の投稿をクリック
                            oldest_post = page.locator('a[href*="/posts/"]').first
                            if oldest_post.count() > 0:
                                oldest_post.click()
                                page.wait_for_timeout(3000)
                                # 日付を取得
                                all_els = page.locator('span, div, p')
                                for j in range(all_els.count()):
                                    try:
                                        t = all_els.nth(j).inner_text().strip()
                                        if len(t) < 20 and ('日前' in t or '時間前' in t or '月前' in t or '年前' in t):
                                            parsed = parse_relative_date(t)
                                            if parsed:
                                                post_dates.append(parsed)
                                    except Exception:
                                        pass
                            break
                    except Exception:
                        pass
        except Exception:
            pass

    page = fetcher.fetch(
        url,
        headless=True,
        timeout=120000,
        page_action=action_scrape,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )

    # 投稿日付から集計
    if post_dates:
        unique_dates = sorted(set(post_dates))
        data['myfans_latest_post_date'] = unique_dates[-1]
        data['myfans_first_post_date'] = unique_dates[0]
        # last_30d_posts が先月テキストから取れなかった場合のフォールバック
        if not data['last_30d_posts']:
            data['last_30d_posts'] = sum(1 for d in unique_dates if is_within_30d(d))

    return data


def scrape_users(usernames: list[str], progress_callback=None) -> list[dict]:
    """複数ユーザーをスクレイピング"""
    results = []
    for idx, username in enumerate(usernames):
        print(f'[{idx+1}/{len(usernames)}] Scraping MyFans: {username}')
        try:
            result = scrape_user_profile(username)
            results.append(result)
            print(f'  -> {result["name"]} | {result["followers"]} followers | {result["posts"]} posts')
        except Exception as e:
            print(f'  -> ERROR: {e}')
            results.append({'username': username, 'error': str(e)})
        if progress_callback:
            progress_callback(idx + 1, len(usernames))
        time.sleep(2)
    return results


if __name__ == '__main__':
    result = scrape_user_profile('_072q')
    print('\n=== Result ===')
    for k, v in result.items():
        if v != '' and v != 0:
            print(f'{k}: {v}')
