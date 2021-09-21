"""网络请求的统一接口"""
import os
import sys
import logging
import requests
import cloudscraper
import lxml.html
from lxml import etree
from lxml.html.clean import Cleaner
from requests.models import Response


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config import cfg


__all__ = ['Request', 'get_html', 'post_html', 'request_get', 'resp2html', 'is_connectable', 'download', 'get_resp_text']


headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36'}

logger = logging.getLogger(__name__)
# 删除js脚本相关的tag，避免网页检测到没有js运行环境时强行跳转，影响调试
cleaner = Cleaner(kill_tags=['script', 'noscript'])


# 与网络请求相关的功能汇总到一个模块中以方便处理，但是不同站点的抓取器又有自己的需求（针对不同网站
# 需要使用不同的UA、语言等）。每次都传递参数很麻烦，而且会面临函数参数越加越多的问题。因此添加这个
# 处理网络请求的类，它带有默认的属性，但是也可以在各个抓取器模块里进行进行定制
class Request():
    """作为网络请求出口并支持各个模块定制功能"""
    def __init__(self, use_scraper=False) -> None:
        # 必须使用copy()，否则各个模块对headers的修改都将会指向本模块中定义的headers变量，导致只有最后一个对headers的修改生效
        self.headers = headers.copy()
        self.cookies = {}
        self.proxies = cfg.Network.proxy
        self.timeout = cfg.Network.timeout
        if not use_scraper:
            self.scraper = None
            self.__get = requests.get
            self.__post = requests.post
        else:
            self.scraper = cloudscraper.create_scraper()
            self.__get = self.scraper.get
            self.__post = self.scraper.post

    def get(self, url, delay_raise=False):
        r = self.__get(url,
                      headers=self.headers,
                      proxies=self.proxies,
                      cookies=self.cookies,
                      timeout=self.timeout)
        if not delay_raise:
            r.raise_for_status()
        return r

    def post(self, url, data, delay_raise=False):
        r = self.__post(url,
                      data=data,
                      headers=self.headers,
                      proxies=self.proxies,
                      cookies=self.cookies,
                      timeout=self.timeout)
        if not delay_raise:
            r.raise_for_status()
        return r

    def get_html(self, url):
        r = self.get(url)
        html = resp2html(r)
        return html


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


def get_resp_text(resp: Response, encoding=None):
    """提取Response的文本"""
    if encoding:
        resp.encoding = encoding
    else:
        resp.encoding = resp.apparent_encoding
    return resp.text


def get_html(url):
    """使用get方法访问指定网页并返回经lxml解析后的document"""
    resp = request_get(url)
    text = get_resp_text(resp, encoding='utf-8')
    html = lxml.html.fromstring(text)
    html.make_links_absolute(url, resolve_base_href=True)
    # 清理功能仅应在需要的时候用来调试网页（如prestige），否则可能反过来影响调试（如JavBus）
    # html = cleaner.clean_html(html)
    # lxml.html.open_in_browser(html, encoding=encoding)  # for develop and debug
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
        logger.debug(f"Connectable: {url} HTTP {r.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        logger.debug(f"Not connectable: {url}\n" + repr(e))
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
    chrome = R'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    subprocess.run(f'"{chrome}" --profile-directory="Profile 2" {url}', shell=True)

import webbrowser
webbrowser.open = open_in_chrome


if __name__ == "__main__":
    print(is_connectable('http://www.baidu.com'))