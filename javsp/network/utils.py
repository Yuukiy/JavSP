from datetime import timedelta
import logging
import time
from aiohttp import ClientTimeout
from tqdm.asyncio import tqdm
from typing import Any, Coroutine, NamedTuple
import aiofiles
from pydantic.types import ByteSize
from pydantic_core import Url

from pydantic_extra_types.pendulum_dt import Duration

from javsp.config import Cfg, CrawlerID
from javsp.network.client import get_session, clear_clients

import asyncio

logger = logging.getLogger(__name__)

class DownloadInfo(NamedTuple):
    size: ByteSize
    elapsed: timedelta

    def get_rate(self) -> float:
        """get rate of this download, unit: Mbps"""
        return self.size.to("mbit") / self.elapsed.total_seconds()

async def url_download(url: Url, target_path: str, desc: str | None = None) -> DownloadInfo:
    url_str = str(url)

    if not desc:
        desc = url_str.split('/')[-1]

    s = get_session(url)

    # REF: https://www.python-httpx.org/advanced/clients/#monitoring-download-progress
    async with aiofiles.open(target_path, 'wb') as download_file:
        # NOTE: Create a client for each request for now, need further refactor

        start = time.monotonic()
        async with s.get(url_str) as response:
            total = response.content_length

            with tqdm(total=total, unit_scale=True, unit_divisor=1024, unit="B") as progress:
                async for chunk in response.content.iter_any():
                    await download_file.write(chunk)
                    progress.update(len(chunk))
            
            response_time = time.monotonic() - start
            return DownloadInfo(ByteSize(total), timedelta(seconds=response_time))

async def test_connect(url_str: str, timeout: Duration) -> bool:
    """测试与指定url的连接，不使用映射，但使用代理"""
    try:
        s = get_session(Url(url_str))
        response = \
            await s.get(
                url_str,
                timeout=ClientTimeout(total=timeout.total_seconds()),
            )
        return response.status == 200
    except Exception as e:
        logger.debug(f"Not connectable: {url_str}\n" + repr(e))
        return False

async def choose_one_connectable(urls: list[str]) -> str | None:
    co_connectables: list[Coroutine[Any, Any, bool]] = []
    for url in urls:
        co_connectables.append(test_connect(url, Duration(seconds=3)))

    connectables = await asyncio.gather(*co_connectables)
    for i, connectable in enumerate(connectables):
        if connectable:
            return urls[i]
    return None

async def resolve_site_fallback(cr_id: CrawlerID, default: str) -> Url:
    if cr_id not in Cfg().network.fallback:
        return Url(default)

    fallbacks = Cfg().network.fallback[cr_id]
    chosen = await choose_one_connectable(fallbacks)
    if chosen is None:
        return Url(default)
    else:
        return Url(chosen)


if __name__ == '__main__':
    async def aentry():
        print(await choose_one_connectable(['http://iandown.what', 'http://www.baidu.com']))
        from javsp.network.client import clear_clients
        await clear_clients()

    # async def aentry():
    #     print(await test_connect("https://www.y78k.com/", Duration(seconds=3)))

    # async def aentry():
    #     await asyncio.gather(
    #         url_download(Url('https://www.google.com/images/branding/googlelogo/2x/googlelogo_light_color_272x92dp.png'), 'gogle_logo.png'),
    #     url_download(Url('https://ei.phncdn.com/www-static/images/pornhub_logo_straight.svg?cache=2024092501'), 'pornhub_logo.svg'),
    #     )
    #     await clear_clients()

    asyncio.run(aentry())
