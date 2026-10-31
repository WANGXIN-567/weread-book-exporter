# 📚 WeRead Book Exporter (`weread-book-exporter`)

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Engine-Playwright-2EAD33.svg)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

将微信读书 Web 端已购或会员书籍**无损抓取全书全文**，并一键导出为 **精排 PDF**、**标准 EPUB** 以及 **纯 Markdown 笔记（适配 Obsidian / Notion）**。

自动保留原书的**目录结构、标题层级、引文/重点段落样式与高清插图**，提供舒适的大字号双字体排版，方便个人深度学习、全文检索与知识库归档。

---

## ✨ 核心特性

### 1. 100% 全书完整抓取（攻克网页端翻页漏字问题）
许多传统的微信读书抓取脚本在默认的上下滚动模式下运行，受限于网页端超长虚拟滚动容器的分片机制，翻页时极易跳过章节下半部分内容。
- **自动双栏翻页模式**：自动检测并切换至水平双栏模式，逐页完整遍历全书；
- **精准页面重组**：在底层捕获 Canvas 绘制指令与分栏坐标，精准还原每一页的文本流与段落顺序，杜绝跨页丢字、重复或错乱。

### 2. 原生级层次还原与断句修复
- **多级样式识别**：根据画布渲染的字号与字重，自动区分**章节标题、独立引文/核心段落、加粗小标题与普通正文**；
- **智能断句拼接**：自动修复因页面折行、翻页或插图穿插导致的句子中断，生成连贯自然的自然段；
- **插图自动下载**：自动提取并下载原书全部高清配图，按阅读顺序内嵌至对应位置。

### 3. 一键导出三大常用格式
| 导出格式 | 适用场景 | 特性说明 |
| :--- | :--- | :--- |
| **精排 PDF (`.pdf`)** | iPad 批注、电脑阅读、打印 | **苹方正文 + 楷体引文**大字号排版，内置封面、可点击目录页、PDF 侧边栏书签大纲 (Outline) 与页码 |
| **标准 EPUB (`.epub`)** | Apple Books / Kindle / 阅读器 | 内嵌多字体排版样式、完整目录导航树与原书高清插图 |
| **Markdown (`.md`)** | Obsidian / Notion / 个人知识库 | 提供**纯 Markdown 版**（引文自动转为 `>` 引用块）与**带样式标签版**，方便检索与做笔记 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 第一步：抓取全书正文与插图

在微信读书网页版打开目标书籍，从浏览器地址栏复制末段的书籍 ID（例如 `https://weread.qq.com/web/reader/<book_id>`）：

```bash
python crawl_weread.py <book_id>
```

> **提示**：首次运行时会弹出浏览器窗口，使用微信扫码登录即可。登录凭证仅保存在本地 `cache/` 目录（已通过 `.gitignore` 忽略），后续使用无需重复扫码。

### 3. 第二步：导出 PDF / EPUB / Markdown

```bash
python export_book.py <book_id>
```

导出完成后，生成的 `.pdf`、`.epub` 与 `.md` 文件均位于 `output/` 目录下。

---

## 🛠️ 工作流程

```mermaid
flowchart LR
    A["微信读书网页版\n(自动切换双栏翻页)"] --> B["底层文本与插图捕获\n逐页提取字号/字重/坐标"]
    B --> C["段落重组与清洗\n合并跨行断句 & 去重"]
    C --> D["多格式导出引擎\nPDF / EPUB / Markdown"]
```

---

## ⚠️ 免责声明 (Disclaimer)

1. 本工具仅用于个人学习、读书笔记整理与前端渲染技术研究。
2. 请支持正版阅读，仅对您个人合法拥有阅读权限的书籍使用本工具，导出的文件请勿用于任何商业用途或公开传播。
3. 本仓库仅包含通用转换脚本，不包含任何受版权保护的书籍内容或个人登录信息。

---

如果这个工具对你的阅读与笔记整理有帮助，欢迎点亮一颗 **Star ⭐** 支持！
