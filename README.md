# Ulta Redken 降价监控 | Ulta Redken Price Monitor

每天自动抓取 Ulta Beauty 上指定 Redken 系列产品的价格，用 Claude AI 分析折扣力度，只在低于 8 折时发送 Mac 桌面通知。

A daily price monitor for Redken products on Ulta Beauty. Uses Claude AI to interpret complex promotions and alerts you via Mac notification when discounts exceed 20%.

---

## 监控系列

| 系列 | 说明 |
|------|------|
| Acidic Bonding Concentrate | 白色修护系列 |
| Acidic Color Gloss | 黑粉色护色系列 |
| Blondage | 紫色漂发护理 |
| Extreme | 蓝色极致修护 |
| Extreme Length | 蓝色长发护理 |

## 功能

- 自动抓取 Ulta 搜索结果（Playwright 浏览器自动化）
- 解析原价、现价、促销文字（满减 / 折扣 / 特定活动）
- 用 Claude AI 换算实际折扣比例
- 生成中文每日报告
- Mac 桌面通知提醒

## 安装

```bash
cd ulta-redken-monitor
python3 -m venv ulta-env
source ulta-env/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## 使用方法

```bash
export ANTHROPIC_API_KEY=你的Claude_API_Key
python monitor.py
```

## 技术栈

- Python 3
- [Playwright](https://playwright.dev/python/) — 浏览器自动化抓取
- [Anthropic Claude API](https://anthropic.com) — 促销解读 + 中文报告

---

*Built with Claude Code*
