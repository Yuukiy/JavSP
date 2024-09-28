from httpx import AsyncClient
from javsp.config import CrawlerID
from javsp.datatype import MovieInfo
from abc import ABC, abstractmethod
from typing import Self


class Crawler(ABC):
    base_url: str
    client: AsyncClient
    id: CrawlerID


    @classmethod
    @abstractmethod
    async def create(cls) -> Self: 
        pass

    @abstractmethod
    async def crawl_and_fill(self, movie: MovieInfo) -> None:
        pass
