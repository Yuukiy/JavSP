# -*- coding: utf-8 -*-
"""
搜索 missav.ai 并缓存目标详情页
注意事项：无法从主程序获取代理（我不会）；所以必须自行添加DEFAULT_PROXY值保证连接。
这个脚本可以独立运行，输入番号即可缓存相应影片番号的搜索页面和影片的详细页面。

改动概要：
1) keyword 兼容两种来源：
   - 其它脚本唤起时通过命令行参数传入（full_id）
   - 若未传，则在本脚本里手动输入
2) 代理使用脚本内的默认设置 DEFAULT_PROXY，无需输入

依赖:
    pip install playwright beautifulsoup4 lxml cloudscraper requests
    python -m playwright install chromium
"""

import os
import re
import sys
import time
import pathlib
import traceback
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# 可选模块，按可用性启用
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except Exception:
    CLOUDSCRAPER_AVAILABLE = False

import requests

# ===================== 配置区 =====================
MISSAV_HOST = "https://missav.ai"
SEARCH_TEMPLATE = "https://missav.ai/ja/search/{keyword}"

# ✅ 默认代理：改成你的实际代理地址；若不想用代理，留空字符串""即可
DEFAULT_PROXY = "http://192.168.31.66:10808"   # ←←← 修改这里

# （暂时无效）如果你想优先使用系统环境变量代理，把下方开关设为 True 
USE_ENV_PROXY_IF_SET = True
# =================================================

CACHE_DIR = pathlib.Path("./cache")
LOG_FILE = CACHE_DIR / "missav_run.log"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _ua() -> str:
    return ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36")


def build_proxies() -> Optional[dict]:
    """
    使用默认代理，无需输入。
    若 USE_ENV_PROXY_IF_SET=True 且环境变量存在，则优先用环境变量。
    """
    if USE_ENV_PROXY_IF_SET:
        http_env = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        https_env = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if http_env or https_env:
            proxies = {"http": http_env or https_env, "https": https_env or http_env}
            log(f"使用环境变量代理：{proxies}")
            return proxies

    if DEFAULT_PROXY:
        proxies = {"http": DEFAULT_PROXY, "https": DEFAULT_PROXY}
        log(f"使用默认代理：{proxies}")
        return proxies

    log("未设置代理。")
    return None


def is_target_link(href: str, keyword: str) -> bool:
    if not href:
        return False
    # 绝对化
    if href.startswith("//"):
        href = "https:" + href
    elif href.startswith("/"):
        href = urljoin(MISSAV_HOST, href)

    try:
        u = urlparse(href)
    except Exception:
        return False

    # 仅 missav.ai 域名
    if u.netloc and u.netloc.lower() not in ("missav.ai", "www.missav.ai"):
        return False

    path_lower = (u.path or "").lower()
    # 必须包含关键词，且不含 /search/
    if keyword.lower() not in path_lower:
        return False
    if "/search/" in path_lower:
        return False
    return True


def to_abs(href: str) -> str:
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return urljoin(MISSAV_HOST, href)
    return href


def pick_first_target(links: List[str], keyword: str) -> Optional[str]:
    for href in links:
        if is_target_link(href, keyword):
            return to_abs(href)
    return None


def extract_links_from_html(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    links = [a.get("href", "").strip() for a in soup.select("a[href]")]
    return [h for h in links if h]


def save_cache(html: str, keyword: str, suffix: str) -> pathlib.Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    safe_kw = re.sub(r"[^\w\-]+", "_", keyword.strip())
    out = CACHE_DIR / f"{safe_kw}_{suffix}_{ts}.html"
    out.write_text(html, encoding="utf-8", errors="ignore")
    log(f"缓存文件已保存：{out}")
    return out


# ---------------- 方案一：Playwright ----------------
def fetch_with_playwright(search_url: str, keyword: str, proxies: Optional[dict]) -> Optional[str]:
    if not PLAYWRIGHT_AVAILABLE:
        log("Playwright 不可用，跳过方案一。")
        return None

    pw_proxy = None
    if proxies and (proxies.get("https") or proxies.get("http")):
        pw_proxy = {"server": proxies.get("https") or proxies.get("http")}

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, proxy=pw_proxy)
            context = browser.new_context(locale="ja-JP", user_agent=_ua())
            page = context.new_page()
            page.set_extra_http_headers({
                "Accept-Language": "ja,en;q=0.9,zh;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            })

            log(f"[PW] 打开搜索页：{search_url}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            # 滚动触发懒加载/通过CF
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1200)

            search_html = page.content()
            save_cache(search_html, keyword, "search")

            links = extract_links_from_html(search_html)
            # 兜底：文本里再扫一轮直链
            links += re.findall(r'https?://(?:www\.)?missav\.ai/[^\s"\'<>]+', search_html, flags=re.I)
            target = pick_first_target(links, keyword)

            if not target:
                log("[PW] 未找到符合规则的详情链接（包含关键词且不含 /search/）。")
                context.close()
                browser.close()
                return None

            log(f"[PW] 发现目标链接：{target}")
            page.goto(target, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            detail_html = page.content()
            save_cache(detail_html, keyword, "detail")

            context.close()
            browser.close()
            return target

    except Exception as e:
        log(f"[PW] 失败：{e}")
        traceback.print_exc()
        return None


# --------------- 方案二：cloudscraper/requests ---------------
def fetch_with_requests(search_url: str, keyword: str, proxies: Optional[dict]) -> Optional[str]:
    if CLOUDSCRAPER_AVAILABLE:
        sess = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        log("[REQ] 使用 cloudscraper。")
    else:
        sess = requests.Session()
        log("[REQ] 使用 requests。")

    if proxies:
        sess.proxies.update(proxies)

    sess.headers.update({
        "User-Agent": _ua(),
        "Accept-Language": "ja,en;q=0.9,zh;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    try:
        log(f"[REQ] 打开搜索页：{search_url}")
        r = sess.get(search_url, timeout=60)
        r.raise_for_status()
        search_html = r.text
        save_cache(search_html, keyword, "search")

        links = extract_links_from_html(search_html)
        links += re.findall(r'href=["\']([^"\']+)["\']', search_html, flags=re.I)
        links += re.findall(r'https?://(?:www\.)?missav\.ai/[^\s"\'<>]+', search_html, flags=re.I)
        target = pick_first_target(links, keyword)

        if not target:
            log("[REQ] 未找到符合规则的详情链接（包含关键词且不含 /search/）。")
            return None

        log(f"[REQ] 发现目标链接：{target}")
        r2 = sess.get(target, timeout=60)
        r2.raise_for_status()
        detail_html = r2.text
        save_cache(detail_html, keyword, "detail")
        return target

    except Exception as e:
        log(f"[REQ] 失败：{e}")
        traceback.print_exc()
        return None


def get_keyword_from_argv_or_input() -> Optional[str]:
    """
    优先从命令行参数读取（供其它脚本唤起，传 full_id）。
    若无参数，则在本脚本里手动输入。
    """
    if len(sys.argv) >= 2:
        kw = sys.argv[1].strip()
        if kw:
            log(f"收到命令行参数 keyword：{kw}")
            return kw

    print("请输入搜索关键词（例如：zuko-118）：")
    kw = input("> ").strip()
    if kw:
        return kw
    return None


def main():
    try:
        keyword = get_keyword_from_argv_or_input()
        if not keyword:
            print("未提供关键词，退出。")
            return

        search_url = SEARCH_TEMPLATE.format(keyword=keyword)
        log(f"搜索URL：{search_url}")

        proxies = build_proxies()

        target_url = None
        if PLAYWRIGHT_AVAILABLE:
            target_url = fetch_with_playwright(search_url, keyword, proxies)

        if not target_url:
            target_url = fetch_with_requests(search_url, keyword, proxies)

        if target_url:
            log(f"完成。目标链接：{target_url}")
            print(f"\n完成 ✅ 目标链接：{target_url}\n缓存目录：{CACHE_DIR.resolve()}")
        else:
            log("未能获取目标链接或缓存详情页。")
            print("\n未能获取目标链接或缓存详情页。详见日志：", LOG_FILE.resolve())

    except Exception as e:
        log(f"[FATAL] {e}")
        traceback.print_exc()
        print("\n发生致命错误，详见日志：", LOG_FILE.resolve())


if __name__ == "__main__":
    main()
