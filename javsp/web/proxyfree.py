"""获取各个网站的免代理地址"""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import *


def get_proxy_free_url(site_name: str, prefer_url=None) -> str:
    """获取指定网站的免代理地址
    Args:
        site_name (str): 站点名称
        prefer_url (str, optional): 优先测试此url是否可用
    Returns:
        str: 指定站点的免代理地址（失败时为空字符串）
    """
    if prefer_url and is_connectable(prefer_url, timeout=5):
        return prefer_url
    # 当prefer_url不可用时，尝试自动获取指定网站的免代理地址
    site_name = site_name.lower()
    func_name = f'_get_{site_name}_urls'
    get_funcs = [i for i in dir(sys.modules[__name__]) if i.startswith('_get_')]
    if func_name in get_funcs:
        get_urls = getattr(sys.modules[__name__], func_name)
        try:
            urls = get_urls()
            return _choose_one(urls)
        except:
            return ''
    else:
        raise Exception("Dont't know how to get proxy-free url for " + site_name)


def _choose_one(urls) -> str:
    for url in urls:
        if is_connectable(url, timeout=5):
            return url
    return ''


def _get_avsox_urls() -> list:
    html = get_html('https://tellme.pw/avsox')
    urls = html.xpath('//h4/strong/a/@href')
    return urls


def _get_javbus_urls() -> list:
    html = get_html('https://www.javbus.one/')
    text = html.text_content()
    urls = re.findall(r'防屏蔽地址：(https://(?:[\d\w][-\d\w]{1,61}[\d\w]\.){1,2}[a-z]{2,})', text, re.I | re.A)
    return urls


def _get_javlib_urls() -> list:
    html = get_html('https://github.com/javlibcom')
    text = html.xpath("//div[@class='p-note user-profile-bio mb-3 js-user-profile-bio f4']")[0].text_content()
    match = re.search(r'[\w\.]+', text, re.A)
    if match:
        domain = f'https://www.{match.group(0)}.com'
        return [domain]


def _get_javdb_urls() -> list:
    html = get_html('https://jav524.app')
    js_links = html.xpath("//script[@src]/@src")
    for link in js_links:
        if '/js/index' in link:
            text = get_resp_text(request_get(link))
            match = re.search(r'\$officialUrl\s*=\s*"(https://(?:[\d\w][-\d\w]{1,61}[\d\w]\.){1,2}[a-z]{2,})"', text, flags=re.I | re.A)
            if match:
                return [match.group(1)]


if __name__ == "__main__":
    print('javdb:\t', _get_javdb_urls())
    print('javlib:\t', _get_javlib_urls())
