"""网络请求的统一接口"""

from typing import Dict
from pydantic_core import Url

from httpx import AsyncClient, AsyncHTTPTransport

from javsp.config import Cfg

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}

def get_proxy(unproxied: bool):
    if Cfg().network.proxy_server is None or unproxied:
        return None
    else:
        return str(Cfg().network.proxy_server)

client_dictionary: Dict[str, AsyncClient] = {}
def get_client(url: Url) -> AsyncClient:
    if url.host is None:
        raise Exception(f"Unknown url {url}")
    else:
        index = url.host
        if index in client_dictionary:
            return client_dictionary[index]
        else:
            unproxied = url.host in Cfg().network.unproxied

            transport = AsyncHTTPTransport(
                    proxy=get_proxy(unproxied), 
                    retries=Cfg().network.retries)

            client = AsyncClient(
                transport=transport,
                # 必须使用copy()，否则各个模块对headers的修改都将会指向本模块中定义的headers变量，导致只有最后一个对headers的修改生效
                headers=headers.copy(),
                timeout=Cfg().network.timeout.total_seconds(),
                follow_redirects=True,
            )

            client_dictionary[index] = client

            return client
