# Cookies

このディレクトリに各サービスのCookieファイル（JSON形式）を配置してください。

## 必要なファイル

| ファイル名 | サービス | 必須 |
|-----------|---------|------|
| `myfans.json` | MyFans | 必須 |
| `x.json` | X (Twitter) | 必須 |
| `instagram.json` | Instagram | 必須 |
| `tiktok.json` | TikTok | 推奨 |

## Cookie の取得方法

1. ブラウザで対象サービスにログイン
2. ブラウザ拡張機能 **EditThisCookie** 等をインストール
3. 対象サイト上で拡張機能を開き、JSON形式でエクスポート
4. このディレクトリに上記ファイル名で保存

## JSON フォーマット例

```json
[
    {
        "domain": ".example.com",
        "name": "session_id",
        "value": "abc123...",
        "path": "/",
        "secure": true,
        "httpOnly": true
    }
]
```

> **注意**: Cookieファイルは `.gitignore` で除外されています。絶対にGitにコミットしないでください。
