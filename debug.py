#!/usr/bin/env python3
"""
快速诊断脚本：打印 Ulta 卡片的真实 HTML 结构
"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_extra_http_headers({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    })

    print("访问 Ulta...")
    page.goto("https://www.ulta.com/search?search=redken", wait_until="load", timeout=60000)
    page.wait_for_timeout(2000)

    # 保存完整页面 HTML
    html = page.content()
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"完整页面 HTML 已保存到 debug_page.html（{len(html)} 字符）")

    # 打印前 3 张卡片的文字内容
    cards = page.query_selector_all("li[class*='productCard']")
    print(f"\n找到 {len(cards)} 个卡片，打印前 3 个的文字内容：")
    for i, card in enumerate(cards[:3]):
        print(f"\n--- 卡片 {i+1} ---")
        print(card.inner_text()[:300])  # 只打印前 300 字符

    # 同时打印第一个卡片的 HTML
    if cards:
        print(f"\n--- 卡片 1 的 HTML（前 500 字符）---")
        print(cards[0].inner_html()[:500])

    browser.close()
