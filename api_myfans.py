"""MyFans API クライアント
ブラウザ内のAPIレスポンスをインターセプトしてJSONデータを直接取得
"""
import re
from datetime import datetime
from scrapling import StealthyFetcher
from utils import load_cookies, is_within_30d

API_BASE = 'https://api.myfans.jp/api'

RANKING_URLS = {
    'daily': 'daily',
    'weekly': 'weekly',
    'monthly': 'monthly',
    'yearly': 'yearly',
}


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


def _make_empty_data(username: str) -> dict:
    """空のデータテンプレート"""
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


def _parse_profile_json(profile: dict, data: dict):
    """show_by_username APIのJSONからCSVデータを抽出"""
    data['name'] = profile.get('name', '')
    data['profile_text'] = profile.get('about', '')
    data['followers'] = profile.get('followers_count', '')
    data['likes'] = profile.get('likes_count', '')
    data['posts'] = profile.get('posts_count', '')

    # 先月の投稿数
    achievement = profile.get('achievement') or {}
    plan_ach = achievement.get('plan') or {}
    data['last_30d_posts'] = plan_ach.get('posts_count_last_month', '')

    # SNSリンク
    twitter_url = profile.get('link_twitter_url') or ''
    if twitter_url:
        data['sns_x'] = 1
        data['sns_url_x'] = twitter_url

    instagram_url = profile.get('link_instagram_url') or ''
    if instagram_url:
        data['sns_instagram'] = 1
        data['sns_url_instagram'] = instagram_url

    tiktok_url = profile.get('link_tiktok_url') or ''
    if tiktok_url:
        data['sns_tiktok'] = 1
        data['sns_url_tiktok'] = tiktok_url

    # その他SNS
    sns_link1 = profile.get('sns_link1') or ''
    sns_link2 = profile.get('sns_link2') or ''
    other_link = sns_link1 or sns_link2
    if other_link:
        data['sns_others'] = 1
        if 'youtube.com' in other_link or 'youtu.be' in other_link:
            data['sns_others_name'] = 'youtube'
        elif 'lit.link' in other_link:
            data['sns_others_name'] = 'lit.link'
        elif 'linktr.ee' in other_link:
            data['sns_others_name'] = 'linktree'
        else:
            data['sns_others_name'] = 'other'
        data['sns_url_others'] = other_link


def _parse_plans_json(plans: list, data: dict):
    """plans APIのJSONからプラン情報を抽出"""
    plans.sort(key=lambda p: p.get('monthly_price', 0))
    for idx, plan in enumerate(plans):
        if idx >= 9:
            break
        data[f'plan{idx+1}_price'] = plan.get('monthly_price', '')
        data[f'plan{idx+1}_posts'] = plan.get('posts_count', '')
    if any(p.get('monthly_price', -1) == 0 for p in plans):
        data['has_free_plan'] = 1


def _parse_posts_json(posts: list, data: dict, key: str):
    """posts APIのJSONから投稿日付を抽出"""
    if not posts:
        return
    post = posts[0]
    date_str = post.get('publish_start_at') or post.get('published_at') or ''
    if date_str:
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            data[key] = dt.strftime('%Y-%m-%d')
        except Exception:
            pass


def scrape_ranking_and_profiles(terms: list[str], limit: int | None = None) -> list[dict]:
    """ランキングからユーザーを収集し、プロフィールも一括取得

    1ブラウザでページ遷移し、APIレスポンスをインターセプトしてJSON取得。
    DOM解析不要で高速。
    """
    fetcher = StealthyFetcher()
    cookies = load_cookies('myfans')
    all_entries = []

    def action(page):
        # APIレスポンスを格納する辞書
        api_cache = {}

        def intercept_api(route):
            """APIレスポンスをインターセプトしてキャッシュ"""
            try:
                response = route.fetch()
                url = route.request.url
                if response.status == 200:
                    try:
                        body_text = response.text()
                        if body_text:
                            import json
                            body = json.loads(body_text)
                            api_cache[url] = body
                    except Exception:
                        pass
                route.fulfill(response=response)
            except Exception:
                route.continue_()

        # APIインターセプト設定
        page.route('**/api.myfans.jp/api/**', intercept_api)

        _click_age_gate(page)

        for term in terms:
            if term not in RANKING_URLS:
                continue

            print(f'\n  [{term}] Fetching ranking...')
            ranking_users = []
            page_num = 0

            # ランキング全ページ取得
            while True:
                page_num += 1
                url = f'/ranking/creators/all?term={term}&page={page_num}'
                print(f'  [{term}] Page {page_num}...')

                api_cache.clear()
                page.evaluate(f"window.location.href = '{url}'")
                page.wait_for_timeout(2000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(1000)

                if page_num == 1:
                    _click_age_gate(page)
                    page.wait_for_timeout(2000)
                    page.wait_for_load_state('networkidle')
                    page.wait_for_timeout(1000)

                # ランキングAPIのレスポンスを探す
                page_users = []
                for cached_url, cached_data in api_cache.items():
                    if 'ranking/creators/all' in cached_url and isinstance(cached_data, dict):
                        page_users = cached_data.get('data', [])
                        if page_users:
                            break

                if not page_users:
                    print(f'    [{term}] Page {page_num}: empty, stopping')
                    break

                ranking_users.extend(page_users)
                print(f'    [{term}] +{len(page_users)} users (total: {len(ranking_users)})')

                if limit and len(ranking_users) >= limit:
                    ranking_users = ranking_users[:limit]
                    break

            print(f'  [{term}] {len(ranking_users)} users found, fetching profiles...')

            # 各ユーザーのプロフィールを取得
            for idx, user in enumerate(ranking_users):
                username = user['username']
                user_id = user['id']
                data = _make_empty_data(username)
                data['rank'] = idx + 1
                data['rank_as'] = term

                # ランキングAPIから既に取得済みのデータ
                data['name'] = user.get('name', '')
                data['followers'] = user.get('followers_count', '')
                data['likes'] = user.get('likes_count', '')

                # プロフィールページに遷移してAPIをインターセプト
                api_cache.clear()
                page.evaluate(f"window.location.href = '/{username}'")
                page.wait_for_timeout(2000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(1000)

                # インターセプトしたAPIレスポンスを解析
                for cached_url, cached_data in api_cache.items():
                    if not cached_data:
                        continue
                    try:
                        if 'show_by_username' in cached_url and isinstance(cached_data, dict):
                            _parse_profile_json(cached_data, data)
                            if data['profile_text'] and re.search(r'初月[無料半額]|トライアル|お試し|無料体験', data['profile_text']):
                                data['has_trial_period'] = 1
                        elif f'{user_id}/plans' in cached_url and isinstance(cached_data, list):
                            _parse_plans_json(cached_data, data)
                        elif f'{user_id}/posts' in cached_url and isinstance(cached_data, dict):
                            posts = cached_data.get('data', [])
                            _parse_posts_json(posts, data, 'myfans_latest_post_date')
                    except Exception as e:
                        print(f'      Parse error for {cached_url}: {e}')

                print(f'    [{term}] #{idx+1} {username}: {data["name"]} | {data["followers"]} followers | {data["posts"]} posts')
                all_entries.append(data)

            print(f'  [{term}] Done: {len([e for e in all_entries if e["rank_as"] == term])} users')

    fetcher.fetch(
        'https://myfans.jp',
        headless=True,
        timeout=3600000,
        page_action=action,
        network_idle=True,
        cookies=cookies,
        locale='ja-JP',
    )

    print(f'\n  === Complete: {len(all_entries)} entries ===')
    return all_entries


if __name__ == '__main__':
    import sys
    terms = [a for a in sys.argv[1:] if a in RANKING_URLS]
    numbers = [a for a in sys.argv[1:] if a.isdigit()]
    limit = int(numbers[0]) if numbers else None

    if not terms:
        print('Usage: python api_myfans.py <daily|weekly|monthly|yearly> [件数]')
        sys.exit(1)

    entries = scrape_ranking_and_profiles(terms, limit)
    print(f'\nTotal: {len(entries)} entries')
    for e in entries[:10]:
        print(f'  #{e["rank"]} [{e["rank_as"]}] {e["username"]} - {e.get("name", "?")} | {e.get("followers", "?")} followers')
