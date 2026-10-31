#!/usr/bin/env python3
"""WeRead Canvas Full-Book Crawler (crawl_weread.py)

核心特性：
1. 自动检测并切换至【双栏水平翻页模式 (isHorizontalReader)】，彻底解决微信读书 Web 端在上下滚动模式下因虚拟滚动高度截断导致每章下半部分丢失 ~40% 内容的问题。
2. 注入 Canvas 2D Context Hook (fillText + clearRect)，利用左/右栏坐标与帧序列号精确切分每一单页，消除短页与跨章同 Y 坐标文字交错。
3. 自动识别画布字号与字重层级（标题 / 古籍条文引文 / 加粗方剂或小标题 / 正文），并自动下载原书全部插图与封面。

用法:
    python crawl_weread.py <book_id>
"""
import asyncio
import collections
import json
import os
import re
import sys
import time
import urllib.request

from playwright.async_api import async_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(BASE, "cache", "browser_profile")
DEFAULT_BOOK_ID = "3b132980813ab94eeg013129"

HOOK = """
(function() {
    window.__wr_chars = [];
    window.__wr_seq = 0;
    var origClear = CanvasRenderingContext2D.prototype.clearRect;
    CanvasRenderingContext2D.prototype.clearRect = function(x, y, w, h) {
        if (w > 100 && h > 100) window.__wr_seq++;
        return origClear.apply(this, arguments);
    };
    var origFill = CanvasRenderingContext2D.prototype.fillText;
    CanvasRenderingContext2D.prototype.fillText = function(text, x, y) {
        if (text && text.trim()) {
            var st = (this.canvas && this.canvas.getAttribute('style')) || '';
            var side = st.includes('right:') ? 1 : 0;
            window.__wr_chars.push({
                t: text,
                x: Math.round(x * 10) / 10,
                y: Math.round(y * 10) / 10,
                f: String(this.font),
                side: side,
                seq: window.__wr_seq
            });
        }
        return origFill.apply(this, arguments);
    };
    window.__wr_drain = function() {
        var out = window.__wr_chars;
        window.__wr_chars = [];
        return out;
    };
    window.__wr_count = function() { return window.__wr_chars.length; };
})();
"""

IMGS_JS = """
() => {
    const H = window.innerHeight, W = window.innerWidth, out = [];
    document.querySelectorAll('img[class*="wr_readerImage"]').forEach(i => {
        const src = i.src || i.getAttribute('data-src') || '';
        if (!src.includes('res.weread.qq.com/wrepub')) return;
        const r = i.getBoundingClientRect();
        if (r.width > 40 && r.height > 40 && r.bottom > 0 && r.top < H &&
            r.right > 0 && r.left < W &&
            getComputedStyle(i).visibility !== 'hidden' && getComputedStyle(i).display !== 'none')
            out.push({src, top: Math.round(r.top), left: Math.round(r.left)});
    });
    return out;
}
"""

MEASURE_RE = re.compile(r'^[a-zA-Z`~!@#$%^&*()\-_=+\[\]{}|;:\',<.>/?\\"\s]{2,}$')
SENT_END_RE = re.compile(r"[。！？；：…][”」）】》]*$")


def norm(s):
    return re.sub(r"\s+", "", (s or "").replace("\u200b", ""))


def size_of(f):
    m = re.search(r"([\d.]+)px", f or "")
    return float(m.group(1)) if m else 0.0


def cls_of(f):
    s = size_of(f)
    if s >= 24.5:
        return "title"
    if s >= 22.0:
        return "yw"
    if "bold" in (f or ""):
        return "fang"
    return "js"


def split_pages(chars):
    """按 (seq, side) 以及 y 坐标回跳切分为独立单页"""
    real = []
    for c in chars:
        t = c["t"].replace("\u200b", "")
        if not t.strip():
            continue
        if t.startswith("abcdefg"):
            continue
        if len(t) > 1 and MEASURE_RE.match(t):
            continue
        c = dict(c)
        c["t"] = t
        real.append(c)

    if not real:
        return []

    pages = []
    cur = []
    cur_key = None
    last_y = -1.0

    for c in real:
        key = (c["seq"], c["side"])
        if cur_key is None:
            cur_key = key
            cur = [c]
            last_y = c["y"]
            continue
        if key != cur_key or (len(c["t"]) == 1 and last_y > 250 and c["y"] < last_y - 80):
            if cur:
                pages.append((cur_key[1], cur))
            cur = [c]
            cur_key = key
            last_y = c["y"]
        else:
            cur.append(c)
            if len(c["t"]) == 1:
                last_y = c["y"]
    if cur:
        pages.append((cur_key[1], cur))
    return pages


def page_lines(chars):
    rows = {}
    for c in chars:
        rows.setdefault(round(c["y"] / 3) * 3, []).append(c)
    raw_lines = []
    for yk in sorted(rows):
        row = sorted(rows[yk], key=lambda c: c["x"])
        text = "".join(c["t"] for c in row).strip()
        if not text:
            continue
        f = collections.Counter(c["f"] for c in row).most_common(1)[0][0]
        raw_lines.append({"y": yk, "text": text, "cls": cls_of(f), "size": round(size_of(f), 1)})

    out = []
    for ln in raw_lines:
        if (out and out[-1]["cls"] == "title" and ln["cls"] == "title"
                and out[-1]["size"] == ln["size"] and ln["y"] - out[-1]["y"] < 55):
            out[-1]["text"] += ln["text"]
            out[-1]["y"] = ln["y"]
        else:
            out.append(ln)
    return out


def render_md(title, blocks, ch_idx):
    out = ["# %s\n" % title]
    buf, buf_cls = [], None
    img_n = 0

    def flush():
        nonlocal buf, buf_cls
        if not buf:
            buf_cls = None
            return
        if buf_cls == "js":
            merged = []
            for line in buf:
                if merged and merged[-1] and not SENT_END_RE.search(merged[-1]):
                    merged[-1] += line
                else:
                    merged.append(line)
            for m in merged:
                if m.strip():
                    out.append(m.strip())
                    out.append("")
        elif buf_cls == "yw":
            joined = "".join(buf)
            for p in re.split(r"(?<=[。！？；”」])(?=\d{1,3}[^\d])", joined):
                if p.strip():
                    out.append('<p class="yw">%s</p>' % p.strip())
                    out.append("")
        elif buf_cls == "fang":
            for line in buf:
                if line.strip():
                    out.append('<p class="fang">%s</p>' % line.strip())
                    out.append("")
        buf, buf_cls = [], None

    imgs = []
    for b in blocks:
        if b["type"] == "img":
            flush()
            img_n += 1
            ext = "jpg"
            m = re.search(r"\.(jpg|jpeg|png|gif|webp)", b["src"].lower())
            if m:
                ext = m.group(1).replace("jpeg", "jpg")
            name = "ch%04d_img%02d.%s" % (ch_idx, img_n, ext)
            out.append("![图](images/%s)\n" % name)
            imgs.append({"src": b["src"], "name": name})
            continue
        if b["cls"] != buf_cls:
            flush()
            buf_cls = b["cls"]
        buf.append(b["text"])
    flush()
    return "\n".join(out).rstrip() + "\n", imgs


async def wait_stable_chars(page, timeout=6.0):
    t0 = time.time()
    last_n = 0
    stable_ticks = 0
    while time.time() - t0 < timeout:
        try:
            n = await page.evaluate("() => window.__wr_count()")
        except Exception:
            n = 0
        if n > 0:
            if n == last_n:
                stable_ticks += 1
                if stable_ticks >= 2:
                    return n
            else:
                last_n = n
                stable_ticks = 0
        await asyncio.sleep(0.18)
    return last_n


async def main(book_id):
    book_dir = os.path.join(BASE, "output", book_id + "_v2")
    md_dir = os.path.join(book_dir, "chapters")
    raw_dir = os.path.join(book_dir, "raw")
    img_dir = os.path.join(book_dir, "images")

    for d in (md_dir, raw_dir):
        os.makedirs(d, exist_ok=True)
        for fn in os.listdir(d):
            fp = os.path.join(d, fn)
            if os.path.isfile(fp):
                os.remove(fp)
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(USER_DATA_DIR, exist_ok=True)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=False, viewport={"width": 1200, "height": 900},
            args=["--disable-blink-features=AutomationControlled"])
        page = await ctx.new_page()
        await page.add_init_script(HOOK)
        await page.goto("https://weread.qq.com/web/reader/%s" % book_id,
                        wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # 若未登录，等待用户扫码登录
        if await page.locator("text=登录").count() > 0 and await page.locator(".readerControls_item.catalog").count() == 0:
            print("请在弹出的浏览器窗口中扫码登录微信读书（限时 120 秒）...", flush=True)
            for _ in range(60):
                await asyncio.sleep(2)
                if await page.locator(".readerControls_item.catalog").count() > 0:
                    break

        # 强制切换为双栏水平翻页模式
        if await page.locator("button.readerControls_item.isNormalReader").count() > 0:
            print("切换至双栏翻页模式...", flush=True)
            await page.click("button.readerControls_item.isNormalReader")
            await asyncio.sleep(4)

        # 提取书籍标题等元数据
        book_title = (await page.title()).replace(" - 微信读书", "").strip()
        meta_file = os.path.join(book_dir, "meta.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({"title": book_title, "book_id": book_id}, f, ensure_ascii=False, indent=2)

        # 读取目录并跳回第 0 项
        await page.click("button.readerControls_item.catalog", timeout=8000)
        await asyncio.sleep(1.5)
        items = page.locator(".readerCatalog_list_item")
        n = await items.count()
        catalog = []
        for i in range(n):
            txt = (await items.nth(i).inner_text()).strip().replace("\n", " ")
            txt = re.sub(r"\s*当前读到.*$", "", txt).strip()
            catalog.append(txt)
        with open(os.path.join(book_dir, "_catalog.json"), "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        print("目录共 %d 项: %s ... %s" % (n, catalog[:3], catalog[-2:]), flush=True)

        if n > 2:
            await items.nth(2).click(timeout=5000)
            await asyncio.sleep(2.0)
            if not await page.locator(".readerCatalog_list_item").first.is_visible():
                await page.click("button.readerControls_item.catalog", timeout=5000)
                await asyncio.sleep(1.0)
        it0 = items.nth(0)
        await it0.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)
        await page.evaluate("() => window.__wr_drain()")
        await it0.click(timeout=5000)
        await asyncio.sleep(2.5)
        try:
            if await page.locator(".readerCatalog_list_item").first.is_visible():
                await page.click("button.readerControls_item.catalog", timeout=2000)
        except Exception:
            await page.keyboard.press("Escape")
        await asyncio.sleep(1.0)

        sections = []
        cur_title = catalog[0] if catalog else "扉页"
        buf = []
        stale = 0
        seen_last = False
        last_after_seen = 0
        last_cat = norm(catalog[-1]) if catalog else ""
        seen_page_sigs = set()
        seen_imgs = set()

        for step in range(1200):
            if step > 0:
                await page.mouse.click(600, 450)
                await page.keyboard.press("ArrowRight")
                await asyncio.sleep(0.35)

            ok = await wait_stable_chars(page, timeout=2.2 if step > 0 else 5.0)
            chars = await page.evaluate("() => window.__wr_drain()") if ok else []
            imgs = await page.evaluate(IMGS_JS)

            pages = split_pages(chars)
            left_imgs = [im for im in imgs if im["left"] < 600]
            right_imgs = [im for im in imgs if im["left"] >= 600]

            got_any = False
            for side, pchars in pages:
                lines = page_lines(pchars)
                if not lines:
                    continue
                sig = norm("".join(ln["text"] for ln in lines))
                if len(sig) > 8 and sig in seen_page_sigs:
                    continue
                if len(sig) > 8:
                    seen_page_sigs.add(sig)
                got_any = True

                for ln in lines:
                    if ln["cls"] == "title":
                        t = ln["text"].strip()
                        if norm(t) != norm(cur_title):
                            if buf:
                                sections.append((cur_title, buf))
                            buf = []
                            cur_title = t
                            print("  ▶ [step %3d] %s" % (step, t), flush=True)
                            if last_cat and norm(t) == last_cat:
                                seen_last = True
                        continue
                    if buf and buf[-1]["type"] == "line" and buf[-1]["text"] == ln["text"] \
                            and buf[-1]["cls"] == ln["cls"]:
                        continue
                    buf.append({"type": "line", "cls": ln["cls"], "text": ln["text"]})

                side_imgs = left_imgs if side == 0 else right_imgs
                for im in side_imgs:
                    if im["src"] not in seen_imgs:
                        seen_imgs.add(im["src"])
                        buf.append({"type": "img", "src": im["src"]})
                        got_any = True

            if not pages and imgs:
                for im in imgs:
                    if im["src"] not in seen_imgs:
                        seen_imgs.add(im["src"])
                        buf.append({"type": "img", "src": im["src"]})
                        got_any = True

            if got_any:
                stale = 0
                if seen_last:
                    last_after_seen += 1
                    if last_after_seen >= 4:
                        print("  末章已抓完，结束", flush=True)
                        break
            else:
                stale += 1
                if seen_last and stale >= 2:
                    print("  已达末章且无新内容，结束", flush=True)
                    break
                if stale >= 8:
                    print("  连续 %d 页无新内容，结束" % stale, flush=True)
                    break

        if cur_title and buf:
            sections.append((cur_title, buf))

        merged_sections = []
        for t, b in sections:
            if merged_sections and norm(merged_sections[-1][0]) == norm(t):
                merged_sections[-1][1].extend(b)
            else:
                merged_sections.append((t, b))

        print("\n共捕获 %d 节:" % len(merged_sections), flush=True)
        total = 0
        saved_idx = 0
        for t, blocks in merged_sections:
            saved_idx += 1
            body, im_list = render_md(t, blocks, saved_idx)
            txt_len = len(re.sub(r"<[^>]+>", "", body))
            if txt_len < 15 and not im_list:
                saved_idx -= 1
                continue
            with open(os.path.join(md_dir, "%04d.md" % saved_idx), "w", encoding="utf-8") as f:
                f.write(body)
            with open(os.path.join(raw_dir, "%04d.json" % saved_idx), "w", encoding="utf-8") as f:
                json.dump({"title": t, "images": im_list, "text_len": txt_len}, f, ensure_ascii=False)
            total += txt_len
            print("  [%02d] %-30s %6d字 %d图" % (saved_idx, t[:30], txt_len, len(im_list)), flush=True)
        print("全书合计 %d 字，%d 节" % (total, saved_idx), flush=True)
        await ctx.close()

    tasks = []
    for jf in sorted(os.listdir(raw_dir)):
        if jf.endswith(".json"):
            with open(os.path.join(raw_dir, jf), encoding="utf-8") as f:
                for im in json.load(f).get("images", []):
                    tasks.append((im["src"], im["name"]))
    ok_img = 0
    for url, name in tasks:
        fp = os.path.join(img_dir, name)
        if os.path.exists(fp) and os.path.getsize(fp) > 500:
            ok_img += 1
            continue
        try:
            req = urllib.request.Request(url, headers={
                "Referer": "https://weread.qq.com/", "User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=20).read()
            if len(raw) > 500:
                with open(fp, "wb") as f:
                    f.write(raw)
                ok_img += 1
        except Exception as e:
            print("  图片下载失败 %s: %s" % (name, e), flush=True)
    print("图片下载完成: %d/%d" % (ok_img, len(tasks)), flush=True)


if __name__ == "__main__":
    bid = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BOOK_ID
    asyncio.run(main(bid))
