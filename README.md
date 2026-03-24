# MyFans Scraper

MyFansのユーザープロフィール・SNS情報を自動収集し、CSVで出力するスクレイピングシステム。

## 概要

- **対象サイト**: [myfans.jp](https://myfans.jp)
- **使用ライブラリ**: [Scrapling](https://github.com/D4Vinci/Scrapling) (StealthyFetcher)
- **出力形式**: CSV

## サイト構造

### URL パターン

| ページ | URL | 備考 |
|--------|-----|------|
| トップ | `https://myfans.jp` | おすすめジャンル、ピックアップ、クリエイター一覧 |
| ユーザープロフィール | `https://myfans.jp/{username}` | 例: `https://myfans.jp/_072q` |
| ランキング(投稿) | `https://myfans.jp/ranking/posts` | クライアントサイドルーティング |
| ランキング(クリエイター) | `https://myfans.jp/ranking/creators/all?term=daily` | daily/weekly/monthly |
| ランキング(ジャンル別) | `https://myfans.jp/ranking/posts/{genre}?term=daily` | 例: `g-vlog`, `g-model` |
| ジャンル一覧 | `https://myfans.jp/genres` | |
| ジャンル検索 | `https://myfans.jp/s/genres/{genre}` | 例: `g-glamorous`, `g-soft` |
| フィード | `https://myfans.jp/feed` | ログイン必須 |
| 検索 | `https://myfans.jp/s` | |

### ユーザープロフィールページの構造

ユーザーページから取得可能な情報:

- **基本情報**: 表示名、@username、プロフィール文
- **統計**: 投稿数、いいね数(K表記)、フォロワー数(K表記)
- **SNSリンク**: Twitter/X, Instagram, TikTok, YouTube等（SVGアイコン付きaタグ、親div `class="flex gap-3"`）
- **プラン情報**: プラン名、価格、説明文
- **投稿一覧**: タブ切替（投稿 / 単品販売）、投稿日付・再生数等

### 技術的特徴

- **フレームワーク**: Next.js (SSR/SPA)
- **UIライブラリ**: Material-UI (MUI) + Tailwind CSS
- **年齢確認**: 初回アクセス時にダイアログ表示 → 「はい」ボタンクリックで突破
- **ナビゲーション**: 下部ナビはクライアントサイドルーティング（aタグではなくdiv + onClick）

## CSV カラム定義

### 基本情報

| # | カラム名 | 説明 | 例 |
|---|---------|------|-----|
| 1 | `scraped_at` | 取得日 | `2026-03-25` |
| 2 | `rank` | ランキング順位（ランキング外は空欄） | `5` |
| 3 | `name` | 表示名 | `ﾐﾙさん` |
| 4 | `username` | ユーザーID | `_072q` |
| 5 | `myfans_url` | プロフィールURL | `https://myfans.jp/_072q` |
| 6 | `profile_text` | プロフィール文 | `軽率におっぱい報告しちゃう...` |
| 7 | `followers` | フォロワー数 | `111900` |
| 8 | `likes` | いいね数 | `139900` |
| 9 | `posts` | 総投稿数 | `286` |
| 10 | `last_30d_posts` | 直近30日の投稿数（実数カウント） | `18` |
| 11 | `myfans_latest_post_date` | MyFans最新投稿日 | `2026-03-24` |
| 12 | `myfans_first_post_date` | MyFans最古投稿日 | `2024-08-10` |

### SNS - X (Twitter)

| # | カラム名 | 説明 | 例 |
|---|---------|------|-----|
| 13 | `sns_x` | アカウント有無 (0/1) | `1` |
| 14 | `sns_url_x` | URL | `https://twitter.com/_072q` |
| 15 | `x_followers` | フォロワー数 | `492581` |
| 16 | `x_posts` | 投稿数 | `3200` |
| 17 | `x_last_30d_posts` | 直近30日投稿数 | `45` |
| 18 | `x_latest_post_date` | 最新投稿日 | `2026-03-24` |
| 19 | `x_first_post_date` | 最初の投稿日 | `2022-06-15` |

### SNS - Instagram

| # | カラム名 | 説明 | 例 |
|---|---------|------|-----|
| 20 | `sns_instagram` | アカウント有無 (0/1) | `1` |
| 21 | `sns_url_instagram` | URL | `https://www.instagram.com/__072q` |
| 22 | `instagram_followers` | フォロワー数 | `15000` |
| 23 | `instagram_posts` | 投稿数 | `120` |
| 24 | `instagram_last_30d_posts` | 直近30日投稿数 | `8` |
| 25 | `instagram_latest_post_date` | 最新投稿日 | `2026-03-20` |
| 26 | `instagram_first_post_date` | 最初の投稿日 | `2023-01-10` |

### SNS - TikTok

| # | カラム名 | 説明 | 例 |
|---|---------|------|-----|
| 27 | `sns_tiktok` | アカウント有無 (0/1) | `1` |
| 28 | `sns_url_tiktok` | URL | `https://www.tiktok.com/@_57391` |
| 29 | `tiktok_followers` | フォロワー数 | `87400` |
| 30 | `tiktok_posts` | 投稿数 | `55` |
| 31 | `tiktok_last_30d_posts` | 直近30日投稿数 | `3` |
| 32 | `tiktok_latest_post_date` | 最新投稿日 | `2026-03-18` |
| 33 | `tiktok_first_post_date` | 最初の投稿日 | `2023-05-01` |

### SNS - その他

| # | カラム名 | 説明 | 例 |
|---|---------|------|-----|
| 34 | `sns_others` | アカウント有無 (0/1) | `0` |
| 35 | `sns_others_name` | 媒体名 | `youtube` |
| 36 | `sns_url_others` | URL | `https://youtube.com/...` |

### プラン情報（金額昇順）

| # | カラム名 | 説明 | 例 |
|---|---------|------|-----|
| 37 | `plan1_price` | プラン1料金（最安） | `1500` |
| 38 | `plan1_posts` | プラン1投稿数 | `199` |
| 39 | `plan2_price` | プラン2料金 | `5000` |
| 40 | `plan2_posts` | プラン2投稿数 | `256` |
| 41-52 | `plan3~9_price/posts` | 同様（空なら空欄） | |

### フラグ

| # | カラム名 | 説明 | 例 |
|---|---------|------|-----|
| 53 | `has_free_plan` | ¥0プランの有無 (0/1) | `0` |
| 54 | `has_trial_period` | 初月無料/半額等の初回オファー有無 (0/1) | `0` |
| 55 | `has_update_frequency` | 投稿頻度（今回スコープ外・空欄） | |

## 必要な認証情報

| サービス | 必要なもの | 必須度 |
|---------|-----------|--------|
| MyFans | ID/PASS または ログイン後Cookie | **必須** |
| X (Twitter) | ログイン後Cookie | **必須** |
| Instagram | ログイン後Cookie | **必須** |
| TikTok | ログイン後Cookie | 推奨 |

### Cookie の取得方法

1. 各サイトにブラウザでログイン
2. DevTools (F12) → Application → Cookies からコピー
3. または拡張機能「EditThisCookie」等でJSON形式エクスポート

## ユーザー収集元

以下の導線からユーザーを収集:

1. **既存CSVデータ** (`DB - 3_21時点myfansランキングデータ.csv`)
2. **ランキングページ** (`/ranking/creators`, `/ranking/posts`)
3. **トップページ** (ピックアップ、おすすめ)
4. **ジャンル検索** (`/s/genres/{genre}`)
5. **フィード** (`/feed` - ログイン必須)

## セットアップ

```bash
pip install scrapling[all]
```

## ファイル構成

```
myfans/
├── README.md              # 本ファイル
├── explore_site.py        # サイト構造調査スクリプト
├── page_*.html            # 調査時に保存したHTMLサンプル
└── (今後追加)
    ├── config.py          # 認証情報・設定
    ├── scraper_myfans.py  # MyFansスクレイパー
    ├── scraper_x.py       # X(Twitter)スクレイパー
    ├── scraper_instagram.py # Instagramスクレイパー
    ├── scraper_tiktok.py  # TikTokスクレイパー
    ├── main.py            # メインスクリプト
    └── output/            # CSV出力先
```
