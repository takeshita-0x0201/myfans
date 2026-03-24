# macOS セットアップ手順（コピペ用）

各コマンドを **1つずつ** コピーして、ターミナルに貼り付けて実行してください。

---

## Step 1. Homebrewインストール

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Step 2. Homebrewのパスを通す（Apple Silicon Mac）

```
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
```

```
source ~/.zprofile
```

確認：

```
brew --version
```

## Step 3. Gitインストール

```
brew install git
```

## Step 4. Python 3.13インストール

```
brew install python@3.13
```

## Step 5. Python 3.13のパスを通す

```
echo 'export PATH="/opt/homebrew/opt/python@3.13/libexec/bin:$PATH"' >> ~/.zprofile
```

```
source ~/.zprofile
```

確認：

```
python3 --version
```

Python 3.13.x と表示されればOK。

## Step 6. リポジトリのクローン

```
cd ~/Documents
```

```
git clone https://github.com/takeshita-0x0201/myfans.git
```

```
cd myfans
```

## Step 7. 仮想環境の作成・有効化

```
python3 -m venv .venv
```

```
source .venv/bin/activate
```

プロンプトの先頭に (.venv) と表示されれば成功。

## Step 8. Pythonパッケージのインストール

```
pip install -r requirements.txt
```

zsh で `no matches found` エラーが出た場合：

```
pip install "scrapling[all]"
```

## Step 9. ブラウザエンジンのインストール

```
python -m camoufox fetch
```

```
python -m playwright install
```

## Step 10. Cookieの配置

cookies/ ディレクトリに以下のファイルを配置（元PCからコピー）：

- cookies/myfans.json（必須）
- cookies/x.json（必須）
- cookies/instagram.json（必須）
- cookies/tiktok.json（推奨）

## Step 11. 動作確認

```
python main.py テスト用ユーザー名
```

output/ フォルダにCSVが生成されれば成功。

---

## 2回目以降の起動手順

```
cd ~/Documents/myfans
```

```
source .venv/bin/activate
```

```
python main.py ユーザー名1 ユーザー名2
```

---

## git pull で更新を取得する（ZIPで初回セットアップした場合）

まず壊れた .git を削除してやり直します：

```
rm -rf ~/Documents/myfans/.git
```

```
cd ~/Documents/myfans
```

```
git init
```

```
git remote add origin https://github.com/takeshita-0x0201/myfans.git
```

```
git fetch origin
```

```
git reset --mixed origin/main
```

GitHubのユーザー名とパスワード（Personal Access Token）を求められます。

Personal Access Tokenの作り方：
1. GitHub にログイン
2. Settings → Developer settings → Personal access tokens → Tokens (classic)
3. Generate new token (classic) をクリック
4. repo にチェックを入れて生成
5. 表示されたトークンをパスワードとして入力

設定後、以降は以下で最新コードを取得できます：

```
git pull origin main
```

---

## トラブル: .zprofile が壊れた場合

以下を実行して .zprofile を正しい内容で上書きしてください：

```
cat > ~/.zprofile << 'EOF'
eval "$(/opt/homebrew/bin/brew shellenv)"
export PATH="/opt/homebrew/opt/python@3.13/libexec/bin:$PATH"
EOF
```

```
source ~/.zprofile
```
