# Ulta Redken 降价监控 | Ulta Redken Price Monitor

每天自动抓取 Ulta Beauty 上所有 Redken 产品，按系列分组展示，用 Claude AI 分析折扣力度，只在低于 8 折时发送 Mac 桌面通知。

A price monitor for Redken products on Ulta Beauty. Scrapes all products, groups them by series, and alerts you via Mac notification when discounts exceed 20%.

---

## 工作流程

### 第一步：全量产品发现
```bash
python discover.py
```
爬取 Ulta Beauty 上所有 Redken 产品（共约 89 个），生成：
- `product_catalog.json` — 原始数据（机器读取）
- `product_list.html` — 所有产品列表（浏览器打开查看，含图片）

### 第二步：按系列分组查看
```bash
python organize.py
```
读取已有数据，按系列自动分组，生成 `product_grouped.html`，方便人工快速浏览。

### 第三步：价格监控（开发中）
```bash
export ANTHROPIC_API_KEY=你的Claude_API_Key
python monitor.py
```
对选定产品持续监控，发现折扣超过 20% 时推送 Mac 桌面通知。

---

## 支持的产品系列

| 系列 | 说明 |
|------|------|
| Acidic Bonding Concentrate | 白色修护系列 |
| Acidic Bonding Curls | 卷发修护系列 |
| Acidic Color Gloss | 黑粉色护色系列 |
| Blondage | 紫色漂发护理 |
| Extreme Length | 蓝色长发护理 |
| Extreme | 蓝色极致修护 |
| All Soft | 柔顺系列 |
| Frizz Dismiss | 控毛躁系列 |
| Volume Injection | 蓬松系列 |
| Magnetics | Magnetics 系列 |
| Brews | 男士护发系列 |
| Dry Shampoo | 干发喷雾 |
| Spray | 喷雾类 |
| 其他系列 | 其余产品统一归入此组 |

---

## 功能

**discover.py（产品发现）**
- 爬取 Ulta Beauty 品牌页所有 Redken 产品（分页自动处理）
- 提取：产品名、价格、促销标签、尺寸、产品图片、链接
- 生成带图片的 HTML 清单（图片悬停可放大预览）

**organize.py（分组整理）**
- 无需重新爬取，直接读取已有 JSON 数据
- 按系列关键词自动分组，未知系列归入 Other
- 生成按系列分区的 HTML，方便人工筛选

**monitor.py（价格监控，开发中）**
- 对指定产品定期抓取价格
- 用 Claude AI 解读复杂促销规则（满减、折扣、特殊活动）
- 折扣超过 20% 时推送 Mac 桌面通知

---

## 安装

```bash
cd ulta-redken-monitor
python3 -m venv ulta-env
source ulta-env/bin/activate
pip install -r requirements.txt
playwright install chromium
```

---

## 技术栈

- Python 3
- [Playwright](https://playwright.dev/python/) — 浏览器自动化抓取（处理 JS 渲染页面）
- [Anthropic Claude API](https://anthropic.com) — 促销解读 + 中文报告

---

## 开发历程 | Development Journey

这个项目不是一次写完的，而是经历了几个迭代阶段：

**阶段一：最小可运行版本**
先做出一个能跑的价格监控脚本（`monitor.py`），验证基本思路可行，然后推上 GitHub。

**阶段二：先别分析，先把数据搞对**
发现直接做分析效果很差，决定退一步——先把所有产品信息完整、准确地爬下来，再考虑分析。这就是 `discover.py` 的由来。
> 教训：数据质量 > 分析逻辑。分析再好也救不了烂数据。

**阶段三：用人工验证来发现 bug**
手动打开 Ulta 网站，看到"You have viewed 89 of 89"，但脚本只爬了 64 个。
通过这个已知的"正确答案"发现了分页 bug，修复后才真正爬全。
> 经验：用人工可验证的总数来核对爬取结果，是发现爬虫 bug 最有效的方法。

**阶段四：输出格式从能用到好用**
`.txt` → `.html`（可点击）→ 加产品图片（图比文字更直观）→ 悬停放大（不占空间又能看清）

**阶段五：分组整理**
机器不知道 Redken 有哪些系列，由用户提供系列关键词，机器按关键词匹配归组。
未能归入任何系列的产品统一落入 Other，不强行猜测。
> 经验：领域知识由人来提供，机器负责执行——人机各司其职。

---

*Built with Claude Code*
