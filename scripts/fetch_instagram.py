"""
Instagram 内部API スクレイパー
==============================
指定ユーザーの以下を取得:
  - 投稿数 / フォロワー数 / フォロー数
  - 直近1ヶ月の投稿数
  - 最新の投稿日
  - 最古の投稿日（※取得可能な範囲）

使い方:
  python3 -u fetch_instagram.py <username>

Cookie:
  cookies/instagram.json に sessionid, csrftoken を含むCookie配列を配置
"""

import requests
import json
import sys
import time
from datetime import datetime, timedelta, timezone

# ============================================================
# Cookie読み込み
# ============================================================
COOKIE_PATH = "cookies/instagram.json"
IG_APP_ID = "936619743392459"
BASE_URL = "https://www.instagram.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
    "X-IG-App-ID": IG_APP_ID,
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.instagram.com/",
    "Accept": "*/*",
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
}


def get_session() -> requests.Session:
    """cookies/instagram.json から認証済みセッションを作成"""
    with open(COOKIE_PATH) as f:
        cookie_list = json.load(f)

    session = requests.Session()
    session.headers.update(HEADERS)

    csrftoken = None
    for c in cookie_list:
        domain = c.get("domain", "").lstrip(".")
        session.cookies.set(c["name"], c["value"], domain=domain, path=c.get("path", "/"))
        if c["name"] == "csrftoken":
            csrftoken = c["value"]

    if csrftoken:
        session.headers["X-CSRFToken"] = csrftoken

    return session


def get_profile_info(session: requests.Session, username: str) -> dict:
    """プロフィール情報を取得"""
    url = f"{BASE_URL}/api/v1/users/web_profile_info/"
    resp = session.get(url, params={"username": username}, timeout=15)
    resp.raise_for_status()
    user = resp.json().get("data", {}).get("user", {})
    if not user:
        raise ValueError(f"ユーザー '{username}' が見つかりませんでした")
    return user


def get_user_posts(session: requests.Session, user_id: str, max_pages: int = 50) -> list:
    """ユーザーの投稿一覧を取得（ページネーション対応）"""
    all_posts = []
    url = f"{BASE_URL}/api/v1/feed/user/{user_id}/"
    params = {"count": 12}
    max_id = None

    for page in range(max_pages):
        if max_id:
            params["max_id"] = max_id

        try:
            resp = session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            print(f"  [!] HTTPエラー (page {page + 1}): {e}", flush=True)
            break
        except json.JSONDecodeError:
            print(f"  [!] JSONパースエラー (page {page + 1})", flush=True)
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            taken_at = item.get("taken_at")
            if taken_at:
                all_posts.append({
                    "id": item.get("pk"),
                    "taken_at": taken_at,
                    "datetime": datetime.fromtimestamp(taken_at, tz=timezone.utc),
                    "caption": (item.get("caption") or {}).get("text", "")[:80],
                    "media_type": item.get("media_type"),
                })

        more_available = data.get("more_available", False)
        next_max_id = data.get("next_max_id")

        print(f"  ページ {page + 1}: {len(items)}件取得 (累計: {len(all_posts)}件)", flush=True)

        if not more_available or not next_max_id:
            print("  → 全投稿を取得完了", flush=True)
            break

        max_id = next_max_id
        time.sleep(2)

    return all_posts


def analyze_posts(posts: list) -> dict:
    """投稿データを分析"""
    if not posts:
        return {
            "total_fetched": 0,
            "recent_month_count": 0,
            "newest_post": None,
            "oldest_post": None,
        }

    now = datetime.now(timezone.utc)
    one_month_ago = now - timedelta(days=30)

    sorted_posts = sorted(posts, key=lambda x: x["taken_at"], reverse=True)
    recent_posts = [p for p in sorted_posts if p["datetime"] >= one_month_ago]

    newest = sorted_posts[0]
    oldest = sorted_posts[-1]

    return {
        "total_fetched": len(posts),
        "recent_month_count": len(recent_posts),
        "newest_post": {
            "date": newest["datetime"].strftime("%Y-%m-%d %H:%M:%S UTC"),
            "caption": newest["caption"],
        },
        "oldest_post": {
            "date": oldest["datetime"].strftime("%Y-%m-%d %H:%M:%S UTC"),
            "caption": oldest["caption"],
        },
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -u fetch_instagram.py <username>", flush=True)
        sys.exit(1)

    target = sys.argv[1].lstrip("@")

    print("=" * 60)
    print(f"Instagram データ取得: @{target}")
    print("=" * 60)

    session = get_session()

    # Step 1: プロフィール
    print("\n[1/3] プロフィール情報を取得中...", flush=True)
    try:
        user = get_profile_info(session, target)
    except Exception as e:
        print(f"[エラー] プロフィール取得失敗: {e}", flush=True)
        sys.exit(1)

    user_id = user.get("id")
    full_name = user.get("full_name", "")
    media_count = user.get("edge_owner_to_timeline_media", {}).get("count", 0)
    follower_count = user.get("edge_followed_by", {}).get("count", 0)
    following_count = user.get("edge_follow", {}).get("count", 0)
    is_private = user.get("is_private", False)

    print(f"  ユーザー名 : @{target}")
    print(f"  表示名     : {full_name}")
    print(f"  ユーザーID : {user_id}")
    print(f"  投稿数     : {media_count:,}")
    print(f"  フォロワー : {follower_count:,}")
    print(f"  フォロー中 : {following_count:,}")
    print(f"  非公開     : {'はい' if is_private else 'いいえ'}")

    if is_private:
        print("\n[注意] 非公開アカウントのため、投稿一覧は取得できません。", flush=True)
        sys.exit(0)

    # Step 2: 投稿一覧
    print(f"\n[2/3] 投稿一覧を取得中... (最大{media_count:,}件)", flush=True)
    posts = get_user_posts(session, user_id)

    # Step 3: 分析
    print("\n[3/3] データ分析中...", flush=True)
    analysis = analyze_posts(posts)

    # 結果出力
    print("\n" + "=" * 60)
    print("取得結果サマリー")
    print("=" * 60)
    print(f"  投稿数（API）       : {media_count:,}")
    print(f"  フォロワー数        : {follower_count:,}")
    print(f"  フォロー数          : {following_count:,}")
    print(f"  取得できた投稿数    : {analysis['total_fetched']:,}")
    print(f"  直近30日の投稿数    : {analysis['recent_month_count']}")

    if analysis["newest_post"]:
        print(f"  最新の投稿日        : {analysis['newest_post']['date']}")
        print(f"    └ キャプション    : {analysis['newest_post']['caption']}")

    if analysis["oldest_post"]:
        print(f"  最古の投稿日        : {analysis['oldest_post']['date']}")
        print(f"    └ キャプション    : {analysis['oldest_post']['caption']}")

    # JSON保存
    result = {
        "username": target,
        "user_id": user_id,
        "full_name": full_name,
        "media_count": media_count,
        "follower_count": follower_count,
        "following_count": following_count,
        "is_private": is_private,
        "fetched_posts": analysis["total_fetched"],
        "recent_30d_posts": analysis["recent_month_count"],
        "newest_post": analysis["newest_post"],
        "oldest_post": analysis["oldest_post"],
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    import os
    os.makedirs("output", exist_ok=True)
    output_file = f"output/ig_{target}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n結果をJSONに保存しました: {output_file}")


if __name__ == "__main__":
    main()
