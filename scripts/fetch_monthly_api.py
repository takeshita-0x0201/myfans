"""MyFans 月間ランキング API取得スクリプト
1ページ(20件)ずつ取得→詳細取得→CSV追記 を繰り返す
"""
import json, csv, requests, os, time
from datetime import datetime

# === Setup ===
with open('cookies/myfans.json') as f:
    cookie_list = json.load(f)

session = requests.Session()
for c in cookie_list:
    session.cookies.set(c['name'], c['value'], domain=c.get('domain', '').lstrip('.'), path=c.get('path', '/'))

token = next(c['value'] for c in cookie_list if c['name'] == '_mfans_token')
session.headers.update({
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'ja-JP',
    'authorization': f'Token token={token}',
    'google-ga-data': 'event328',
    'origin': 'https://myfans.jp',
    'referer': 'https://myfans.jp/',
    'sec-ch-ua': '"Chromium";v="145", "Not:A-Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/145.0.0.0 Safari/537.36',
    'x-mf-locale': 'ja',
    'x-vercel-env': 'production',
})

BASE = 'https://api.myfans.jp'

CSV_COLUMNS = [
    'rank', 'rank_term', 'sexual_orientation',
    'username', 'name', 'myfans_url', 'profile_text',
    'followers', 'likes', 'posts', 'last_30d_posts',
    'myfans_latest_post_date', 'myfans_first_post_date',
    'sns_x', 'sns_url_x', 'sns_instagram', 'sns_url_instagram',
    'sns_tiktok', 'sns_url_tiktok', 'sns_others', 'sns_url_others',
    'plan1_price', 'plan1_posts', 'plan2_price', 'plan2_posts',
    'plan3_price', 'plan3_posts', 'plan4_price', 'plan4_posts',
    'plan5_price', 'plan5_posts', 'plan6_price', 'plan6_posts',
    'plan7_price', 'plan7_posts', 'plan8_price', 'plan8_posts',
    'plan9_price', 'plan9_posts',
    'has_free_plan', 'has_trial_period',
]

DELAY = 0.3  # リクエスト間隔(秒)


def api_get(url, params=None):
    """API GET with retry"""
    for attempt in range(3):
        try:
            r = session.get(url, params=params, timeout=15)
            if r.status_code == 200:
                time.sleep(DELAY)
                return r.json()
            elif r.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f'    Rate limited, waiting {wait}s...', flush=True)
                time.sleep(wait)
            else:
                print(f'    HTTP {r.status_code} for {url}', flush=True)
                time.sleep(2)
        except Exception as e:
            print(f'    Request error: {e}, retrying...', flush=True)
            time.sleep(5)
    return None


def fetch_user_detail(rank, username, user_id):
    """1ユーザーの詳細を取得してdict返却"""
    # Profile
    p = api_get(f'{BASE}/api/v2/users/show_by_username', {'username': username})
    if not p:
        return None

    # Plans
    plans_raw = api_get(f'{BASE}/api/v1/users/{user_id}/plans')
    plans = sorted(plans_raw, key=lambda x: x['monthly_price']) if plans_raw else []

    # Posts: latest (page 1) + oldest (estimated last page)
    latest_date = oldest_date = ''
    pr = api_get(f'{BASE}/api/users/{user_id}/posts',
                 {'sort_key': 'publish_start_at', 'page': 1})
    if pr and pr.get('data'):
        latest_date = pr['data'][0].get('published_at', '')
        total_posts = p.get('posts_count', 0) or 0
        if total_posts <= 20:
            oldest_date = pr['data'][-1].get('published_at', '')
        else:
            last_pg = max(1, (total_posts + 19) // 20)
            for try_pg in [last_pg, last_pg - 1, last_pg + 1]:
                if try_pg < 2:
                    continue
                r2 = api_get(f'{BASE}/api/users/{user_id}/posts',
                             {'sort_key': 'publish_start_at', 'page': try_pg})
                if r2 and r2.get('data'):
                    oldest_date = r2['data'][-1].get('published_at', '')
                    break

    ach = (p.get('achievement') or {}).get('plan') or {}

    row = {
        'rank': rank, 'rank_term': 'monthly',
        'sexual_orientation': p.get('creator_sexual_orientation', ''),
        'username': username, 'name': p.get('name', ''),
        'myfans_url': f'https://myfans.jp/{username}',
        'profile_text': (p.get('about') or '').replace('\r\n', ' ').replace('\n', ' '),
        'followers': p.get('followers_count', ''),
        'likes': p.get('likes_count', ''),
        'posts': p.get('posts_count', ''),
        'last_30d_posts': ach.get('posts_count_last_month', ''),
        'myfans_latest_post_date': latest_date[:10] if latest_date else '',
        'myfans_first_post_date': oldest_date[:10] if oldest_date else '',
        'sns_x': 1 if p.get('link_twitter_url') else 0,
        'sns_url_x': p.get('link_twitter_url') or '',
        'sns_instagram': 1 if p.get('link_instagram_url') else 0,
        'sns_url_instagram': p.get('link_instagram_url') or '',
        'sns_tiktok': 1 if p.get('link_tiktok_url') else 0,
        'sns_url_tiktok': p.get('link_tiktok_url') or '',
        'sns_others': 1 if (p.get('link_youtube_url') or p.get('sns_link1') or p.get('sns_link2')) else 0,
        'sns_url_others': p.get('link_youtube_url') or p.get('sns_link1') or p.get('sns_link2') or '',
    }
    for i in range(9):
        if i < len(plans):
            row[f'plan{i+1}_price'] = plans[i]['monthly_price']
            row[f'plan{i+1}_posts'] = plans[i]['posts_count']
        else:
            row[f'plan{i+1}_price'] = ''
            row[f'plan{i+1}_posts'] = ''
    row['has_free_plan'] = 1 if any(pl['monthly_price'] == 0 for pl in plans) else 0
    row['has_trial_period'] = 1 if any(pl.get('active_discount') for pl in plans) else 0
    return row


def main():
    import sys
    start_page = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end_page = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    os.makedirs('output', exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    outpath = f'output/api_monthly_{ts}.csv'

    # CSVファイルをヘッダー付きで作成
    with open(outpath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()

    # 開始ページ前のランク数を計算 (page1=21件, page2以降=20件)
    if start_page == 1:
        global_rank = 0
    else:
        global_rank = 21 + (start_page - 2) * 20

    total_ok = 0
    total_err = 0
    start = time.time()

    print(f'Fetching pages {start_page} to {end_page} (rank {global_rank + 1}~)', flush=True)

    for page in range(start_page, end_page + 1):
        # === 1ページ分のランキング取得 ===
        if page == 1:
            params = {'genre_key': 'all', 'sexual_orientation': 'woman',
                      'term': 'monthly', 'page': 1, 'per_page': 21, 'padding': 0}
        else:
            params = {'genre_key': 'all', 'sexual_orientation': 'woman',
                      'term': 'monthly', 'page': page, 'per_page': 20, 'padding': 1}

        ranking_data = api_get(f'{BASE}/api/ranking/creators/all', params)
        if not ranking_data or not ranking_data.get('data'):
            print(f'Page {page}: empty, stopping.', flush=True)
            break

        users = ranking_data['data']
        print(f'\n=== Page {page}: {len(users)} users ===', flush=True)

        # === このページのユーザー詳細を1件ずつ取得 ===
        page_rows = []
        for i, user in enumerate(users):
            global_rank += 1
            username = user['username']
            user_id = user['id']
            print(f'  [{global_rank:4d}] {username}...', end=' ', flush=True)

            try:
                row = fetch_user_detail(global_rank, username, user_id)
                if row:
                    page_rows.append(row)
                    total_ok += 1
                    print(f'{row["name"]} | {row["followers"]} flw', flush=True)
                else:
                    total_err += 1
                    print('SKIP (no data)', flush=True)
            except Exception as e:
                total_err += 1
                print(f'ERROR: {e}', flush=True)

        # === このページ分をCSVに追記 ===
        with open(outpath, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction='ignore')
            writer.writerows(page_rows)

        elapsed = time.time() - start
        rate = global_rank / elapsed if elapsed > 0 else 0
        print(f'  -> Saved page {page} ({len(page_rows)} rows) | '
              f'Total: {total_ok} ok, {total_err} err | '
              f'{rate:.1f} users/sec', flush=True)

        # ページ間で少し待つ
        time.sleep(1)

        # 最終ページチェック
        if ranking_data.get('pagination', {}).get('next') is None:
            print(f'\nReached last page ({page}).', flush=True)
            break

    elapsed = time.time() - start
    print(f'\n=== Complete ===', flush=True)
    print(f'  {total_ok} users saved, {total_err} errors', flush=True)
    print(f'  {elapsed:.0f}sec ({elapsed/max(total_ok,1):.2f}s/user)', flush=True)
    print(f'  Output: {outpath}', flush=True)


if __name__ == '__main__':
    main()
