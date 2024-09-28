from datetime import timedelta
import time
from tqdm.asyncio import tqdm
from typing import Any, Coroutine, NamedTuple
import aiofiles
from pretty_errors import os
from pydantic.types import ByteSize
from pydantic_core import Url

from pydantic_extra_types.pendulum_dt import Duration

from javsp.config import Cfg, CrawlerID
from javsp.network.client import get_client

import asyncio

class DownloadInfo(NamedTuple):
    size: ByteSize
    elapsed: timedelta

    def get_rate(self) -> float:
        """get rate of this download, unit: Mbps"""
        return self.size.to("mbit") / self.elapsed.total_seconds()

async def url_download(url: Url, target_path: str, desc: str | None = None) -> DownloadInfo:
    url_str = str(url)

    if url.scheme == 'file':
        path: str = url.path
        start_time: float = time.time()
        async with aiofiles.open(path, "rb") as src:
           async with aiofiles.open(target_path, "wb") as dest:
               await dest.write(await src.read())
        filesize = os.path.getsize(path)
        elapsed = time.time() - start_time
        return DownloadInfo(ByteSize(filesize), Duration(seconds=elapsed))

    if not desc:
        desc = url_str.split('/')[-1]

    client = get_client(url)

    # REF: https://www.python-httpx.org/advanced/clients/#monitoring-download-progress
    async with aiofiles.open(target_path, 'wb') as download_file:
        # NOTE: Create a client for each request for now, need further refactor
        async with client.stream("GET", url_str) as response:
            total = int(response.headers["Content-Length"])

            with tqdm(total=total, unit_scale=True, unit_divisor=1024, unit="B") as progress:
                num_bytes_downloaded = response.num_bytes_downloaded
                for chunk in response.iter_bytes():
                    await download_file.write(chunk)
                    progress.update(response.num_bytes_downloaded - num_bytes_downloaded)
                    num_bytes_downloaded = response.num_bytes_downloaded
            
            return DownloadInfo(ByteSize(response.num_bytes_downloaded), response.elapsed)

async def test_connect(url_str: str, timeout: Duration) -> bool:
    """测试与指定url的连接，不使用映射，但使用代理"""
    try:
        print(f"Attemping to connect {url_str}")
        client = get_client(Url(url_str))
        response = \
            await client.get(
                url_str,
                timeout=timeout.total_seconds(),
                follow_redirects=True,
            )
        return response.status_code == 200
    except:
        return False

async def choose_one_connectable(urls: list[str]) -> str | None:
    print(urls)
    co_connectables: list[Coroutine[Any, Any, bool]] = []
    for url in urls:
        co_connectables.append(test_connect(url, Duration(seconds=5)))

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
    # async def aentry():
    #     print(await choose_one_connectable(['http://iandown.what', 'http://www.baidu.com']))

    async def aentry():
        print(await test_connect("https://www.y78k.com/", timeout=3))

    asyncio.run(aentry())
