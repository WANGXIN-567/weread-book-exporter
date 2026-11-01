#!/usr/bin/env python3
"""WeRead One-Click Book Exporter (main.py)

一键无损抓取并导出微信读书全格式电子书（PDF / EPUB / Markdown）

用法:
    python main.py <微信读书网页链接或书籍ID>

示例:
    python main.py https://weread.qq.com/web/reader/3b132980813ab94eeg013129
    python main.py 3b132980813ab94eeg013129
"""
import asyncio
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import crawl_weread
import export_book


def print_banner():
    print("""
===========================================================
  📚 WeRead Book Exporter - 微信读书全书无损一键导出工具
===========================================================
    """)


async def run(raw_input, force=False):
    book_id = crawl_weread.extract_book_id(raw_input)
    if not book_id:
        print("❌ 错误: 请输入有效的微信读书网页链接或书籍 ID！")
        print("👉 示例: python main.py https://weread.qq.com/web/reader/3b132980813ab94eeg013129")
        sys.exit(1)

    print(f"🚀 开始执行一键全流程导出，书籍 ID: {book_id}\n")

    # 第一步：完整抓取全书（支持真·断点续传与自愈复用）
    print("【步骤 1/2】抓取全书章节、插图与原版封面...")
    crawl_ok = await crawl_weread.main(book_id, force=force)
    if not crawl_ok:
        print("\n❌ 抓取未完成，导出终止。请检查网络或重新扫码。")
        sys.exit(1)

    # 第二步：一键多格式导出
    print("\n【步骤 2/2】正在生成精排 PDF、EPUB 与 Markdown 笔记...")
    export_ok = await export_book.main(book_id)
    if not export_ok:
        print("\n❌ 导出过程遇到错误，请检查日志。")
        sys.exit(1)

    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "output"))
    print("=" * 60)
    print(f"🎉 全部完成！导出的所有文件已保存在:\n👉 {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    print_banner()
    force_flag = any(arg in sys.argv for arg in ("--force", "-f"))
    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if not args:
        try:
            user_input = input("请输入微信读书网页链接或书籍 ID: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n已取消。")
            sys.exit(0)
        if not user_input:
            print("未输入有效链接或 ID，程序退出。")
            sys.exit(0)
    else:
        user_input = args[0].strip()

    asyncio.run(run(user_input, force=force_flag))
