"""网络请求的统一接口"""

from typing import Any, Coroutine, Dict
from pydantic_core import Url

from javsp.config import Cfg
from aiohttp import BaseConnector, ClientSession, TCPConnector
from aiohttp_socks import ProxyConnector
import asyncio

default_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

def get_proxy(unproxied: bool):
    if Cfg().network.proxy_server is None or unproxied:
        return None
    else:
        return str(Cfg().network.proxy_server)

session_dictionary: Dict[str, ClientSession] = {}
proxy_connector: BaseConnector | None = None
def get_session(url: Url) -> ClientSession:
    if url.host is None:
        raise Exception(f"Unknown url {url}")
    else:
        index = url.host
        if index in session_dictionary:
            return session_dictionary[index]
        else:
            proxy = get_proxy(url.host in Cfg().network.unproxied)


            connector: BaseConnector 
            if proxy is None:
                connector = TCPConnector()
            else:
                global proxy_connector
                if proxy_connector is None:
                    proxy_connector = ProxyConnector.from_url(proxy)
                connector = proxy_connector

            session = ClientSession(
                connector=connector,
                # 必须使用copy()，否则各个模块对headers的修改都将会指向本模块中定义的headers变量，导致只有最后一个对headers的修改生效
                headers=default_headers.copy())

            
            session_dictionary[index] = session

            return session

async def clear_clients():
    close_tasks: list[Coroutine[Any, Any, None]] = []
    for client in session_dictionary.values():
        close_tasks.append(client.close())

    await asyncio.gather(*close_tasks)

    if proxy_connector is not None:
        await proxy_connector.close()
