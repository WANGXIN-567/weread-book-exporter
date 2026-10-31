# 📚 WeRead Canvas Book Exporter (`weread-book-exporter`)

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Canvas%20Hook-2EAD33.svg)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

将微信读书 Web 端（Canvas 加密渲染）已购/会员书籍一键无损导出为 **双字体精排 PDF（苹方正文 + 楷体引文）**、**双字体 EPUB** 以及 **纯 Markdown 学习笔记版（适配 Obsidian / Notion）**。

特别针对**中医古籍解读（如《伤寒论》）、经典注疏、带引文专著**做了深度排版优化：自动根据 Canvas 渲染字号与字重识别**标题、古籍原文条文、方剂/重点引文、现代解读正文**，呈现出版级阅读体验。

---

## ✨ 核心特性与技术亮点

### 1. 攻克微信读书 Web 端「漏抓 40% 内容」的顽疾
许多基于 Playwright 的微信读书抓取脚本在默认的**上下滚动模式 (`isNormalReader`)** 下运行。由于微信读书在滚动模式下采用高达 `17,000px+` 的虚拟滚动分片容器，仅靠翻页键或固定视口抓取会导致每章下半部分（约 40% 内容）被直接跳过。
- 本工具自动检测并强制切换至 **双栏水平翻页模式 (`isHorizontalReader`)**；
- 结合 `CanvasRenderingContext2D.prototype.clearRect` 帧序列号与左右栏 (`left` / `right`) 样式属性，将每一次重绘精确拆分为独立单页，彻底消除跨章或短页同 `Y` 坐标文字交错乱码。

### 2. 智能识别「原文 / 方剂 / 现代解读」三层排版结构
通过拦截 `CanvasRenderingContext2D.prototype.fillText` 的实时 `ctx.font` 属性：
- **`>= 24.5px`**：自动识别为章节/小节标题，并支持跨行长标题智能合并；
- **`22.0px ~ 24.5px`**：识别为古籍条文/核心引文（如《伤寒论》398 条原文），自动提取生成朱砂红 **`第 X 条`** 徽章，采用 **14.8pt 大字号楷体 + 宣纸米底色卡片** 呈现；
- **`bold 18px`**：二次语义判别区分「经方组成与煎服法」与「正文内加粗重点句」，自动修复因画布折行导致的段中断句；
- **`18px` 常规**：识别为现代解读正文，采用 **13.2pt 苹方字体 (PingFang SC)** 舒适行距排版。

### 3. 一键输出四大格式
| 格式 | 适用场景 | 排版特色 |
| :--- | :--- | :--- |
| **精排 PDF (`.pdf`)** | iPad / 平板批注、桌面阅读、打印装订 | **苹方正文 + 楷体条文**、高清封面、可点击双栏目录、PDF 侧边栏书签大纲 (Outline)、朱砂红条文徽章、页眉页脚页码 |
| **双字体 EPUB (`.epub`)** | Apple Books / Kindle / 微信读书导入 | 内嵌 CSS 双字体样式（原文楷体 + 正文宋体），完整保留目录树与原书高清插图 |
| **纯 Markdown (`.md`)** | Obsidian / Notion / Logseq 知识库 | 古籍条文自动转为 `> **条文**` 引用块，零 HTML 标签污染，方便全文检索与双链笔记 |
| **HTML 标签版 Markdown (`.md`)** | 二次排版定制 | 保留 `<p class="yw">` 与 `<p class="fang">` 语义标签，方便自定义 CSS |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 第一步：抓取全书章节与插图

在微信读书网页版打开目标书籍，从浏览器地址栏获取末段的书籍 ID（例如 `https://weread.qq.com/web/reader/3b132980813ab94eeg013129` 中的 `3b132980813ab94eeg013129`）：

```bash
python crawl_weread.py 3b132980813ab94eeg013129
```

> **提示**：首次运行时会弹出 Chromium 窗口，请使用微信扫码登录您的微信读书账号。登录状态会自动保存在本地 `cache/browser_profile/` 目录中（已加入 `.gitignore`，不会上传），后续运行无需重复扫码。

### 3. 第二步：生成精排 PDF / EPUB / Markdown

```bash
python export_book.py 3b132980813ab94eeg013129
```

导出完成后，所有文件均保存在 `output/` 目录下。

---

## 🛠️ 工作原理简析

```mermaid
flowchart LR
    A["微信读书 Web 端\n(强制双栏翻页模式)"] --> B["Canvas 2D Hook\n拦截 fillText & clearRect"]
    B --> C["单页切分与去重\n按 (seq, side, y) 重建行"]
    C --> D["字号/字重语义分类\n标题 / 原文(yw) / 方剂(fang) / 正文"]
    D --> E["跨行断句修复\n& 原书插图下载"]
    E --> F["多格式渲染引擎\nPDF (苹方+楷体) / EPUB / Markdown"]
```

---

## ⚠️ 免责声明 (Disclaimer)

1. 本项目仅用于个人学习、无障碍大字号阅读辅助与前端 Canvas 渲染技术研究。
2. 请支持正版图书，仅对您个人合法拥有阅读权限（已购买或会员期内）的书籍使用本工具，导出的文件请勿用于任何商业用途或公开传播。
3. 本仓库不包含任何受版权保护的书籍内容或个人登录凭证（均已在 `.gitignore` 中排除）。

---

如果这个工具对你的学习与读书笔记整理有帮助，欢迎点亮一颗 **Star ⭐** 支持！
