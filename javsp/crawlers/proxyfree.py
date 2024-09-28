"""获取各个网站的免代理地址"""
from collections.abc import Callable, Coroutine
import re
import sys
from typing import Any, Dict

from pydantic_core import Url
from pydantic_extra_types.pendulum_dt import Duration
from lxml import html

from javsp.config import CrawlerID
from javsp.network.utils import test_connect
from javsp.network.client import get_client


async def _get_avsox_urls() -> list:
    link = 'https://tellme.pw/avsox'
    client = get_client(Url(link))
    resp = await client.get(link)
    tree = html.fromstring(resp.text)
    urls = tree.xpath('//h4/strong/a/@href')
    return urls


async def _get_javbus_urls() -> list:
    link = 'https://www.javbus.one/'
    client = get_client(Url(link))
    resp = await client.get(link)
    text = resp.text
    urls = re.findall(r'防屏蔽地址：(https://(?:[\d\w][-\d\w]{1,61}[\d\w]\.){1,2}[a-z]{2,})', text, re.I | re.A)
    return urls


async def _get_javlib_urls() -> list:
    link = 'https://github.com/javlibcom'
    client = get_client(Url(link))
    resp = await client.get(link)
    tree = html.fromstring(resp.text)
    text = tree.xpath("//div[@class='p-note user-profile-bio mb-3 js-user-profile-bio f4']")[0].text_content()
    match = re.search(r'[\w\.]+', text, re.A)
    if match:
        domain = f'https://www.{match.group(0)}.com'
        return [domain]


async def _get_javdb_urls() -> list:
    root_link = 'https://jav524.app'
    client = get_client(Url(root_link))
    resp = await client.get(root_link)
    tree = html.fromstring(resp.text)
    js_links = tree.xpath("//script[@src]/@src")
    for link in js_links:
        if '/js/index' in link:
            link = root_link + link
            resp = await client.get(link)
            text = resp.text
            match = re.search(r'\$officialUrl\s*=\s*"(https://(?:[\d\w][-\d\w]{1,61}[\d\w]\.){1,2}[a-z]{2,})"', text, flags=re.I | re.A)
            if match:
                return [match.group(1)]

proxy_free_fns: Dict[CrawlerID, Callable[[], Coroutine[Any, Any, list[str]]]]= {
        CrawlerID.avsox: _get_avsox_urls,
        CrawlerID.javdb: _get_javdb_urls,
        CrawlerID.javbus: _get_javbus_urls,
        CrawlerID.javlib: _get_javlib_urls,
}

def _choose_one(urls: list[str]) -> str:
    for url in urls:
        if test_connect(url, Duration(seconds=5)):
            return url
    return ''

async def get_proxy_free_url(site_name: CrawlerID, prefer_url: str | None=None) -> str:
    """获取指定网站的免代理地址
    Args:
        site_name (str): 站点名称
        prefer_url (str, optional): 优先测试此url是否可用
    Returns:
        str: 指定站点的免代理地址（失败时为空字符串）
    """
    if prefer_url and test_connect(prefer_url, Duration(seconds=5)):
        return prefer_url

    if site_name in proxy_free_fns:
        try:
            urls = await proxy_free_fns[site_name]()
            return _choose_one(urls)
        except:
            return ''
    else:
        raise Exception("Dont't know how to get proxy-free url for " + site_name)



if __name__ == "__main__":

    async def test_main():
        print('javdb:\t', await _get_javdb_urls())
        print('javlib:\t', await _get_javlib_urls())

    import asyncio
    asyncio.run(test_main())
