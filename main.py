"""
MyFans Scraper - メインスクリプト
ランキングからユーザーを収集し、プロフィール + SNS情報をCSVに出力
"""
import csv
import os
import sys
import time
from datetime import datetime

from scraper_myfans import scrape_user_profile
from scraper_x import scrape_x_profile
from scraper_instagram import scrape_instagram_profile
from scraper_tiktok import scrape_tiktok_profile
from scraper_discover import discover_from_rankings, RANKING_URLS

# CSV カラム定義（順序固定）
CSV_COLUMNS = [
    'scraped_at', 'rank', 'rank_as', 'name', 'username', 'myfans_url', 'profile_text',
    'followers', 'likes', 'posts', 'last_30d_posts',
    'myfans_latest_post_date', 'myfans_first_post_date',
    # X
    'sns_x', 'sns_url_x', 'x_followers', 'x_posts',
    'x_last_30d_posts', 'x_latest_post_date', 'x_first_post_date',
    # Instagram
    'sns_instagram', 'sns_url_instagram', 'instagram_followers', 'instagram_posts',
    'instagram_last_30d_posts', 'instagram_latest_post_date', 'instagram_first_post_date',
    'instagram_status',
    # TikTok
    'sns_tiktok', 'sns_url_tiktok', 'tiktok_followers', 'tiktok_posts',
    'tiktok_last_30d_posts', 'tiktok_latest_post_date', 'tiktok_first_post_date',
    # Others
    'sns_others', 'sns_others_name', 'sns_url_others',
    # Plans
    'plan1_price', 'plan1_posts', 'plan2_price', 'plan2_posts',
    'plan3_price', 'plan3_posts', 'plan4_price', 'plan4_posts',
    'plan5_price', 'plan5_posts', 'plan6_price', 'plan6_posts',
    'plan7_price', 'plan7_posts', 'plan8_price', 'plan8_posts',
    'plan9_price', 'plan9_posts',
    # Flags
    'has_free_plan', 'has_trial_period', 'has_update_frequency',
]

VALID_TERMS = set(RANKING_URLS.keys())


def scrape_single_user(username: str) -> dict:
    """1ユーザーの全データを収集"""
    print(f'\n{"="*60}')
    print(f'Scraping: {username}')
    print(f'{"="*60}')

    # 1. MyFansプロフィール
    print(f'  [1/4] MyFans profile...')
    data = scrape_user_profile(username)

    # 2. X (Twitter)
    if data.get('sns_x') == 1 and data.get('sns_url_x'):
        print(f'  [2/4] X profile: {data["sns_url_x"]}')
        x_data = scrape_x_profile(data['sns_url_x'])
        data.update(x_data)
    else:
        print(f'  [2/4] X: skipped (no link)')

    # 3. Instagram
    if data.get('sns_instagram') == 1 and data.get('sns_url_instagram'):
        print(f'  [3/4] Instagram profile: {data["sns_url_instagram"]}')
        ig_data = scrape_instagram_profile(data['sns_url_instagram'])
        data.update(ig_data)
    else:
        print(f'  [3/4] Instagram: skipped (no link)')

    # 4. TikTok
    if data.get('sns_tiktok') == 1 and data.get('sns_url_tiktok'):
        print(f'  [4/4] TikTok profile: {data["sns_url_tiktok"]}')
        tt_data = scrape_tiktok_profile(data['sns_url_tiktok'])
        data.update(tt_data)
    else:
        print(f'  [4/4] TikTok: skipped (no link)')

    print(f'  Done: {data.get("name", "?")} | '
          f'followers={data.get("followers", "?")} | '
          f'posts={data.get("posts", "?")} | '
          f'last_30d={data.get("last_30d_posts", "?")}')

    return data


def write_csv(results: list[dict], output_path: str):
    """結果をCSVに出力"""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction='ignore')
        writer.writeheader()
        for row in results:
            clean_row = {col: row.get(col, '') for col in CSV_COLUMNS}
            writer.writerow(clean_row)
    print(f'\nCSV saved: {output_path}')


def main():
    args = sys.argv[1:]

    if not args:
        print('Usage: python main.py <daily|weekly|monthly|yearly> [件数]')
        print('  例: python main.py daily            # 日間ランキング全件')
        print('  例: python main.py monthly 50        # 月間ランキング上位50件')
        print('  例: python main.py daily weekly 30   # 日間+週間 各上位30件')
        sys.exit(1)

    # 引数パース: ランキング種別と件数を分離
    terms = [a for a in args if a in VALID_TERMS]
    numbers = [a for a in args if a.isdigit()]
    limit = int(numbers[0]) if numbers else None

    if not terms:
        print(f'Error: ランキング種別を指定してください (daily/weekly/monthly/yearly)')
        sys.exit(1)

    print(f'>>> Ranking: {", ".join(terms)}' + (f' (各上位{limit}件)' if limit else ' (全件)'))
    print(f'>>> Starting...')

    # ランキングからユーザーを収集
    entries = discover_from_rankings(terms, limit)

    if not entries:
        print('No users found.')
        sys.exit(1)

    print(f'\n>>> {len(entries)} entries to scrape')

    # 出力先
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f'output/myfans_data_{timestamp}.csv'

    # スクレイピング実行（同一ユーザーのキャッシュで重複回避）
    cache = {}
    results = []
    unique_users = list(dict.fromkeys(e['username'] for e in entries))
    total_users = len(unique_users)

    for idx, entry in enumerate(entries):
        username = entry['username']

        if username not in cache:
            user_idx = unique_users.index(username) + 1
            print(f'\n>>> [{user_idx}/{total_users}] {username}')
            try:
                cache[username] = scrape_single_user(username)
            except Exception as e:
                print(f'  -> FATAL ERROR for {username}: {e}')
                cache[username] = {
                    'username': username,
                    'scraped_at': datetime.now().strftime('%Y-%m-%d'),
                }
            time.sleep(1)

        # キャッシュからデータをコピーし、rank/rank_asを付与
        data = {**cache[username]}
        data['rank'] = entry['rank']
        data['rank_as'] = entry['rank_as']
        results.append(data)

        # 途中経過を保存（5ユーザーごと or 最後）
        if (idx + 1) % 5 == 0 or idx == len(entries) - 1:
            write_csv(results, output_path)
            print(f'  -> Progress saved ({idx+1}/{len(entries)} entries)')

    # 最終保存
    write_csv(results, output_path)
    print(f'\n=== Complete: {len(results)} entries ({total_users} unique users) ===')
    print(f'Output: {output_path}')


if __name__ == '__main__':
    main()
