"""
CSVのInstagram URLからプロフィール・投稿情報を取得してCSVを更新する

Usage:
  python3 -u enrich_instagram.py <csv_path>

追加カラム:
  ig_user_id, ig_full_name, ig_media_count, ig_follower_count,
  ig_following_count, ig_is_private
"""

import csv
import json
import sys
import re
import time
import requests
from datetime import datetime, timezone

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

IG_COLUMNS = [
    "ig_user_id", "ig_full_name", "ig_media_count", "ig_follower_count",
    "ig_following_count", "ig_is_private", "ig_is_joined_recently", "ig_latest_post_date",
]


def get_session() -> requests.Session:
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


def extract_username(url: str) -> str:
    """Instagram URLからユーザー名を抽出"""
    url = url.strip().rstrip("/")
    m = re.search(r'instagram\.com/([^/?#]+)', url)
    return m.group(1) if m else ""


def get_profile_info(session: requests.Session, username: str) -> dict | None:
    """プロフィール情報を取得"""
    url = f"{BASE_URL}/api/v1/users/web_profile_info/"
    for attempt in range(3):
        try:
            resp = session.get(url, params={"username": username}, timeout=15)
            if resp.status_code == 200:
                user = resp.json().get("data", {}).get("user", {})
                return user if user else None
            elif resp.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...", flush=True)
                time.sleep(wait)
            else:
                print(f"    HTTP {resp.status_code}", flush=True)
                return None
        except Exception as e:
            print(f"    Error: {e}", flush=True)
            time.sleep(5)
    return None


def get_latest_post_date(session: requests.Session, user_id: str) -> str:
    """投稿の1ページ目だけ取得して最新投稿日を返す"""
    url = f"{BASE_URL}/api/v1/feed/user/{user_id}/"
    try:
        resp = session.get(url, params={"count": 1}, timeout=15)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            if items:
                taken_at = items[0].get("taken_at")
                if taken_at:
                    return datetime.fromtimestamp(taken_at, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        pass
    return ""


def fetch_ig_data(session: requests.Session, ig_username: str) -> dict:
    """1ユーザー分のIG情報を取得（プロフィール+最新投稿日）"""
    empty = {col: "" for col in IG_COLUMNS}

    user = get_profile_info(session, ig_username)
    if not user:
        return empty

    user_id = user.get("id", "")
    is_private = user.get("is_private", False)
    media_count = user.get("edge_owner_to_timeline_media", {}).get("count", 0)

    latest_date = ""
    if not is_private and media_count > 0 and user_id:
        latest_date = get_latest_post_date(session, user_id)

    return {
        "ig_user_id": ig_username,
        "ig_full_name": user.get("full_name", ""),
        "ig_media_count": media_count,
        "ig_follower_count": user.get("edge_followed_by", {}).get("count", 0),
        "ig_following_count": user.get("edge_follow", {}).get("count", 0),
        "ig_is_private": 1 if is_private else 0,
        "ig_is_joined_recently": 1 if user.get("is_joined_recently", False) else 0,
        "ig_latest_post_date": latest_date,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -u enrich_instagram.py <csv_path>", flush=True)
        sys.exit(1)

    csv_path = sys.argv[1]

    # CSV読み込み
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        original_columns = reader.fieldnames
        rows = list(reader)

    # 新しいカラム追加
    out_columns = list(original_columns) + IG_COLUMNS

    session = get_session()

    total = len(rows)
    ig_targets = [(i, r) for i, r in enumerate(rows) if r.get("sns_url_instagram", "").strip()]
    print(f"CSV: {total}行, Instagram URL あり: {len(ig_targets)}行\n", flush=True)

    for idx, (i, row) in enumerate(ig_targets):
        ig_url = row["sns_url_instagram"].strip()
        ig_username = extract_username(ig_url)

        if not ig_username:
            print(f"[{idx+1}/{len(ig_targets)}] #{row['rank']} {row['username']} - IG URL parse failed: {ig_url}", flush=True)
            for col in IG_COLUMNS:
                rows[i][col] = ""
            continue

        print(f"[{idx+1}/{len(ig_targets)}] #{row['rank']} {row['username']} -> @{ig_username}...", end=" ", flush=True)

        ig_data = fetch_ig_data(session, ig_username)
        for col in IG_COLUMNS:
            rows[i][col] = ig_data[col]

        if ig_data["ig_user_id"]:
            print(f"OK | {ig_data['ig_full_name']} | {ig_data['ig_follower_count']} flw | {ig_data['ig_media_count']} posts", flush=True)
        else:
            print("SKIP (not found)", flush=True)

        time.sleep(1)

    # IGなしの行にも空カラム追加
    for row in rows:
        for col in IG_COLUMNS:
            row.setdefault(col, "")

    # CSV上書き保存
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=out_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n=== 完了 ===", flush=True)
    print(f"  処理: {len(ig_targets)}件", flush=True)
    print(f"  保存: {csv_path}", flush=True)


if __name__ == "__main__":
    main()
