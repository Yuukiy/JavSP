"""网络请求的统一接口"""
import os
import sys
import requests
import cloudscraper
import lxml.html
from lxml import etree
from lxml.html.clean import Cleaner
from requests.models import Response


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config import cfg


__all__ = ['get_html', 'post_html', 'request_get', 'resp2html', 'is_connectable', 'download', 'get_resp_text']


headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36'}

scraper = cloudscraper.create_scraper()
# 删除js脚本相关的tag，避免网页检测到没有js运行环境时强行跳转，影响调试
cleaner = Cleaner(kill_tags=['script', 'noscript'])


def request_get(url, cookies={}, timeout=cfg.Network.timeout, delay_raise=False):
    """获取指定url的原始请求"""
    r = requests.get(url, headers=headers, proxies=cfg.Network.proxy, cookies=cookies, timeout=timeout)
    if not delay_raise:
        r.raise_for_status()
    return r


def request_post(url, data, cookies={}, timeout=cfg.Network.timeout, delay_raise=False):
    """向指定url发送post请求"""
    r = requests.post(url, data=data, headers=headers, proxies=cfg.Network.proxy, cookies=cookies, timeout=timeout)
    if not delay_raise:
        r.raise_for_status()
    return r


def scraper_get(url, cookies={}, timeout=cfg.Network.timeout, delay_raise=False):
    """使用cloudscraper访问指定url并返回原始请求"""
    r = scraper.get(url, headers=headers, proxies=cfg.Network.proxy, cookies=cookies, timeout=timeout)
    if not delay_raise:
        r.raise_for_status()
    return r


def get_resp_text(resp: Response, encoding=None):
    """提取Response的文本"""
    if encoding:
        resp.encoding = encoding
    else:
        resp.encoding = resp.apparent_encoding
    return resp.text


def get_html(url, encoding='utf-8', cookies={}, attach_raw=False, use_scraper=False):
    """使用get方法访问指定网页并返回经lxml解析后的document"""
    if use_scraper:
        resp = scraper_get(url, cookies=cookies)
    else:
        resp = request_get(url, cookies=cookies)
    text = get_resp_text(resp, encoding=encoding)
    html = lxml.html.fromstring(text)
    html.make_links_absolute(url, resolve_base_href=True)
    # 清理功能仅应在需要的时候用来调试网页（如prestige），否则可能反过来影响调试（如JavBus）
    # html = cleaner.clean_html(html)
    # lxml.html.open_in_browser(html, encoding=encoding)  # for develop and debug
    if attach_raw:
        # 部分情况下需要获得原始的request请求，但是为了统一管理网络出口，又不便在别的模块里使用requests
        return html, resp
    else:
        return html


def resp2html(resp, encoding='utf-8'):
    """将request返回的response转换为经lxml解析后的document"""
    text = get_resp_text(resp, encoding=encoding)
    html = lxml.html.fromstring(text)
    html.make_links_absolute(resp.url, resolve_base_href=True)
    # html = cleaner.clean_html(html)
    # lxml.html.open_in_browser(html, encoding=encoding)  # for develop and debug
    return html


def post_html(url, data, encoding='utf-8', cookies={}):
    """使用post方法访问指定网页并返回经lxml解析后的document"""
    resp = request_post(url, data, cookies=cookies)
    text = get_resp_text(resp, encoding=encoding)
    html = lxml.html.fromstring(text)
    html.make_links_absolute(url, resolve_base_href=True)
    # html = cleaner.clean_html(html)
    # lxml.html.open_in_browser(html, encoding=encoding)  # for develop and debug
    return html


def dump_xpath_node(node, filename=None):
    """将xpath节点dump到文件"""
    if not filename:
        filename = node.tag + '.html'
    with open(filename, 'wt', encoding='utf-8') as f:
        content = etree.tostring(node, pretty_print=True).decode('utf-8')
        f.write(content)


def is_connectable(url, timeout=3):
    """测试与指定url的连接"""
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False


def download(url, file):
    """下载指定url的资源"""
    r = requests.get(url, headers=headers, proxies=cfg.Network.proxy)
    r.raise_for_status()
    with open(file, 'wb') as f:
        f.write(r.content)


def open_in_chrome(url, new=0, autoraise=True):
    """使用指定的Chrome Profile打开url，便于调试"""
    import subprocess
    chrome = 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    subprocess.run(f'"{chrome}" --profile-directory="Profile 2" {url}', shell=True)

# import webbrowser
# webbrowser.open = open_in_chrome


if __name__ == "__main__":
    print(is_connectable('http://www.baidu.com'))