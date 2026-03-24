"""
MyFans Scraper - メインスクリプト
ユーザープロフィール + SNS情報を収集してCSVに出力
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
from scraper_ranking import scrape_monthly_creator_ranking
from scraper_discover import discover_usernames

# CSV カラム定義（順序固定）
CSV_COLUMNS = [
    'scraped_at', 'rank', 'name', 'username', 'myfans_url', 'profile_text',
    'followers', 'likes', 'posts', 'last_30d_posts',
    'myfans_latest_post_date', 'myfans_first_post_date',
    # X
    'sns_x', 'sns_url_x', 'x_followers', 'x_posts',
    'x_last_30d_posts', 'x_latest_post_date', 'x_first_post_date',
    # Instagram
    'sns_instagram', 'sns_url_instagram', 'instagram_followers', 'instagram_posts',
    'instagram_last_30d_posts', 'instagram_latest_post_date', 'instagram_first_post_date',
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



def scrape_single_user(username: str, rank: str = '') -> dict:
    """1ユーザーの全データを収集"""
    print(f'\n{"="*60}')
    print(f'Scraping: {username}')
    print(f'{"="*60}')

    # 1. MyFansプロフィール
    print(f'  [1/4] MyFans profile...')
    data = scrape_user_profile(username)
    data['rank'] = rank

    # 2. X (Twitter)
    if data.get('sns_x') == 1 and data.get('sns_url_x'):
        print(f'  [2/4] X profile: {data["sns_url_x"]}')
        x_data = scrape_x_profile(data['sns_url_x'])
        data.update(x_data)
        time.sleep(2)
    else:
        print(f'  [2/4] X: skipped (no link)')

    # 3. Instagram
    if data.get('sns_instagram') == 1 and data.get('sns_url_instagram'):
        print(f'  [3/4] Instagram profile: {data["sns_url_instagram"]}')
        ig_data = scrape_instagram_profile(data['sns_url_instagram'])
        data.update(ig_data)
        time.sleep(2)
    else:
        print(f'  [3/4] Instagram: skipped (no link)')

    # 4. TikTok
    if data.get('sns_tiktok') == 1 and data.get('sns_url_tiktok'):
        print(f'  [4/4] TikTok profile: {data["sns_url_tiktok"]}')
        tt_data = scrape_tiktok_profile(data['sns_url_tiktok'])
        data.update(tt_data)
        time.sleep(2)
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
            # 欠損カラムを空文字で埋める
            clean_row = {col: row.get(col, '') for col in CSV_COLUMNS}
            writer.writerow(clean_row)
    print(f'\nCSV saved: {output_path}')


def main():
    # -n オプションで件数制限（例: python main.py -n 10）
    limit = None
    args = sys.argv[1:]
    if '-n' in args:
        n_idx = args.index('-n')
        limit = int(args[n_idx + 1])
        args = args[:n_idx] + args[n_idx + 2:]

    if args:
        # コマンドライン引数でユーザー名指定
        usernames = args
    else:
        # MyFansサイトからユーザーを自動発見
        print('>>> Discovering users from MyFans...')
        usernames = discover_usernames()
        print(f'Discovered {len(usernames)} unique users')

    if not usernames:
        print('No users found.')
        sys.exit(1)

    # 件数制限
    if limit:
        usernames = usernames[:limit]
        print(f'Limited to first {limit} users')

    ranks = {}

    # 出力先
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f'output/myfans_data_{timestamp}.csv'

    # 月間クリエイターランキングを取得
    print('\n>>> Fetching monthly creator ranking...')
    try:
        ranking = scrape_monthly_creator_ranking()
        print(f'  Ranking: {len(ranking)} creators found')
        # ランキング情報をranksに反映
        for username in usernames:
            if username in ranking:
                ranks[username] = ranking[username]
    except Exception as e:
        print(f'  Ranking fetch failed: {e}')

    # スクレイピング実行
    results = []
    total = len(usernames)
    for idx, username in enumerate(usernames):
        print(f'\n>>> [{idx+1}/{total}] {username}')
        try:
            data = scrape_single_user(username, rank=ranks.get(username, ''))
            results.append(data)

            # 途中経過を保存（クラッシュ対策）
            if (idx + 1) % 5 == 0 or idx == total - 1:
                write_csv(results, output_path)
                print(f'  -> Progress saved ({idx+1}/{total})')

        except Exception as e:
            print(f'  -> FATAL ERROR for {username}: {e}')
            results.append({
                'username': username,
                'scraped_at': datetime.now().strftime('%Y-%m-%d'),
                'rank': ranks.get(username, ''),
            })

        # レート制限対策
        time.sleep(3)

    # 最終保存
    write_csv(results, output_path)
    print(f'\n=== Complete: {len(results)}/{total} users scraped ===')
    print(f'Output: {output_path}')


if __name__ == '__main__':
    main()
