"""MyFans ランキング＋プロフィール スクレイパー
ランキングページからユーザーを発見し、そのままプロフィールを取得する統合フロー
"""
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from scrapling import StealthyFetcher
from utils import load_cookies, parse_count, parse_relative_date, is_within_30d

# ランキング種別 → 全件ページURL
RANKING_URLS = {
    'daily': '/ranking/creators/all?term=daily',
    'weekly': '/ranking/creators/all?term=weekly',
    'monthly': '/ranking/creators/all?term=monthly',
    'yearly': '/ranking/creators/all?term=yearly',
}

# ユーザープロフィールリンクでないパスの一覧
EXCLUDE_PREFIXES = [
    '/posts/', '/ranking/', '/s/', '/feature/', '/genres',
    '/account', '/feed', '/en/', '/ja/', '/search',
]

# ページ並列取得のワーカー数
PAGE_WORKERS = 5


def _click_age_gate(page):
    """年齢確認ダイアログを突破"""
    try:
        buttons = page.locator('button')
        for i in range(buttons.count()):
            if 'はい' in buttons.nth(i).inner_text():
                buttons.nth(i).click()
                page.wait_for_timeout(2000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(1000)
                return
    except Exception:
        pass


def _extract_usernames(page) -> list[str]:
    """ページ内の全ユーザープロフィールリンクからユーザー名を抽出（出現順）"""
    usernames = []
    links = page.locator('a')
    for i in range(links.count()):
        try:
            href = links.nth(i).get_attribute('href') or ''
            if (href.startswith('/')
                    and not any(href.startswith(p) for p in EXCLUDE_PREFIXES)
                    and len(href) > 1
                    and '?' not in href
                    and '#' not in href
                    and '/' not in href.lstrip('/')):
                username = href.lstrip('/')
                if username and username not in usernames:
                    usernames.append(username)
        except Exception:
            pass
    return usernames


def _make_empty_data(username: str) -> dict:
    """空のデータテンプレートを生成"""
    data = {
        'scraped_at': datetime.now().strftime('%Y-%m-%d'),
        'rank': '',
        'rank_as': '',
        'name': '',
        'username': username,
        'myfans_url': f'https://myfans.jp/{username}',
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
    return data


def _scrape_profile(page, username: str) -> dict:
    """ユーザープロフィールページからデータを抽出"""
    data = _make_empty_data(username)
    post_dates = []

    # プロフィールページへ遷移
    page.evaluate(f"window.location.href = '/{username}'")
    page.wait_for_timeout(2000)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)
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
    bio_text = ''
    if bio_el.count() > 0:
        bio_text = bio_el.first.inner_text().strip()

    promo_texts = []
    spans = page.locator('span')
    for i in range(spans.count()):
        try:
            text = spans.nth(i).inner_text().strip()
            if '先月の投稿数' in text or 'おすすめのプラン' in text:
                promo_texts.append(text)
        except Exception:
            pass

    parts = []
    if promo_texts:
        parts.extend(promo_texts)
    if bio_text:
        parts.append(bio_text)
    data['profile_text'] = '\n'.join(parts) if parts else ''

    # === 先月の投稿数 ===
    for text in promo_texts:
        try:
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

    plans.sort(key=lambda p: p['price'])
    for idx, plan in enumerate(plans):
        if idx >= 9:
            break
        data[f'plan{idx+1}_price'] = plan['price']
        data[f'plan{idx+1}_posts'] = plan['posts']

    if any(p['price'] == 0 for p in plans):
        data['has_free_plan'] = 1

    page_text = page.locator('body').inner_text()
    if re.search(r'初月[無料半額]|トライアル|お試し|無料体験', page_text):
        data['has_trial_period'] = 1

    # === 投稿日付の取得（スワイプビュー） ===
    first_post = page.locator('a[href*="/posts/"]').first
    if first_post.count() > 0:
        first_post.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(1000)

        collected = set()
        for scroll_round in range(5):
            all_els = page.locator('span, div, p')
            count = all_els.count()
            for i in range(count):
                try:
                    text = all_els.nth(i).inner_text().strip()
                    if len(text) < 20 and ('日前' in text or '時間前' in text or '分前' in text or '月前' in text or '年前' in text):
                        if text not in collected:
                            collected.add(text)
                            parsed = parse_relative_date(text)
                            if parsed:
                                post_dates.append(parsed)
                except Exception:
                    pass
            page.evaluate('window.scrollBy(0, window.innerHeight)')
            page.wait_for_timeout(500)

        try:
            page.go_back()
            page.wait_for_timeout(2000)
        except Exception:
            pass

    # === 最古の投稿日付を取得 ===
    try:
        select = page.locator('.MuiSelect-select')
        if select.count() > 0:
            select.first.click()
            page.wait_for_timeout(500)
            items = page.locator('[role="option"], .MuiMenuItem-root, li')
            for i in range(items.count()):
                try:
                    text = items.nth(i).inner_text().strip()
                    if '古い' in text:
                        items.nth(i).click()
                        page.wait_for_timeout(2000)
                        page.wait_for_load_state('networkidle')
                        page.wait_for_timeout(1000)

                        oldest_post = page.locator('a[href*="/posts/"]').first
                        if oldest_post.count() > 0:
                            oldest_post.click()
                            page.wait_for_timeout(2000)
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

    # 投稿日付から集計
    if post_dates:
        unique_dates = sorted(set(post_dates))
        data['myfans_latest_post_date'] = unique_dates[-1]
        data['myfans_first_post_date'] = unique_dates[0]
        if not data['last_30d_posts']:
            data['last_30d_posts'] = sum(1 for d in unique_dates if is_within_30d(d))

    return data


def _fetch_pages_worker(term: str, worker_id: int, total_workers: int, limit: int | None) -> list[dict]:
    """ワーカー: ランキングページを取得し、各ユーザーのプロフィールもそのまま取得

    worker_id=0, total_workers=3 → pages 1, 4, 7, ...
    worker_id=1, total_workers=3 → pages 2, 5, 8, ...

    Returns: [{username, rank, rank_as, + 全プロフィールデータ}, ...]
    """
    fetcher = StealthyFetcher()
    cookies = load_cookies('myfans')
    base_url = RANKING_URLS[term]
    results = []  # (page_num, rank_in_page, data_dict)

    def action(page):
        _click_age_gate(page)

        page_num = worker_id + 1
        global_rank_offset = worker_id * 20  # 各ページ約20件想定

        while True:
            url = f'{base_url}&page={page_num}'
            print(f'  [{term}] W{worker_id+1}: page {page_num}')

            page.evaluate(f"window.location.href = '{url}'")
            page.wait_for_timeout(2000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(1000)

            if page_num == worker_id + 1:
                _click_age_gate(page)

            for _ in range(3):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(500)

            users = _extract_usernames(page)
            if not users:
                print(f'    [{term}] W{worker_id+1}: page {page_num} empty, stopping')
                break

            print(f'    [{term}] W{worker_id+1}: page {page_num} -> {len(users)} users, scraping profiles...')

            for idx, username in enumerate(users):
                try:
                    data = _scrape_profile(page, username)
                    data['rank_as'] = term
                    results.append((page_num, idx, data))
                    print(f'      [{term}] {username}: {data.get("name", "?")} | {data.get("followers", "?")} followers')
                except Exception as e:
                    print(f'      [{term}] {username}: ERROR {e}')
                    data = _make_empty_data(username)
                    data['rank_as'] = term
                    results.append((page_num, idx, data))

                # limit チェック
                if limit:
                    total_so_far = len(results)
                    if total_so_far >= limit:
                        return

            # ランキングの次のページへ（ワーカー分ストライド）
            page_num += total_workers

    fetcher.fetch(
        'https://myfans.jp',
        headless=True,
        timeout=3600000,  # 1時間（多数ユーザー対応）
        page_action=action,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )

    return results


def scrape_ranking_and_profiles(terms: list[str], limit: int | None = None) -> list[dict]:
    """ランキングからユーザーを発見し、プロフィールも一括取得

    Args:
        terms: ランキング種別のリスト
        limit: 各ランキングの取得件数上限

    Returns:
        list[dict]: 全プロフィールデータ（rank, rank_as付き）
    """
    all_entries = []

    for term in terms:
        if term not in RANKING_URLS:
            print(f'  Unknown term: {term}, skipping')
            continue

        print(f'\n  [{term}] Starting with {PAGE_WORKERS} parallel browsers...')

        # 各ワーカーを並列実行
        all_results = []
        with ThreadPoolExecutor(max_workers=PAGE_WORKERS) as executor:
            futures = {
                executor.submit(_fetch_pages_worker, term, i, PAGE_WORKERS, limit): i
                for i in range(PAGE_WORKERS)
            }
            for future in as_completed(futures):
                worker_id = futures[future]
                try:
                    worker_results = future.result()
                    all_results.extend(worker_results)
                except Exception as e:
                    print(f'  [{term}] Worker {worker_id+1} failed: {e}')

        # ページ番号→ページ内順序でソートして順位を振る
        all_results.sort(key=lambda x: (x[0], x[1]))

        # 重複ユーザー除去（複数ワーカーが同じユーザーを拾う可能性は低いが念のため）
        seen = set()
        rank = 0
        for page_num, idx_in_page, data in all_results:
            username = data['username']
            if username in seen:
                continue
            seen.add(username)
            rank += 1
            data['rank'] = rank

            if limit and rank > limit:
                break

            all_entries.append(data)

        print(f'  [{term}] Done: {len([e for e in all_entries if e["rank_as"] == term])} users')

    print(f'\n  === Complete: {len(all_entries)} entries ===')
    return all_entries


if __name__ == '__main__':
    import sys
    terms = [a for a in sys.argv[1:] if a in RANKING_URLS]
    numbers = [a for a in sys.argv[1:] if a.isdigit()]
    limit = int(numbers[0]) if numbers else None

    if not terms:
        print('Usage: python scraper_discover.py <daily|weekly|monthly|yearly> [件数]')
        sys.exit(1)

    entries = scrape_ranking_and_profiles(terms, limit)
    print(f'\nTotal: {len(entries)} entries')
    for e in entries[:10]:
        print(f'  #{e["rank"]} [{e["rank_as"]}] {e["username"]} - {e.get("name", "?")}')
