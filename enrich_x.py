"""
CSVのX (Twitter) URLからプロフィール情報を取得してCSVを更新する

Usage:
  python3 -u enrich_x.py <csv_path>

追加カラム:
  x_user_id, x_name, x_statuses_count, x_follower_count,
  x_following_count, x_listed_count, x_created_at, x_is_blue_verified,
  x_recent_30d_posts, x_latest_post_date
"""

import csv
import json
import sys
import re
import time
import requests
from datetime import datetime, timedelta, timezone

COOKIE_PATH = "cookies/x.json"

BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json",
    "X-Twitter-Active-User": "yes",
    "X-Twitter-Auth-Type": "OAuth2Session",
    "X-Twitter-Client-Language": "ja",
    "Referer": "https://x.com/",
    "Accept": "*/*",
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
}

FEATURES_USER = {
    "hidden_profile_subscriptions_enabled": True,
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "subscriptions_verification_info_is_identity_verified_enabled": True,
    "subscriptions_verification_info_verified_since_enabled": True,
    "highlights_tweets_tab_ui_enabled": True,
    "responsive_web_twitter_article_notes_tab_enabled": True,
    "subscriptions_feature_can_gift_premium": True,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
}

GRAPHQL_USER_BY_SCREEN_NAME = "xmU6X_CKVnQ5lSrCbAmJsg/UserByScreenName"
GRAPHQL_USER_TWEETS = "E3opETHurmVJflFsUBVuUQ/UserTweets"

FEATURES_TWEETS = {
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}

X_COLUMNS = [
    "x_user_id", "x_name", "x_statuses_count", "x_follower_count",
    "x_following_count", "x_created_at", "x_is_blue_verified",
    "x_latest_post_date",
]


def get_session() -> requests.Session:
    with open(COOKIE_PATH) as f:
        cookie_list = json.load(f)

    session = requests.Session()
    session.headers.update(HEADERS)

    ct0 = None
    for c in cookie_list:
        domain = c.get("domain", "").lstrip(".")
        session.cookies.set(c["name"], c["value"], domain=domain, path=c.get("path", "/"))
        if c["name"] == "ct0":
            ct0 = c["value"]

    if ct0:
        session.headers["X-Csrf-Token"] = ct0

    return session


def extract_username(url: str) -> str:
    """X URLからユーザー名を抽出"""
    url = url.strip().rstrip("/")
    m = re.search(r'(?:twitter\.com|x\.com)/([^/?#]+)', url)
    if m:
        name = m.group(1)
        if name.lower() not in ("home", "explore", "search", "notifications", "messages", "i", "settings"):
            return name
    return ""


def get_user_info(session: requests.Session, username: str) -> dict | None:
    """GraphQL UserByScreenName でプロフィール取得"""
    variables = {
        "screen_name": username,
        "withSafetyModeUserFields": True,
    }
    params = {
        "variables": json.dumps(variables),
        "features": json.dumps(FEATURES_USER),
    }
    url = f"https://x.com/i/api/graphql/{GRAPHQL_USER_BY_SCREEN_NAME}"

    for attempt in range(3):
        try:
            resp = session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                user_result = resp.json().get("data", {}).get("user", {}).get("result", {})
                return user_result if user_result else None
            elif resp.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...", flush=True)
                time.sleep(wait)
            else:
                print(f"    HTTP {resp.status_code}", flush=True)
                return None
        except Exception as e:
            print(f"    Error: {e}", flush=True)
            time.sleep(5)
    return None


def get_recent_tweets(session: requests.Session, user_id: str) -> tuple:
    """直近ツイートを取得し、最新投稿日と30日以内の投稿数を返す。30日超えたら打ち切り。"""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    latest_date = ""
    recent_count = 0
    cursor = None

    for page in range(1):  # 最新投稿日だけなので1ページで十分
        variables = {
            "userId": user_id,
            "count": 20,
            "includePromotedContent": False,
            "withQuickPromoteEligibilityTweetFields": True,
            "withVoice": True,
            "withV2Timeline": True,
        }
        if cursor:
            variables["cursor"] = cursor

        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(FEATURES_TWEETS),
        }
        url = f"https://x.com/i/api/graphql/{GRAPHQL_USER_TWEETS}"

        try:
            resp = session.get(url, params=params, timeout=15)
            if resp.status_code == 429:
                print(f"\n    Tweets: rate limited, waiting 60s...", end="", flush=True)
                time.sleep(60)
                resp = session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                print(f"\n    Tweets: HTTP {resp.status_code}", end="", flush=True)
                break
            data = resp.json()
        except Exception as e:
            print(f"\n    Tweets: error {e}", end="", flush=True)
            break

        # タイムラインからツイートとカーソルを抽出
        timeline = (
            data.get("data", {}).get("user", {}).get("result", {})
            .get("timeline_v2", {}).get("timeline", {})
        )
        if not timeline:
            timeline = data.get("data", {}).get("user", {}).get("result", {}).get("timeline", {})

        instructions = timeline.get("instructions", [])
        found_old = False
        next_cursor = None

        for instruction in instructions:
            entries = []
            if instruction.get("type") == "TimelineAddEntries":
                entries = instruction.get("entries", [])

            for entry in entries:
                entry_id = entry.get("entryId", "")
                if "cursor-bottom" in entry_id:
                    next_cursor = entry.get("content", {}).get("value", "")
                    continue
                if "cursor-top" in entry_id:
                    continue

                # ツイート抽出
                tweet_result = (
                    entry.get("content", {}).get("itemContent", {})
                    .get("tweet_results", {}).get("result", {})
                )
                if not tweet_result:
                    continue
                if tweet_result.get("__typename") == "TweetWithVisibilityResults":
                    tweet_result = tweet_result.get("tweet", {})

                legacy = tweet_result.get("legacy", {})
                created_at_str = legacy.get("created_at", "")
                if not created_at_str:
                    continue

                try:
                    dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
                except ValueError:
                    continue

                if not latest_date:
                    latest_date = dt.strftime("%Y-%m-%d")

                if dt >= cutoff:
                    recent_count += 1
                else:
                    found_old = True
                    break

        if found_old or not next_cursor:
            break

        cursor = next_cursor
        time.sleep(1)

    return latest_date, recent_count


def fetch_x_data(session: requests.Session, x_username: str) -> dict:
    """1ユーザー分のX情報を取得"""
    empty = {col: "" for col in X_COLUMNS}

    user_result = get_user_info(session, x_username)
    if not user_result:
        return empty

    legacy = user_result.get("legacy", {})
    rest_id = user_result.get("rest_id", "")

    result = {
        "x_user_id": x_username,
        "x_name": legacy.get("name", ""),
        "x_statuses_count": legacy.get("statuses_count", 0),
        "x_follower_count": legacy.get("followers_count", 0),
        "x_following_count": legacy.get("friends_count", 0),
        "x_created_at": legacy.get("created_at", ""),
        "x_is_blue_verified": 1 if user_result.get("is_blue_verified", False) else 0,
        "x_latest_post_date": "",
    }

    if rest_id:
        latest, _ = get_recent_tweets(session, rest_id)
        result["x_latest_post_date"] = latest

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -u enrich_x.py <csv_path>", flush=True)
        sys.exit(1)

    csv_path = sys.argv[1]

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        original_columns = reader.fieldnames
        rows = list(reader)

    out_columns = list(original_columns) + X_COLUMNS

    session = get_session()

    total = len(rows)
    x_targets = [(i, r) for i, r in enumerate(rows) if r.get("sns_url_x", "").strip()]
    print(f"CSV: {total}行, X URL あり: {len(x_targets)}行\n", flush=True)

    # 初回: 全行にカラム追加してヘッダー書き込み
    for row in rows:
        for col in X_COLUMNS:
            row.setdefault(col, "")

    for idx, (i, row) in enumerate(x_targets):
        x_url = row["sns_url_x"].strip()
        x_username = extract_username(x_url)

        if not x_username:
            print(f"[{idx+1}/{len(x_targets)}] #{row['rank']} {row['username']} - X URL parse failed: {x_url}", flush=True)
        else:
            print(f"[{idx+1}/{len(x_targets)}] #{row['rank']} {row['username']} -> @{x_username}...", end=" ", flush=True)

            x_data = fetch_x_data(session, x_username)
            for col in X_COLUMNS:
                rows[i][col] = x_data[col]

            if x_data["x_user_id"]:
                print(f"OK | {x_data['x_name']} | {x_data['x_follower_count']} flw | {x_data['x_statuses_count']} tweets", flush=True)
            else:
                print("SKIP (not found)", flush=True)

            time.sleep(1)

        # 1ユーザーごとにCSV保存
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=out_columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    print(f"\n=== 完了 ===", flush=True)
    print(f"  処理: {len(x_targets)}件", flush=True)
    print(f"  保存: {csv_path}", flush=True)


if __name__ == "__main__":
    main()
