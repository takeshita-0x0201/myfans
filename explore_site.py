"""
MyFansサイト構造調査スクリプト
Scraplingを使用してユーザーページの構造を把握する
"""
from scrapling import StealthyFetcher
import time

fetcher = StealthyFetcher()


def click_age_gate(page):
    """年齢確認ダイアログの「はい」ボタンをクリック（同期版）"""
    try:
        buttons = page.locator('button')
        count = buttons.count()
        for i in range(count):
            btn = buttons.nth(i)
            text = btn.inner_text()
            if 'はい' in text or 'Yes' in text:
                print(f"  -> 年齢確認ボタンをクリック: {text.strip()}")
                btn.click()
                page.wait_for_timeout(3000)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)
                break
    except Exception as e:
        print(f"  -> 年齢確認処理エラー: {e}")


def explore_user_page(username="_072q"):
    """ユーザーページの構造を調査"""
    url = f"https://myfans.jp/{username}"
    print(f"\n{'='*60}")
    print(f"Fetching: {url}")
    print(f"{'='*60}")

    page = fetcher.fetch(
        url,
        headless=True,
        timeout=60000,
        page_action=click_age_gate,
        network_idle=True,
    )
    print(f"Status: {page.status}")

    html = page.html_content
    print(f"HTML length: {len(html)} chars")

    # タイトル
    title = page.css('title')
    if title:
        print(f"Title: {title[0].text}")

    # 全テキスト要素
    print("\n--- 主要テキスト要素 ---")
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        elements = page.css(tag)
        if elements:
            print(f"\n<{tag}> ({len(elements)}個):")
            for i, el in enumerate(elements[:15]):
                text = el.text.strip()
                if text and len(text) < 200:
                    print(f"  [{i}] {text}")

    # p / span
    print("\n--- p/span テキスト ---")
    for tag in ['p', 'span']:
        elements = page.css(tag)
        if elements:
            count = 0
            for el in elements:
                text = el.text.strip()
                if text and 2 < len(text) < 200:
                    classes = el.attrib.get('class', '')
                    print(f"  <{tag} class='{classes[:50]}'> {text}")
                    count += 1
                    if count >= 50:
                        break

    # div テキスト
    print("\n--- div テキスト ---")
    count = 0
    for el in page.css('div'):
        text = el.text.strip()
        if text and 2 < len(text) < 120:
            classes = el.attrib.get('class', '')
            print(f"  <div class='{classes[:50]}'> {text}")
            count += 1
            if count >= 60:
                break

    # リンク
    print("\n--- 全リンク ---")
    links = page.css('a')
    seen = set()
    for link in links:
        href = link.attrib.get('href', '')
        text = link.text.strip()[:80]
        classes = link.attrib.get('class', '')[:40]
        if href and href not in seen:
            seen.add(href)
            print(f"  [{classes}] {href} -> {text}")

    # SVG付きリンク
    print("\n--- SVGを含むリンク ---")
    for link in page.css('a'):
        svgs = link.css('svg')
        if svgs:
            href = link.attrib.get('href', '')
            text = link.text.strip()[:40]
            print(f"  {href} (SVG icon) -> {text}")

    # ボタン
    print("\n--- ボタン ---")
    for btn in page.css('button'):
        text = btn.text.strip()[:80]
        if text:
            print(f"  {text}")

    # 特徴的クラス名
    print("\n--- 特徴的クラス名 ---")
    all_classes = set()
    for el in page.css('[class]'):
        for c in el.attrib.get('class', '').split():
            all_classes.add(c)
    keywords = ['follower', 'like', 'post', 'sns', 'social', 'profile', 'plan',
                'rank', 'count', 'stat', 'fan', 'user', 'creator', 'bio',
                'avatar', 'header', 'banner', 'tab', 'nav', 'menu', 'sidebar']
    for c in sorted(all_classes):
        if any(kw in c.lower() for kw in keywords):
            print(f"  .{c}")

    # HTML保存
    html_path = f'/Users/yukitakeshia/Documents/GitHub/myfans/page_{username}.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\nHTML保存: {html_path} ({len(html)} chars)")

    return page


def explore_top_page():
    """トップページの構造を調査"""
    url = "https://myfans.jp"
    print(f"\n{'='*60}")
    print(f"Fetching TOP: {url}")
    print(f"{'='*60}")

    page = fetcher.fetch(
        url,
        headless=True,
        timeout=60000,
        page_action=click_age_gate,
        network_idle=True,
        locale='ja-JP',
    )
    print(f"Status: {page.status}")
    html = page.html_content
    print(f"HTML length: {len(html)} chars")

    print("\n--- リンク一覧 ---")
    links = page.css('a')
    seen = set()
    for link in links:
        href = link.attrib.get('href', '')
        text = link.text.strip()[:60]
        if href and href not in seen:
            seen.add(href)
            print(f"  {href} -> {text}")

    html_path = '/Users/yukitakeshia/Documents/GitHub/myfans/page_top.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\nHTML保存: {html_path}")
    return page


if __name__ == "__main__":
    print("=== MyFans サイト構造調査 ===")

    # 1. ユーザーページ
    user_page = explore_user_page("_072q")

    time.sleep(3)

    # 2. トップページ
    top_page = explore_top_page()

    print("\n\n=== 調査完了 ===")
