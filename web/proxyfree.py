"""获取各个网站的免代理地址"""
import re
import sys
import lxml.html

sys.path.append('../')
from web.base import get_html, is_connectable


def get_proxy_free_url(site_name: str) -> str:
    """获取指定网站的免代理地址"""
    site_name = site_name.lower()
    if site_name == 'avsox':
        return _choose_one(_get_avsox_urls())
    elif site_name == 'javbus':
        return _choose_one(_get_javbus_urls())
    elif site_name == 'javlib':
        return _choose_one(_get_javlib_urls())
    elif site_name == 'javdb':
        return _choose_one(_get_javdb_urls())
    else:
        raise Exception("Dont't know how to get proxy-free url for " + site_name)


def _choose_one(urls) -> str:
    for url in urls:
        if is_connectable(url):
            return url
    return ''


def _get_avsox_urls() -> list:
    resp = get_html('https://tellme.pw/avsox')
    html = lxml.html.fromstring(resp)
    urls = html.xpath('//h4/strong/a/@href')
    return urls


def _get_javbus_urls() -> list:
    resp = get_html('https://www.javbus.one/')
    html = lxml.html.fromstring(resp)
    text = html.text_content()
    urls = re.findall(r'防屏蔽地址：(https://(?:[\d\w][-\d\w]{1,61}[\d\w]\.){1,2}[a-z]{2,})', text, re.I | re.A)
    return urls


def _get_javlib_urls() -> list:
    resp = get_html('https://www.ebay.com/usr/javlibrary')
    html = lxml.html.fromstring(resp)
    text = html.xpath('//h2[@class="bio inline_value"]')[0].text_content()
    match = re.search(r'[\w\.]+', text, re.A)
    if match:
        domain = f'https://www.{match.group(0)}.com'
        return [domain]


def _get_javdb_urls() -> list:
    resp = get_html('https://lynnconway.me/javdbnews')
    html = lxml.html.fromstring(resp)
    text = html.xpath('//p[@class="text3"]')[0].text_content()
    urls = [i.strip() for i in text.split('/')]
    return urls


if __name__ == "__main__":
    print(get_proxy_free_url('javlib'))
