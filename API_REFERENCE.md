# MyFans API リファレンス

MyFans の内部 API をリバースエンジニアリングして特定したエンドポイント一覧。
フロントエンド (`myfans.jp`) とバックエンド (`api.myfans.jp`) 間の通信をキャプチャして文書化したもの。

> **調査日**: 2026-03-26
> **ベース URL**: `https://api.myfans.jp`

---

## 認証

### 必須ヘッダー

すべてのリクエストに以下のヘッダーが必要。

```
authorization: Token token=<JWT>
google-ga-data: event328
origin: https://myfans.jp
referer: https://myfans.jp/
accept: application/json, text/plain, */*
accept-language: ja-JP
sec-ch-ua: "Chromium";v="145", "Not:A-Brand";v="99"
sec-ch-ua-mobile: ?0
sec-ch-ua-platform: "macOS"
user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36
x-mf-locale: ja
x-vercel-env: production
```

### JWT トークン

- Cookie `_mfans_token` に格納されている JWT をそのまま `authorization` ヘッダーに使用する
- 形式: `Token token=<JWT>`
- JWT ペイロード例: `{ "user_id": "7a2000c1-...", "exp": 2089391641 }` (有効期限が非常に長い)

### WAF 保護

- AWS ELB (awselb/2.0) によるWAFが有効
- `google-ga-data: event328` ヘッダーが無いと **403 Forbidden** が返る
- `origin` / `referer` / `sec-ch-ua` 系ヘッダーも必要

---

## 共通仕様

### ページネーション

リスト系エンドポイントは以下の形式のページネーションを返す。

```json
{
  "data": [ ... ],
  "pagination": {
    "current": 1,
    "next": 2,
    "previous": null
  }
}
```

- `pagination.next` が `null` の場合、最終ページ
- `pagination.previous` が `null` の場合、先頭ページ

### ID 形式

ユーザーID・プランID 等はすべて UUID v4 形式。
例: `286cfa16-98e5-419b-bb8d-6282ee0e0475`

---

## エンドポイント一覧

| # | メソッド | パス | 説明 |
|---|---------|------|------|
| 1 | GET | `/api/ranking/creators/all` | クリエイターランキング |
| 2 | GET | `/api/v2/users/show_by_username` | ユーザープロフィール (username指定) |
| 3 | GET | `/api/v1/users/{user_id}/plans` | プラン一覧 |
| 4 | GET | `/api/users/{user_id}/posts` | 投稿一覧 |
| 5 | GET | `/api/users/{user_id}/ranking_orders` | ランキング順位 (ジャンル別) |
| 6 | GET | `/api/v1/users/{user_id}` | ユーザープロフィール (ID指定) |

---

## 1. クリエイターランキング

ランキングページに表示されるクリエイター一覧を取得する。

### リクエスト

```
GET /api/ranking/creators/all
```

### パラメータ

| パラメータ | 型 | 必須 | 説明 | 値の例 |
|---|---|---|---|---|
| `term` | string | Yes | ランキング期間 | `daily`, `weekly`, `monthly`, `yearly` |
| `genre_key` | string | Yes | ジャンル | `all`, `f-amateur`, `f-secret-account`, `f-home-video` 等 |
| `sexual_orientation` | string | Yes | カテゴリ | `general`, `woman` |
| `page` | integer | Yes | ページ番号 (1始まり) | `1` |
| `per_page` | integer | Yes | 1ページあたりの件数 | `21` (デフォルト) |
| `padding` | integer | Yes | オフセット | `0` |

### レスポンス

```json
{
  "data": [
    {
      "id": "286cfa16-98e5-419b-bb8d-6282ee0e0475",
      "username": "natsumikan",
      "name": "なつみ",
      "about": "趣味:ダイエット...",
      "avatar_url": "https://content.mfcdn.jp/...",
      "banner_url": "https://content.mfcdn.jp/...",
      "followers_count": 194,
      "likes_count": 497,
      "is_official": false,
      "is_following": false,
      "has_approved_user_identification": true,
      "can_display_premium_badge": true,
      "can_create_coupon": true,
      "can_use_dashboard": true,
      "recommended_plan": {
        "id": "39579995-...",
        "product_name": "なつみのひみつるーむ",
        "monthly_price": 2000,
        "posts_count": 17,
        "flag": "recommended",
        "is_single": true,
        "is_back_number": false,
        "status": "initialize",
        "description": "月額1,800円で...",
        "active_discount": null,
        "active_plan_bundles": [
          {
            "id": "a50c741d-...",
            "duration_months": 6,
            "price": 10800,
            "monthly_price": 1800,
            "discount_rate": 10,
            "is_recommended": true,
            "display_price": 10800
          }
        ],
        "user": {
          "id": "286cfa16-...",
          "username": "natsumikan",
          "name": "なつみ",
          "creator_sexual_orientation": "general"
        }
      }
    }
  ],
  "pagination": {
    "current": 1,
    "next": 2,
    "previous": null
  }
}
```

### フィールド説明

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | string (UUID) | ユーザーID |
| `username` | string | ユーザー名 (URLスラッグ) |
| `name` | string | 表示名 |
| `about` | string | プロフィール文 |
| `followers_count` | integer | フォロワー数 |
| `likes_count` | integer | いいね数 |
| `is_official` | boolean | 公式アカウントか |
| `has_approved_user_identification` | boolean | 本人確認済みか |
| `recommended_plan` | object / null | おすすめプラン (無い場合は `null` またはキー自体が無い) |
| `recommended_plan.monthly_price` | integer | 月額料金 (円) |
| `recommended_plan.posts_count` | integer | プラン内の投稿数 |
| `recommended_plan.active_discount` | object / null | 適用中の割引 |
| `recommended_plan.active_discount.discount_rate` | integer | 割引率 (%) |
| `recommended_plan.active_plan_bundles` | array | 複数月バンドル |

### 備考

- `per_page=21` がフロントエンドのデフォルト値
- 最終ページは 21 件未満になる (例: 47 件のランキングなら page 3 で 5 件)
- `sexual_orientation=general` は一般、`woman` は女性カテゴリ
- ランキング内の **順序 = 配列のインデックス順** (rank フィールドは無い)

---

## 2. ユーザープロフィール (username 指定)

最も情報量が豊富なエンドポイント。SNS リンク・実績情報を含む。

### リクエスト

```
GET /api/v2/users/show_by_username?username={username}
```

### パラメータ

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `username` | string | Yes | ユーザー名 |

### レスポンス

```json
{
  "id": "286cfa16-98e5-419b-bb8d-6282ee0e0475",
  "username": "natsumikan",
  "name": "なつみ",
  "about": "趣味:ダイエット...",
  "active": true,
  "avatar_url": "https://content.mfcdn.jp/...",
  "banner_url": "https://content.mfcdn.jp/...",
  "followers_count": 194,
  "followings_count": 0,
  "likes_count": 497,
  "posts_count": 43,
  "post_images_count": 12,
  "post_videos_count": 31,
  "is_official": false,
  "is_following": false,
  "is_followed": false,
  "is_blocking": false,
  "is_subscribed": false,
  "has_ranking": true,
  "hidden_ranking_order": false,
  "has_approved_user_identification": true,
  "can_display_premium_badge": true,
  "can_create_coupon": true,
  "can_use_dashboard": true,
  "label": null,
  "genre_keys": [],
  "creator_sexual_orientation": "general",

  "link_twitter_id": "natsumi11723",
  "link_twitter_url": "https://twitter.com/natsumi11723",
  "link_instagram_id": "",
  "link_instagram_url": null,
  "link_tiktok_id": "natsunatsumi723",
  "link_tiktok_url": "https://www.tiktok.com/@natsunatsumi723",
  "link_youtube_url": "",
  "sns_link1": "",
  "sns_link2": "",

  "achievement": {
    "plan": {
      "posts_count_last_month": 43
    },
    "recommended_plan": {
      "plan_cost": 2000,
      "plan_cost_per_content": 117
    }
  },

  "back_number_post_images_count": 0,
  "back_number_post_videos_count": 0,
  "cant_receive_message": false,
  "current_back_number_plan": null,
  "is_bought_back_number": false,
  "is_single_month_back_number": false,
  "single_month_back_number_amount": null,
  "show_tip_button": true,
  "short_url": null,
  "has_gachas": false
}
```

### フィールド説明

#### 基本情報

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | string (UUID) | ユーザーID (他APIで `{user_id}` として使用) |
| `username` | string | ユーザー名 |
| `name` | string | 表示名 |
| `about` | string | プロフィール文 |
| `active` | boolean | アカウントがアクティブか |
| `followers_count` | integer | フォロワー数 |
| `followings_count` | integer | フォロー数 |
| `likes_count` | integer | いいね数 |
| `posts_count` | integer | 総投稿数 |
| `post_images_count` | integer | 画像投稿数 |
| `post_videos_count` | integer | 動画投稿数 |
| `creator_sexual_orientation` | string | クリエイターカテゴリ (`general`, `woman`) |

#### SNS リンク

| フィールド | 型 | 説明 |
|---|---|---|
| `link_twitter_id` | string | X (Twitter) ユーザーID |
| `link_twitter_url` | string / null | X プロフィール URL |
| `link_instagram_id` | string | Instagram ユーザーID |
| `link_instagram_url` | string / null | Instagram プロフィール URL |
| `link_tiktok_id` | string | TikTok ユーザーID |
| `link_tiktok_url` | string / null | TikTok プロフィール URL |
| `link_youtube_url` | string | YouTube URL |
| `sns_link1` | string | その他 SNS リンク 1 (lit.link, linktr.ee 等) |
| `sns_link2` | string | その他 SNS リンク 2 |

#### 実績 (achievement)

| フィールド | 型 | 説明 |
|---|---|---|
| `achievement.plan.posts_count_last_month` | integer | **先月の投稿数** |
| `achievement.recommended_plan.plan_cost` | integer | おすすめプラン月額 (円) |
| `achievement.recommended_plan.plan_cost_per_content` | integer | 1コンテンツあたり単価 (円) |

### 備考

- SNS URL が未設定の場合、`null` または空文字列 `""` が返る (フィールドにより異なる)
- `link_twitter_url` は `twitter.com` ドメインのまま (`x.com` ではない)
- `achievement` はクリエイターでないユーザーには無い可能性がある

---

## 3. プラン一覧

ユーザーが公開しているサブスクリプションプランの一覧を取得する。

### リクエスト

```
GET /api/v1/users/{user_id}/plans
```

### パスパラメータ

| パラメータ | 型 | 説明 |
|---|---|---|
| `user_id` | string (UUID) | ユーザーID (プロフィールAPIの `id` フィールド) |

### レスポンス

配列形式 (ページネーション無し)。

```json
[
  {
    "id": "39579995-5e6f-47e8-92ed-fd9c9b265e2b",
    "product_name": "なつみのひみつるーむ",
    "monthly_price": 2000,
    "posts_count": 17,
    "status": "initialize",
    "flag": "recommended",
    "description": "月額1,800円で...",
    "is_single": true,
    "is_back_number": false,
    "is_limited_access": false,
    "disallow_new_subscriber": false,
    "is_unlimited": false,
    "welcome_message": "",
    "active_discount": null,
    "active_plan_bundles": [
      {
        "id": "a50c741d-...",
        "duration_months": 6,
        "price": 10800,
        "monthly_price": 1800,
        "discount_rate": 10,
        "is_recommended": true,
        "display_price": 10800
      },
      {
        "id": "77f84216-...",
        "duration_months": 3,
        "price": 5700,
        "monthly_price": 1900,
        "discount_rate": 5,
        "is_recommended": false,
        "display_price": 5700
      },
      {
        "id": "050d40b1-...",
        "duration_months": 12,
        "price": 20400,
        "monthly_price": 1700,
        "discount_rate": 15,
        "is_recommended": false,
        "display_price": 20400
      }
    ],
    "plan_discounts": null,
    "applying_discount": null,
    "applying_coupon": null,
    "cdb": null,
    "is_unlimited_ch_private": false
  }
]
```

### フィールド説明

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | string (UUID) | プランID |
| `product_name` | string | プラン名 |
| `monthly_price` | integer | 月額料金 (円) |
| `posts_count` | integer | プラン内投稿数 |
| `flag` | string / null | `"recommended"` = おすすめプラン |
| `description` | string | プラン説明文 |
| `is_single` | boolean | 単体プランか |
| `is_back_number` | boolean | バックナンバープランか |
| `is_limited_access` | boolean | 限定アクセスプランか |
| `disallow_new_subscriber` | boolean | 新規加入停止中か |
| `active_discount` | object / null | 適用中の割引 |
| `active_discount.discount_rate` | integer | 割引率 (%) |
| `active_plan_bundles` | array | 複数月バンドルプラン |
| `active_plan_bundles[].duration_months` | integer | バンドル期間 (月) |
| `active_plan_bundles[].price` | integer | バンドル総額 (円) |
| `active_plan_bundles[].monthly_price` | integer | バンドル月額換算 (円) |
| `active_plan_bundles[].discount_rate` | integer | バンドル割引率 (%) |

### 備考

- 配列の順序は不定 (料金順ではない)
- プランが 0 件のユーザーは空配列 `[]` が返る
- `monthly_price: 0` のプラン = 無料プラン

---

## 4. 投稿一覧

ユーザーの投稿一覧をページネーション付きで取得する。

### リクエスト

```
GET /api/users/{user_id}/posts
```

### パラメータ

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `user_id` (パス) | string (UUID) | Yes | ユーザーID |
| `sort_key` | string | No | ソートキー: `publish_start_at` (デフォルト: 新しい順) |
| `page` | integer | No | ページ番号 (1始まり、デフォルト: 1) |

### レスポンス

```json
{
  "data": [
    {
      "id": "25c3de57-83c0-4914-8961-0c9a41036a9e",
      "kind": "video",
      "status": "approved",
      "status_label": "publishing",
      "body": "みんなお昼なにたべたー？？",
      "published_at": "2026-03-25T11:28:56+09:00",
      "humanized_publish_start_at": "03/25 11:28",
      "likes_count": 1,
      "bookmarks_count": 0,
      "view_count": 26,
      "bookmarked": false,
      "liked": false,
      "visible": true,
      "free": true,
      "limited": false,
      "available": true,
      "pinned_at": null,
      "publish_end_at": null,
      "publish_start_at": null,
      "deleted_at_i18n": null,
      "attachment": null,
      "video_processing": false,
      "video_duration": {
        "hours": null,
        "minutes": "00",
        "seconds": "11"
      },
      "metadata": {
        "video": {
          "duration": 11133,
          "resolutions": ["sd", "hd"]
        }
      },
      "thumbnail_url": "https://content.mfcdn.jp/...",
      "affiliate_status": "off",
      "plan": null,
      "current_single_plan": null,
      "plans": [],
      "user": { "..." : "..." },
      "post_images": [ { "..." : "..." } ]
    }
  ],
  "pagination": {
    "current": 1,
    "next": 2,
    "previous": null
  }
}
```

### フィールド説明

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | string (UUID) | 投稿ID |
| `kind` | string | 投稿種別: `video`, `image`, `text` |
| `status` | string | ステータス: `approved` |
| `body` | string | 投稿本文 |
| `published_at` | string (ISO 8601) | **公開日時** (タイムゾーン付き) |
| `humanized_publish_start_at` | string | 公開日時 (人間可読形式: `MM/DD HH:mm`) |
| `likes_count` | integer | いいね数 |
| `bookmarks_count` | integer | ブックマーク数 |
| `view_count` | integer | 閲覧数 |
| `free` | boolean | 無料投稿か |
| `limited` | boolean | 期間限定か |
| `available` | boolean | 現在閲覧可能か |
| `visible` | boolean | 表示されているか |
| `video_duration` | object / null | 動画の長さ (hours/minutes/seconds) |
| `metadata.video.duration` | integer | 動画の長さ (ミリ秒) |
| `plan` | object / null | 紐付きプラン |
| `current_single_plan` | object / null | 単品販売プラン |
| `current_single_plan.amount` | integer | 単品価格 (円) |
| `plans` | array | 閲覧可能なプラン一覧 |
| `thumbnail_url` | string | サムネイル画像 URL |

### 備考

- 1ページあたり **20 件** が返る
- ソート順は **新しい順** 固定 (`sort_order=asc` 等のパラメータは効かない)
- 最古の投稿日を得るには、**最終ページの最後のアイテム** を参照する
- `pagination.next == null` で最終ページを検出可能

### 最古投稿の取得パターン

```python
# ページを順に辿って最終ページを見つける
page = 1
while True:
    r = session.get(f'/api/users/{user_id}/posts', params={
        'sort_key': 'publish_start_at', 'page': page
    })
    data = r.json()
    if data['pagination']['next'] is None:
        oldest_post = data['data'][-1]
        oldest_date = oldest_post['published_at']
        break
    page = data['pagination']['next']
```

---

## 5. ランキング順位 (ジャンル別)

特定ユーザーのジャンル別ランキング順位を取得する。

### リクエスト

```
GET /api/users/{user_id}/ranking_orders
```

### パラメータ

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `user_id` (パス) | string (UUID) | Yes | ユーザーID |
| `term` | string | Yes | 期間: `daily`, `weekly`, `monthly`, `yearly` |

### レスポンス

配列形式。

```json
[
  {
    "genre_key": "all",
    "rank_number": 1
  },
  {
    "genre_key": "g-soft",
    "rank_number": 1
  },
  {
    "genre_key": "g-glamorous",
    "rank_number": 1
  }
]
```

### フィールド説明

| フィールド | 型 | 説明 |
|---|---|---|
| `genre_key` | string / null | ジャンルキー (`all` = 総合) |
| `rank_number` | integer / null | 順位 |

### 備考

- ランキング圏外のジャンルは配列に含まれない
- `genre_key` が `null` / `rank_number` が `null` のエントリが含まれることがある (無視してよい)

---

## 6. ユーザープロフィール (ID 指定)

エンドポイント 2 とほぼ同じだが、ID で直接指定する。

### リクエスト

```
GET /api/v1/users/{user_id}
```

### レスポンス

エンドポイント 2 (show_by_username) と同一フォーマット。
ただし `creator_sexual_orientation` フィールドが無い場合がある。

---

## CSV カラムとの対応表

現在のスクレイパーが出力する CSV カラムと、API フィールドの対応。

| CSV カラム | API エンドポイント | API フィールド |
|---|---|---|
| `name` | #2 profile | `name` |
| `username` | #2 profile | `username` |
| `myfans_url` | - | `https://myfans.jp/{username}` (構築) |
| `profile_text` | #2 profile | `about` |
| `followers` | #2 profile | `followers_count` |
| `likes` | #2 profile | `likes_count` |
| `posts` | #2 profile | `posts_count` |
| `last_30d_posts` | #2 profile | `achievement.plan.posts_count_last_month` |
| `myfans_latest_post_date` | #4 posts | `data[0].published_at` (page 1) |
| `myfans_first_post_date` | #4 posts | 最終ページ `data[-1].published_at` |
| `rank` | #1 ranking | 配列インデックス + (page - 1) * per_page |
| `sns_x` / `sns_url_x` | #2 profile | `link_twitter_url` |
| `sns_instagram` / `sns_url_instagram` | #2 profile | `link_instagram_url` |
| `sns_tiktok` / `sns_url_tiktok` | #2 profile | `link_tiktok_url` |
| `sns_others` / `sns_url_others` | #2 profile | `link_youtube_url`, `sns_link1`, `sns_link2` |
| `planN_price` | #3 plans | `[N-1].monthly_price` (金額昇順ソート後) |
| `planN_posts` | #3 plans | `[N-1].posts_count` |
| `has_free_plan` | #3 plans | `any(p.monthly_price == 0)` |
| `has_trial_period` | #3 plans | `any(p.active_discount is not None)` |

---

## 速度比較

| 処理 | DOM スクレイピング | API 直接呼び出し |
|---|---|---|
| ランキング全件 (47件) | ブラウザ5並列 × ページ遷移 (~2分) | HTTP 3リクエスト (~1秒) |
| プロフィール1件 | ブラウザ操作 (~30秒) | HTTP 1リクエスト (~0.5秒) |
| プラン1件 | DOM解析 (プロフィールに含む) | HTTP 1リクエスト (~0.3秒) |
| 投稿日付1件 | スワイプビュースクロール (~20秒) | HTTP 2リクエスト (~0.5秒) |
| **合計 (100ユーザー)** | **~1時間** | **~3分** |

---

## サンプル実装 (Python)

```python
import json
import requests

# セッション構築
def create_session(cookies_path='cookies/myfans.json'):
    with open(cookies_path) as f:
        cookie_list = json.load(f)

    session = requests.Session()
    for c in cookie_list:
        session.cookies.set(
            c['name'], c['value'],
            domain=c.get('domain', '').lstrip('.'),
            path=c.get('path', '/')
        )

    # _mfans_token から authorization ヘッダーを構築
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
    return session


BASE = 'https://api.myfans.jp'


# ランキング全件取得
def get_ranking(session, term='daily'):
    users = []
    page = 1
    while True:
        r = session.get(f'{BASE}/api/ranking/creators/all', params={
            'genre_key': 'all',
            'sexual_orientation': 'general',
            'term': term,
            'page': page,
            'per_page': 21,
            'padding': 0,
        })
        data = r.json()
        users.extend(data['data'])
        if data['pagination']['next'] is None:
            break
        page = data['pagination']['next']
    return users


# ユーザープロフィール取得
def get_profile(session, username):
    r = session.get(f'{BASE}/api/v2/users/show_by_username',
                    params={'username': username})
    return r.json()


# プラン一覧取得
def get_plans(session, user_id):
    r = session.get(f'{BASE}/api/v1/users/{user_id}/plans')
    return r.json()


# 最新投稿日・最古投稿日を取得
def get_post_dates(session, user_id):
    # 最新 (page 1)
    r = session.get(f'{BASE}/api/users/{user_id}/posts',
                    params={'sort_key': 'publish_start_at', 'page': 1})
    data = r.json()
    if not data.get('data'):
        return None, None

    latest = data['data'][0]['published_at']

    # 最古 (最終ページ)
    while data['pagination']['next'] is not None:
        r = session.get(f'{BASE}/api/users/{user_id}/posts',
                        params={'sort_key': 'publish_start_at',
                                'page': data['pagination']['next']})
        data = r.json()

    oldest = data['data'][-1]['published_at'] if data.get('data') else latest
    return latest, oldest
```
