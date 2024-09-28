import asyncio
import tracemalloc

from javsp.crawlers.proxyfree import get_proxy_free_url
from javsp.config import CrawlerID

def test_get_url():
    async def wrap():
        assert await get_proxy_free_url(CrawlerID.javlib) != None
        assert await get_proxy_free_url(CrawlerID.javdb) != None
    asyncio.run(wrap())


def test_get_url_with_prefer():
    async def wrap():
        prefer_url = 'https://www.baidu.com'
        assert prefer_url == await get_proxy_free_url(CrawlerID.javlib, prefer_url)
    asyncio.run(wrap())

if __name__ == "__main__":
    async def aentry():
        print(await get_proxy_free_url(CrawlerID.javlib))

    tracemalloc.start()
    asyncio.run(aentry(), debug=True)
