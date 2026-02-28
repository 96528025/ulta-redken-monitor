#!/usr/bin/env python3
"""
产品分组工具

读取 product_catalog.json，按 Redken 系列分组，生成带分组标题的 HTML。
不需要重新爬取，直接用现有数据。

使用方法:
  python organize.py
"""

import json
from datetime import datetime

# ─────────────────────────────────────────────
# 系列定义（顺序很重要：Extreme Length 必须在 Extreme 前面，
# 否则 "Extreme Length" 会被错误归到 "Extreme" 组）
# ─────────────────────────────────────────────

SERIES = [
    "Acidic Bonding Concentrate",
    "Acidic Bonding Curls",
    "Acidic Color Gloss",
    "Blondage",
    "Extreme Length",
    "Extreme",
    "All Soft",
    "Frizz Dismiss",
    "Volume Injection",
    "Magnetics",
    "Brews",
    "Dry Shampoo",
    "Spray",
]

OTHER_LABEL = "其他系列 / Other"


def get_series(name):
    name_lower = name.lower()
    for series in SERIES:
        if series.lower() in name_lower:
            return series
    return OTHER_LABEL


def group_products(products):
    groups = {s: [] for s in SERIES}
    groups[OTHER_LABEL] = []
    for p in products:
        series = get_series(p.get("name", ""))
        groups[series].append(p)
    return groups


# ─────────────────────────────────────────────
# HTML 生成
# ─────────────────────────────────────────────

def build_rows(products, start_num=1):
    rows = ""
    for i, p in enumerate(products, start_num):
        name = p.get("name", "")
        price = p.get("price_text", "—")
        badge = p.get("badge", "")
        sizes = p.get("sizes", "")
        link = p.get("link", "")
        image = p.get("image", "")

        badge_html = f'<span class="badge">{badge}</span>' if badge else ""
        sizes_html = f'<span class="sizes">{sizes}</span>' if sizes else ""
        name_html = f'<a href="{link}" target="_blank">{name}</a>' if link else name
        img_html = (
            f'<div class="img-wrap"><img class="product-img" src="{image}" alt="{name}" loading="lazy"></div>'
            if image else '<div class="img-wrap img-empty"></div>'
        )

        rows += f"""
        <tr>
          <td class="num">{i}</td>
          <td class="img-cell">{img_html}</td>
          <td class="name">{name_html} {badge_html} {sizes_html}</td>
          <td class="price">{price}</td>
        </tr>"""
    return rows


def build_group_section(series_name, products, start_num, is_other=False):
    if not products:
        return "", start_num

    count = len(products)
    style = 'style="border-left-color: #aaa;"' if is_other else ""
    rows = build_rows(products, start_num)

    html = f"""
  <h2 class="series-title" {style}>{series_name} <span class="series-count">{count} 个产品</span></h2>
  <table>
    <thead><tr><th>#</th><th style="width:72px;">图片</th><th>产品名称</th><th>价格</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>"""

    return html, start_num + count


def save_grouped_html(products, scraped_at):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    groups = group_products(products)

    # 统计每个系列数量（供报告用）
    series_summary = ", ".join(
        f"{s}: {len(groups[s])}" for s in SERIES if groups[s]
    )
    other_count = len(groups[OTHER_LABEL])

    body_sections = ""
    counter = 1

    for series in SERIES:
        section, counter = build_group_section(series, groups[series], counter)
        body_sections += section

    # 其他系列放最后
    section, counter = build_group_section(OTHER_LABEL, groups[OTHER_LABEL], counter, is_other=True)
    body_sections += section

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <title>Redken 产品分组清单 {now}</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; max-width: 960px; margin: 40px auto; padding: 0 20px; color: #222; }}
    h1 {{ font-size: 22px; color: #333; }}
    .meta {{ color: #888; font-size: 13px; margin-bottom: 30px; }}
    h2.series-title {{
      font-size: 16px; margin-top: 44px; padding: 9px 16px;
      background: #fdf5f9; border-left: 4px solid #e4007c;
      display: flex; align-items: baseline; gap: 10px;
    }}
    .series-count {{ font-weight: normal; font-size: 13px; color: #aaa; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
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
      width: 56px; height: 56px; object-fit: cover; border-radius: 6px;
      display: block; cursor: zoom-in; will-change: transform;
      transition: transform 0.2s ease, box-shadow 0.2s ease, border-radius 0.2s ease;
      transform-origin: left center; position: relative; z-index: 1;
    }}
    .product-img:hover {{
      transform: scale(3.5); z-index: 999;
      border-radius: 0; box-shadow: 0 6px 20px rgba(0,0,0,0.25);
    }}
  </style>
</head>
<body>
  <h1>Redken 产品分组清单</h1>
  <p class="meta">
    数据来源：{scraped_at} &nbsp;|&nbsp; 生成时间：{now}<br>
    共 {len(products)} 个产品 &nbsp;|&nbsp; {series_summary}{f" | 其他: {other_count}" if other_count else ""}
  </p>
  {body_sections}
</body>
</html>"""

    out_file = "product_grouped.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成 {out_file}（双击用浏览器打开）")

    # 打印分组统计
    print("\n分组统计：")
    for s in SERIES:
        if groups[s]:
            print(f"  {s}: {len(groups[s])} 个")
    if groups[OTHER_LABEL]:
        print(f"  {OTHER_LABEL}: {len(groups[OTHER_LABEL])} 个")


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────

def main():
    try:
        with open("product_catalog.json", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("找不到 product_catalog.json，请先运行 discover.py 爬取数据。")
        return

    products = data.get("ulta_products", [])
    scraped_at = data.get("scraped_at", "未知")[:16].replace("T", " ")
    print(f"读取到 {len(products)} 个 Ulta 产品（数据时间：{scraped_at}）")

    save_grouped_html(products, scraped_at)


if __name__ == "__main__":
    main()
