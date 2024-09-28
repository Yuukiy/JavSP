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

# def resp2html(resp: Response) -> lxml.html.HtmlElement:
#
#     """将request返回的response转换为经lxml解析后的document"""
#
#     html = lxml.html.fromstring(resp.text)
#     html.make_links_absolute(str(resp.url), resolve_base_href=True)
#     return html
#
async def test_connect(url_str: str, timeout: Duration) -> bool:
    """测试与指定url的连接，不使用映射，但使用代理"""
    try:

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

async def resolve_site_fallback(cr_id: CrawlerID, default: str) -> Url:
    if cr_id not in Cfg().network.fallback:
        return Url(default)
    
    tasks: list[tuple[str, Coroutine[Any, Any, bool]]] = []
    for fallback in Cfg().network.fallback[cr_id]:
        tasks.append((fallback, test_connect(fallback, Duration(seconds=3))))

    for (fallback, task) in tasks:
        if await task:
            return Url(fallback)

    return Url(default)
