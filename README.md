# MyFans Scraper

MyFansのユーザープロフィール・SNS情報を自動収集し、CSVで出力するスクレイピングシステム。

## クイックスタート

### 1. セットアップ

```bash
git clone https://github.com/takeshita-0x0201/myfans.git
cd myfans

# Python 3.13+ 推奨
pip install -r requirements.txt
```

### 2. Cookieの配置

`cookies/` ディレクトリに各サービスのCookieファイルを配置してください。
詳細は [`cookies/README.md`](cookies/README.md) を参照。

| ファイル | サービス | 必須 |
|---------|---------|------|
| `cookies/myfans.json` | MyFans | 必須 |
| `cookies/x.json` | X (Twitter) | 必須 |
| `cookies/instagram.json` | Instagram | 必須 |
| `cookies/tiktok.json` | TikTok | 推奨 |

### 3. 実行

```bash
# 特定のユーザーをスクレイピング
python main.py _072q secret_japan yuma24

# 既存CSVの全ユーザーを一括スクレイピング
# (デフォルト: ~/Downloads/DB - 3_21時点myfansランキングデータ.csv)
python main.py
```

CSVは `output/myfans_data_YYYYMMDD_HHMMSS.csv` に出力されます。
5ユーザーごとに途中保存されるため、中断しても途中までの結果が残ります。

## 処理時間の目安

1ユーザーあたり約10分（MyFans + X + Instagram + TikTok）。
SNSリンクがないユーザーは該当SNSをスキップするため短縮されます。

## ファイル構成

```
myfans/
├── main.py               # メインスクリプト（エントリポイント）
├── scraper_myfans.py     # MyFansスクレイパー
├── scraper_x.py          # X (Twitter) スクレイパー
├── scraper_instagram.py  # Instagramスクレイパー
├── scraper_tiktok.py     # TikTokスクレイパー
├── utils.py              # 共通ユーティリティ
├── requirements.txt      # Pythonパッケージ
├── cookies/              # Cookie格納（git管理外）
│   └── README.md         # Cookie取得手順
├── output/               # CSV出力先（git管理外）
├── .gitignore
└── README.md
```

## CSV カラム定義（55カラム）

### 基本情報

| カラム | 説明 |
|--------|------|
| `scraped_at` | 取得日 |
| `rank` | ランキング順位（ランキング外は空欄） |
| `name` | 表示名 |
| `username` | ユーザーID |
| `myfans_url` | プロフィールURL |
| `profile_text` | プロフィール文 |
| `followers` | フォロワー数 |
| `likes` | いいね数 |
| `posts` | 総投稿数 |
| `last_30d_posts` | 直近30日の投稿数（実数） |
| `myfans_latest_post_date` | MyFans最新投稿日 |
| `myfans_first_post_date` | MyFans最古投稿日 |

### SNS（X / Instagram / TikTok 各7カラム）

各SNSについて以下のカラムがあります（`{sns}` = `x`, `instagram`, `tiktok`）：

| カラム | 説明 |
|--------|------|
| `sns_{sns}` | アカウント有無 (0/1) |
| `sns_url_{sns}` | プロフィールURL |
| `{sns}_followers` | フォロワー数 |
| `{sns}_posts` | 投稿数 |
| `{sns}_last_30d_posts` | 直近30日投稿数 |
| `{sns}_latest_post_date` | 最新投稿日 |
| `{sns}_first_post_date` | 最初の投稿日 |

### その他SNS

| カラム | 説明 |
|--------|------|
| `sns_others` | 有無 (0/1) |
| `sns_others_name` | 媒体名 (youtube, lit.link等) |
| `sns_url_others` | URL |

### プラン情報（金額昇順、最大9プラン）

| カラム | 説明 |
|--------|------|
| `plan{N}_price` | プランN料金（円） |
| `plan{N}_posts` | プランN投稿数 |

### フラグ

| カラム | 説明 |
|--------|------|
| `has_free_plan` | ¥0プランの有無 (0/1) |
| `has_trial_period` | 初月無料/半額等の有無 (0/1) |
| `has_update_frequency` | 投稿頻度（現在スコープ外・空欄） |

## 技術詳細

- **Scrapling** の `StealthyFetcher` でブラウザレンダリング（Camoufox/Playwright）
- MyFansは年齢確認ダイアログを自動突破
- Xはセンシティブコンテンツ警告を自動突破
- MyFansの投稿日付はスワイプビューをスクロールして収集
- プラン情報は金額の昇順でソートして格納
