"""
MyFans Scraper - メインスクリプト
ランキングからユーザーを収集し、プロフィール + SNS情報をCSVに出力
"""
import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from scraper_discover import scrape_ranking_and_profiles, RANKING_URLS
from scraper_x import scrape_all_x
from scraper_instagram import scrape_all_instagram
from scraper_tiktok import scrape_all_tiktok

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

    # 引数パース
    terms = [a for a in args if a in VALID_TERMS]
    numbers = [a for a in args if a.isdigit()]
    limit = int(numbers[0]) if numbers else None

    if not terms:
        print('Error: ランキング種別を指定してください (daily/weekly/monthly/yearly)')
        sys.exit(1)

    print(f'>>> Ranking: {", ".join(terms)}' + (f' (各上位{limit}件)' if limit else ' (全件)'))

    # 出力先
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f'output/myfans_data_{timestamp}.csv'

    # === Phase 1: ランキング + MyFansプロフィール 一括取得 ===
    print(f'\n{"="*60}')
    print(f'Phase 1: ランキング + MyFansプロフィール')
    print(f'{"="*60}')
    entries = scrape_ranking_and_profiles(terms, limit)

    if not entries:
        print('No users found.')
        sys.exit(1)

    # 途中CSV保存
    write_csv(entries, output_path)
    print(f'  -> Phase 1 complete ({len(entries)} entries), CSV saved')

    # === Phase 2: X / Instagram / TikTok 並列取得 ===
    x_urls = []
    x_url_to_idx = {}
    ig_urls = []
    ig_url_to_idx = {}
    tiktok_urls = []
    tiktok_url_to_idx = {}

    for idx, entry in enumerate(entries):
        if entry.get('sns_x') == 1 and entry.get('sns_url_x'):
            url = entry['sns_url_x']
            if url not in x_url_to_idx:
                x_urls.append(url)
                x_url_to_idx[url] = []
            x_url_to_idx[url].append(idx)
        if entry.get('sns_instagram') == 1 and entry.get('sns_url_instagram'):
            url = entry['sns_url_instagram']
            if url not in ig_url_to_idx:
                ig_urls.append(url)
                ig_url_to_idx[url] = []
            ig_url_to_idx[url].append(idx)
        if entry.get('sns_tiktok') == 1 and entry.get('sns_url_tiktok'):
            url = entry['sns_url_tiktok']
            if url not in tiktok_url_to_idx:
                tiktok_urls.append(url)
                tiktok_url_to_idx[url] = []
            tiktok_url_to_idx[url].append(idx)

    print(f'\n{"="*60}')
    print(f'Phase 2: SNS プロフィール（並列実行）')
    print(f'  X: {len(x_urls)} / Instagram: {len(ig_urls)} / TikTok: {len(tiktok_urls)}')
    print(f'{"="*60}')

    sns_tasks = []
    if x_urls:
        sns_tasks.append(('X', scrape_all_x, x_urls, x_url_to_idx))
    if ig_urls:
        sns_tasks.append(('Instagram', scrape_all_instagram, ig_urls, ig_url_to_idx))
    if tiktok_urls:
        sns_tasks.append(('TikTok', scrape_all_tiktok, tiktok_urls, tiktok_url_to_idx))

    if sns_tasks:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            for name, func, urls, url_map in sns_tasks:
                futures[executor.submit(func, urls)] = (name, url_map)

            for future in as_completed(futures):
                name, url_map = futures[future]
                try:
                    sns_results = future.result()
                    for url, sns_data in sns_results.items():
                        for idx in url_map.get(url, []):
                            entries[idx].update(sns_data)
                    print(f'  -> {name} complete ({len(sns_results)} results)')
                except Exception as e:
                    print(f'  -> {name} failed: {e}')
    else:
        print('  -> No SNS links found, skipping')

    # === 最終CSV出力 ===
    write_csv(entries, output_path)
    unique_users = len(set(e['username'] for e in entries))
    print(f'\n=== Complete: {len(entries)} entries ({unique_users} unique users) ===')
    print(f'Output: {output_path}')


if __name__ == '__main__':
    main()
