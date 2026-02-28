#!/usr/bin/env python3
"""
Ulta Beauty Redken 降价监控工具

使用方法:
  python monitor.py

需要设置环境变量:
  export ANTHROPIC_API_KEY=你的Claude_API_Key
"""

import os
import json
import re
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright
import anthropic

# ========== 监控系列配置 ==========
SERIES = [
    {
        "name": "Acidic Bonding Concentrate",
        "label": "白色 - Acidic Bonding Concentrate",
        "search": "redken acidic bonding concentrate",
    },
    {
        "name": "Acidic Color Gloss",
        "label": "黑粉色 - Acidic Color Gloss",
        "search": "redken acidic color gloss",
    },
    {
        "name": "Blondage",
        "label": "紫色 - Blondage",
        "search": "redken blondage",
    },
    {
        "name": "Extreme",
        "label": "蓝色① - Extreme",
        "search": "redken extreme",
    },
    {
        "name": "Extreme Length",
        "label": "蓝色② - Extreme Length",
        "search": "redken extreme length",
    },
]

DISCOUNT_THRESHOLD = 0.8   # 只关注低于8折的产品
STATE_FILE = "prices_state.json"
# ==================================


def scrape_series(page, series):
    """抓取某个系列在 Ulta 的产品列表"""
    search_url = f"https://www.ulta.com/search?search={series['search'].replace(' ', '+')}"
    print(f"  正在访问: {search_url}")

    page.goto(search_url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)  # 等待 JS 渲染

    products = []

    # 找所有产品卡片
    cards = page.query_selector_all("[class*='ProductCard'], [data-testid*='product']")
    if not cards:
        # 备用选择器
        cards = page.query_selector_all(".ProductCard, .product-card, [class*='productCard']")

    print(f"  找到 {len(cards)} 个产品卡片")

    for card in cards:
        try:
            # 产品名称
            name_el = card.query_selector("[class*='product-name'], [class*='ProductName'], h3, h4, [class*='title']")
            name = name_el.inner_text().strip() if name_el else ""

            # 跳过非 Redken 产品（因为搜索结果可能混入其他品牌）
            if "redken" not in name.lower() and "acidic" not in name.lower() and \
               "blondage" not in name.lower() and "extreme" not in name.lower():
                # 尝试从品牌字段判断
                brand_el = card.query_selector("[class*='brand'], [class*='Brand']")
                brand = brand_el.inner_text().strip() if brand_el else ""
                if "redken" not in brand.lower():
                    continue

            if not name:
                continue

            # 现价（优先找 sale price）
            sale_price_el = card.query_selector(
                "[class*='sale'], [class*='Sale'], [class*='discount'], [class*='special'], "
                "[class*='price--sale'], [class*='priceText--sale']"
            )
            regular_price_el = card.query_selector(
                "[class*='regular'], [class*='Regular'], [class*='original'], "
                "[class*='price--regular'], [class*='priceText--regular'], [class*='price']"
            )

            sale_price = None
            original_price = None

            if sale_price_el:
                sale_text = sale_price_el.inner_text().strip()
                sale_price = parse_price(sale_text)

            if regular_price_el:
                regular_text = regular_price_el.inner_text().strip()
                original_price = parse_price(regular_text)

            # 如果没找到分开的价格，用通用选择器
            if not original_price:
                all_price_els = card.query_selector_all("[class*='price'], [class*='Price']")
                prices = []
                for el in all_price_els:
                    p = parse_price(el.inner_text())
                    if p:
                        prices.append(p)
                if prices:
                    original_price = max(prices)  # 最高价当原价
                    if len(prices) > 1:
                        sale_price = min(prices)

            # 促销文字（满减等）
            promo_el = card.query_selector(
                "[class*='promo'], [class*='Promo'], [class*='offer'], [class*='badge'], "
                "[class*='Banner'], [class*='tag']"
            )
            promo_text = promo_el.inner_text().strip() if promo_el else ""

            # 产品链接
            link_el = card.query_selector("a")
            link = "https://www.ulta.com" + link_el.get_attribute("href") \
                if link_el and link_el.get_attribute("href") else ""

            if original_price:
                products.append({
                    "name": name,
                    "original_price": original_price,
                    "sale_price": sale_price,
                    "promo_text": promo_text,
                    "link": link,
                })

        except Exception as e:
            continue

    return products


def parse_price(text):
    """从字符串中提取价格数字，例如 '$28.00' → 28.0"""
    if not text:
        return None
    match = re.search(r"\$?([\d]+\.[\d]{2})", text)
    if match:
        return float(match.group(1))
    match = re.search(r"\$?([\d]+)", text)
    if match:
        return float(match.group(1))
    return None


def analyze_deals_with_claude(all_products, threshold=DISCOUNT_THRESHOLD):
    """用 Claude API 分析促销力度，返回值得购买的产品"""
    client = anthropic.Anthropic()

    # 整理成文字给 Claude 分析
    products_text = ""
    for series_name, products in all_products.items():
        products_text += f"\n【{series_name}】\n"
        for p in products:
            products_text += f"- {p['name']}\n"
            products_text += f"  原价: ${p['original_price']:.2f}"
            if p['sale_price']:
                ratio = p['sale_price'] / p['original_price']
                products_text += f"  | 售价: ${p['sale_price']:.2f} ({ratio:.0%})"
            if p['promo_text']:
                products_text += f"  | 促销: {p['promo_text']}"
            products_text += "\n"

    prompt = f"""你是一个帮用户分析 Ulta Beauty 上 Redken 产品折扣的助手。

以下是今天抓取到的产品信息：

{products_text}

用户的购买标准：只有当产品实际折扣低于8折（即支付价格 ≤ 原价×0.8）时才值得购买。

请完成以下任务：
1. 分析每个有折扣的产品，判断是否达到8折以下
2. 如果有满减促销（如"满$40减$10"），说明需要购买多少才能享受，以及能否达到8折
3. 生成一份简洁的中文报告，格式如下：

✅ 值得购买（低于8折）：
- [产品名] 原价$XX → 现价$XX（X折）[附链接]

⚠️ 接近8折（0.8~0.85折）：
- [产品名] 原价$XX → 现价$XX（X折）

❌ 折扣不够（高于0.85）：
- [系列名]目前无明显折扣

📌 满减提示：
- 如果有满减活动，解释一下

最后一行：当前最值得下手的产品是什么？"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def mac_notify(title, message):
    """发送 Mac 桌面通知"""
    script = f'display notification "{message}" with title "{title}" sound name "Ping"'
    subprocess.run(["osascript", "-e", script])


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("错误：请先设置 Anthropic API Key")
        print("运行: export ANTHROPIC_API_KEY=你的APIKey")
        return

    print("=" * 55)
    print("  Ulta Redken 降价监控")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    all_products = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 设置 User-Agent，模拟正常浏览器
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        })

        for series in SERIES:
            print(f"\n正在抓取：{series['label']}")
            try:
                products = scrape_series(page, series)
                all_products[series["label"]] = products
                print(f"  ✅ 找到 {len(products)} 个产品")
            except Exception as e:
                print(f"  ❌ 抓取失败: {e}")
                all_products[series["label"]] = []

        browser.close()

    # 检查是否有任何产品
    total = sum(len(v) for v in all_products.values())
    if total == 0:
        print("\n⚠️  没有抓取到任何产品，可能网站结构有变化")
        print("建议手动检查 Ulta 网站")
        return

    print(f"\n共抓取到 {total} 个产品，正在用 Claude 分析折扣...")

    # Claude 分析
    report = analyze_deals_with_claude(all_products)

    # 打印报告
    print("\n" + "=" * 55)
    print("  今日 Redken 折扣报告")
    print("=" * 55)
    print(report)
    print("=" * 55)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # 保存状态
    save_state({
        "last_run": datetime.now().isoformat(),
        "products": {k: v for k, v in all_products.items()},
    })

    # Mac 通知
    has_deal = "✅" in report
    if has_deal:
        mac_notify("🔴 Redken 有折扣！", "有产品低于8折，快去看报告！")
    else:
        mac_notify("Redken 监控完成", "今天暂无低于8折的产品")


if __name__ == "__main__":
    main()
