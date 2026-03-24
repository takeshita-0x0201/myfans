# MyFans Scraper

MyFansのユーザープロフィール・SNS情報を自動収集し、CSVで出力するスクレイピングシステム。

## 動作環境

- **macOS**（Intel / Apple Silicon どちらも対応）
- **Python 3.13以上**（必須）
- 各サービスのログイン済みCookie

## 完全セットアップ手順（macOS / ゼロから）

### Step 1. Homebrewのインストール

ターミナル（アプリケーション → ユーティリティ → ターミナル）を開いて実行：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

インストール完了後、**Apple Silicon Mac（M1/M2/M3/M4）** の場合のみ、画面に表示される `eval` で始まる2行のコマンドを実行してパスを通してください。**Intel Mac** の場合はそのまま使えます。

確認：
```bash
brew --version
```

### Step 2. Gitのインストール

```bash
brew install git
```

確認：
```bash
git --version
```

### Step 3. Python 3.13のインストール

```bash
brew install python@3.13
```

確認：
```bash
python3 --version
# Python 3.13.x と表示されればOK
```

### Step 4. リポジトリのクローン

```bash
cd ~/Documents
git clone https://github.com/takeshita-0x0201/myfans.git
cd myfans
```

### Step 5. 仮想環境の作成・有効化

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> プロンプトの先頭に `(.venv)` と表示されれば成功です。
> 以降、**ターミナルを開き直すたびに** `cd ~/Documents/myfans && source .venv/bin/activate` を実行してください。

### Step 6. Pythonパッケージのインストール

```bash
pip install -r requirements.txt
```

### Step 7. ブラウザエンジンのインストール

Scraplingは内部でCamoufox（Firefox改造版）とPlaywrightを使います。

```bash
python -m camoufox fetch
python -m playwright install
```

### Step 8. Cookieの配置

`cookies/` ディレクトリに各サービスのCookieファイル（JSON形式）を配置します。
元PCから `cookies/*.json` をコピーするか、新たに取得してください。
詳細は [`cookies/README.md`](cookies/README.md) を参照。

| ファイル | サービス | 必須 |
|---------|---------|------|
| `cookies/myfans.json` | MyFans | 必須 |
| `cookies/x.json` | X (Twitter) | 必須 |
| `cookies/instagram.json` | Instagram | 必須 |
| `cookies/tiktok.json` | TikTok | 推奨 |

**Cookie取得手順（概要）:**

1. ブラウザで対象サービスにログイン
2. ブラウザ拡張機能（EditThisCookie等）でCookieをJSON形式でエクスポート
3. `cookies/` ディレクトリに上記ファイル名で保存

### Step 9. 動作確認

```bash
python main.py テスト用ユーザー名
```

`output/` フォルダにCSVが生成されれば成功です。

### 毎回の起動手順（2回目以降）

```bash
cd ~/Documents/myfans
source .venv/bin/activate
python main.py ユーザー名1 ユーザー名2
```

## 使い方

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

## トラブルシューティング

### `ModuleNotFoundError: No module named 'scrapling'`

仮想環境が有効か確認してください。

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### `camoufox` や `playwright` 関連のエラー

ブラウザが未インストールの可能性があります。

```bash
python -m camoufox fetch
python -m playwright install
```

### Cookieの有効期限切れ

各サービスのCookieは定期的に期限切れになります。スクレイピング結果が空やエラーになる場合は、ブラウザで再ログインしてCookieを再取得してください。

### `Python 3.13+ required` エラー

```bash
python3 --version
```

3.13未満の場合は、[python.org](https://www.python.org/downloads/) または `pyenv` で3.13以上をインストールしてください。

```bash
# pyenvの場合
pyenv install 3.13.0
pyenv local 3.13.0
```

## ファイル構成

```
myfans/
├── main.py               # メインスクリプト（エントリポイント）
├── scraper_myfans.py     # MyFansスクレイパー
├── scraper_x.py          # X (Twitter) スクレイパー
├── scraper_instagram.py  # Instagramスクレイパー
├── scraper_tiktok.py     # TikTokスクレイパー
├── scraper_ranking.py    # 月間クリエイターランキング
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
