"""获取各个网站的免代理地址"""
import re
import sys
import lxml.html

sys.path.append('../')
from web.base import get_html, is_connectable


def get_proxy_free_url(site_name: str) -> str:
    """获取指定网站的免代理地址"""
    site_name = site_name.lower()
    if site_name == 'javbus':
        return _choose_one(_get_javbus_urls())
    elif site_name == 'javlib':
        return ''
    else:
        raise Exception("Dont't know how to get proxy-free url for " + site_name)


def _choose_one(urls) -> str:
    # 最后一个地址是永久地址，不测试它的连接情况
    for url in urls[:-1]:
        if is_connectable(url):
            return url
    return urls[-1]


def _get_javbus_urls() -> list:
    resp = get_html('https://www.javbus.one/')
    html = lxml.html.fromstring(resp)
    text = html.text_content()
    urls = re.findall(r'防屏蔽地址：(https://(?:[\d\w][-\d\w]{1,61}[\d\w]\.){1,2}[a-z]{2,})', text, re.I | re.A)
    # 始终将永久地址附加到最后
    urls.append('https://www.javbus.com/')
    return urls
    

if __name__ == "__main__":
    print(get_proxy_free_url('javbus'))
