#!/usr/bin/env python3
"""
Redken 产品全量抓取工具（纯爬虫，不调用 Claude）

分别抓取：
  1. Ulta Beauty 上所有 Redken 产品
  2. Redken 官网所有产品

结果保存到 product_catalog.json 和 product_list.txt（方便人工查看）

使用方法:
  python discover.py
  （不需要设置任何 API Key）
"""

import json
from datetime import datetime
from playwright.sync_api import sync_playwright


# ─────────────────────────────────────────────
# 抓取 Ulta Beauty 上所有 Redken 产品
# ─────────────────────────────────────────────

def scrape_ulta_all_redken(page):
    print("\n【Ulta Beauty】正在抓取所有 Redken 产品...")

    all_products = []
    page_num = 1

    while True:
        if page_num == 1:
            url = "https://www.ulta.com/brand/redken"
        else:
            url = f"https://www.ulta.com/brand/redken?page={page_num}"

        print(f"  第 {page_num} 页：{url}")
        page.goto(url, wait_until="load", timeout=60000)
        page.wait_for_timeout(2000)

        # 滚动确保懒加载完成
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1500)

        cards = page.query_selector_all("li[class*='productCard']")
        if not cards:
            cards = page.query_selector_all("div.ProductCard")

        if not cards:
            print(f"  第 {page_num} 页没有产品，停止")
            break

        print(f"  找到 {len(cards)} 个产品卡片")

        page_products = []
        for card in cards:
            try:
                p = extract_ulta_product(card)
                if p:
                    page_products.append(p)
            except Exception:
                continue

        print(f"  本页成功提取 {len(page_products)} 个产品")
        all_products.extend(page_products)

        # 如果这页不足 64 个卡片，说明是最后一页
        if len(cards) < 64:
            break
        page_num += 1

    print(f"  Ulta 共提取 {len(all_products)} 个产品")
    return all_products


def extract_ulta_product(card):
    # 产品全名（screen reader span，格式："Redken All Soft Shampoo"）
    name_el = card.query_selector("span[class*='isScreenReader']")
    name = name_el.inner_text().strip() if name_el else ""

    # 兜底：用短名称
    if not name:
        name_el = card.query_selector(".pal-c-ProductCardBody--content p")
        name = name_el.inner_text().strip() if name_el else ""

    if not name:
        return None

    # 价格文字（保留原始格式，如 "$11.00 - $56.00" 或 "$28.00"）
    price_el = card.query_selector(".pal-c-Price__priceContainer span")
    price_text = price_el.inner_text().strip() if price_el else ""

    # 促销标签（sale badge）
    badge_el = card.query_selector("[class*='badge'], [class*='Badge'], [class*='promo'], [class*='sale']")
    badge_text = badge_el.inner_text().strip() if badge_el else ""

    # 链接
    link_el = card.query_selector("a[href]")
    link = link_el.get_attribute("href") if link_el else ""
    if link and link.startswith("/"):
        link = "https://www.ulta.com" + link

    # 尺寸数量（如 "4 sizes"）
    size_el = card.query_selector("[class*='variant'], [class*='Variant']")
    sizes = size_el.inner_text().strip() if size_el else ""

    # 产品图片（保留原始 400x400 URL，让浏览器缩放，保证清晰度）
    img_el = card.query_selector("img[src]")
    img_src = img_el.get_attribute("src") if img_el else ""

    return {
        "source": "ulta",
        "name": name,
        "price_text": price_text,
        "badge": badge_text,
        "sizes": sizes,
        "link": link,
        "image": img_src,
    }


# ─────────────────────────────────────────────
# 抓取 Redken 官网所有产品
# ─────────────────────────────────────────────

def scrape_redken_official(page):
    print("\n【Redken 官网】正在抓取所有产品...")
    url = "https://www.redken.com/collections/all"
    print(f"  访问：{url}")

    try:
        page.goto(url, wait_until="load", timeout=60000)
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"  加载超时，继续尝试提取已加载内容...")

    # 滚动加载
    prev_height = 0
    for _ in range(15):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1200)
        curr_height = page.evaluate("document.body.scrollHeight")
        if curr_height == prev_height:
            break
        prev_height = curr_height

    # 保存 Redken 官网第一个卡片 HTML 供调试
    all_cards = page.query_selector_all("[class*='product']")
    if all_cards:
        with open("debug_redken_card.html", "w", encoding="utf-8") as f:
            f.write(all_cards[0].inner_html()[:3000])
        print("  Redken 第一个卡片 HTML 已保存到 debug_redken_card.html")

    # 尝试多种选择器
    cards = page.query_selector_all(".product-card, .product-item, [class*='ProductCard']")
    if not cards:
        cards = page.query_selector_all("li[class*='product']")

    print(f"  找到 {len(cards)} 个产品卡片")

    products = []
    for card in cards:
        try:
            p = extract_redken_product(card)
            if p:
                products.append(p)
        except Exception:
            continue

    # 去重（按名称）
    seen = set()
    unique = []
    for p in products:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique.append(p)

    print(f"  成功提取 {len(unique)} 个产品（去重后）")
    return unique


def extract_redken_product(card):
    # 尝试找产品名
    name = ""
    for selector in ["h2", "h3", "[class*='product-title']", "[class*='product-name']",
                     "[class*='productTitle']", "[class*='productName']"]:
        el = card.query_selector(selector)
        if el:
            text = el.inner_text().strip()
            # 过滤掉纯badge文字（BEST SELLER, NEW 等）
            if text and len(text) > 5 and text not in ("BEST SELLER", "NEW", "AWARD-WINNER"):
                name = text
                break

    if not name:
        return None

    # 价格
    price_el = card.query_selector("[class*='price'], .price")
    price_text = price_el.inner_text().strip() if price_el else ""

    # 链接
    link_el = card.query_selector("a[href]")
    link = link_el.get_attribute("href") if link_el else ""
    if link and link.startswith("/"):
        link = "https://www.redken.com" + link

    return {
        "source": "redken_official",
        "name": name,
        "price_text": price_text,
        "link": link,
    }


# ─────────────────────────────────────────────
# 生成 HTML 报告
# ─────────────────────────────────────────────

def build_product_rows(products):
    rows = ""
    for i, p in enumerate(products, 1):
        name = p.get("name", "")
        price = p.get("price_text", "—")
        badge = p.get("badge", "")
        sizes = p.get("sizes", "")
        link = p.get("link", "")
        image = p.get("image", "")

        badge_html = f'<span class="badge">{badge}</span>' if badge else ""
        sizes_html = f'<span class="sizes">{sizes}</span>' if sizes else ""
        name_html = f'<a href="{link}" target="_blank">{name}</a>' if link else name
        img_html = f'<div class="img-wrap"><img class="product-img" src="{image}" alt="{name}" loading="lazy"></div>' if image else '<div class="img-wrap img-empty"></div>'

        rows += f"""
        <tr>
          <td class="num">{i}</td>
          <td class="img-cell">{img_html}</td>
          <td class="name">{name_html} {badge_html} {sizes_html}</td>
          <td class="price">{price}</td>
        </tr>"""
    return rows


def save_html(ulta_products, redken_products):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ulta_rows = build_product_rows(ulta_products)
    redken_rows = build_product_rows(redken_products)

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <title>Redken 产品清单 {now}</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; }}
    h1 {{ font-size: 22px; color: #333; }}
    h2 {{ font-size: 17px; margin-top: 40px; padding: 8px 14px; background: #f5f5f5; border-left: 4px solid #e4007c; }}
    .meta {{ color: #888; font-size: 13px; margin-bottom: 30px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th {{ text-align: left; padding: 8px 12px; background: #fafafa; border-bottom: 2px solid #eee; font-size: 13px; color: #666; }}
    td {{ padding: 9px 12px; border-bottom: 1px solid #f0f0f0; font-size: 14px; vertical-align: middle; }}
    tr:hover {{ background: #fffbf5; }}
    td.num {{ color: #bbb; width: 36px; font-size: 12px; }}
    td.name a {{ color: #1a1a1a; text-decoration: none; }}
    td.name a:hover {{ color: #e4007c; text-decoration: underline; }}
    td.price {{ color: #333; font-weight: 500; white-space: nowrap; width: 160px; }}
    .badge {{ display: inline-block; font-size: 11px; padding: 2px 7px; border-radius: 3px; background: #fff0f6; color: #c0006a; border: 1px solid #ffd6ea; margin-left: 6px; }}
    .sizes {{ font-size: 12px; color: #999; margin-left: 6px; }}
    td.img-cell {{ width: 72px; padding: 6px 10px; }}
    .img-wrap {{ width: 56px; height: 56px; overflow: visible; position: relative; }}
    .img-empty {{ background: #f5f5f5; border-radius: 6px; }}
    .product-img {{
      width: 56px;
      height: 56px;
      object-fit: cover;
      border-radius: 6px;
      display: block;
      transition: transform 0.2s ease, box-shadow 0.2s ease, border-radius 0.2s ease;
      transform-origin: left center;
      position: relative;
      z-index: 1;
      cursor: zoom-in;
      will-change: transform;
    }}
    .product-img:hover {{
      transform: scale(3.5);
      z-index: 999;
      border-radius: 0;
      box-shadow: 0 6px 20px rgba(0,0,0,0.25);
    }}
  </style>
</head>
<body>
  <h1>Redken 产品全量清单</h1>
  <p class="meta">抓取时间：{now} &nbsp;|&nbsp; Ulta Beauty: {len(ulta_products)} 个 &nbsp;|&nbsp; Redken 官网: {len(redken_products)} 个</p>

  <h2>Ulta Beauty &nbsp; <span style="font-weight:normal;font-size:14px;">共 {len(ulta_products)} 个产品</span></h2>
  <table>
    <thead><tr><th>#</th><th style="width:72px;">图片</th><th>产品名称</th><th>价格</th></tr></thead>
    <tbody>{ulta_rows}</tbody>
  </table>

  <h2>Redken 官网 &nbsp; <span style="font-weight:normal;font-size:14px;">共 {len(redken_products)} 个产品</span></h2>
  <table>
    <thead><tr><th>#</th><th style="width:72px;">图片</th><th>产品名称</th><th>价格</th></tr></thead>
    <tbody>{redken_rows}</tbody>
  </table>
</body>
</html>"""

    with open("product_list.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("\nHTML 清单已保存到 product_list.html（双击用浏览器打开）")


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Redken 产品全量抓取（无 Claude，不消耗 API）")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    ulta_products = []
    redken_products = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        })

        try:
            ulta_products = scrape_ulta_all_redken(page)
        except Exception as e:
            print(f"  Ulta 抓取失败: {e}")

        # TODO: Redken 官网抓取暂时禁用，待后续优化
        # try:
        #     redken_products = scrape_redken_official(page)
        # except Exception as e:
        #     print(f"  Redken 官网抓取失败: {e}")

        browser.close()

    # 保存 JSON
    with open("product_catalog.json", "w", encoding="utf-8") as f:
        json.dump({
            "scraped_at": datetime.now().isoformat(),
            "ulta_count": len(ulta_products),
            "redken_count": len(redken_products),
            "ulta_products": ulta_products,
            "redken_products": redken_products,
        }, f, ensure_ascii=False, indent=2)

    # 保存可读文本
    save_html(ulta_products, redken_products)

    print(f"\n完成！Ulta: {len(ulta_products)} 个，Redken 官网: {len(redken_products)} 个")


if __name__ == "__main__":
    main()
