"""从https://gyutto.com/官网抓取数据"""
import logging
import time

from javsp.crawlers.exceptions import MovieNotFoundError
from javsp.datatype import MovieInfo
from javsp.network.utils import resolve_site_fallback
from javsp.network.client import get_session
from javsp.crawlers.interface import Crawler
from javsp.config import CrawlerID
from lxml import html
from lxml.html import HtmlElement

logger = logging.getLogger(__name__)

def get_movie_title(tree: HtmlElement) -> str:
    container = tree.xpath("//h1")
    if len(container) > 0:
        container = container[0]
    title = container.text
    
    return title

def get_movie_img(tree: HtmlElement, index = 1) -> list[str]:
    images = []
    container = tree.xpath("//a[@class='highslide']/img")
    if len(container) > 0:
        if index == 0:
            return container[0].get('src')
        
        for row in container:
            images.append(row.get('src'))

    return images

class GyuttoCrawler(Crawler):
    id = CrawlerID.gyutto

    @classmethod
    async def create(cls): 
        self = cls()
        url = await resolve_site_fallback(self.id, 'http://gyutto.com')
        self.base_url = str(url)
        self.client = get_session(url)
        return self

    async def crawl_and_fill(self, movie: MovieInfo) -> None:
        """解析指定番号的影片数据"""
        # 去除番号中的'gyutto'字样
        id_uc = movie.dvdid.upper()
        if not id_uc.startswith('GYUTTO-'):
            raise ValueError('Invalid gyutto number: ' + movie.dvdid)
        gyutto_id = id_uc.replace('GYUTTO-', '')
        # 抓取网页
        url = f'{self.base_url}/i/item{gyutto_id}?select_uaflag=1'
        r = await self.client.get(url)
        if r.status == 404:
            raise MovieNotFoundError(__name__, movie.dvdid)
        tree = html.fromstring(await r.text())
        container = tree.xpath("//dl[@class='BasicInfo clearfix']")

        producer = None
        genre = None
        date = None
        publish_date = None

        for row in container:
            key = row.xpath(".//dt/text()")
            if key[0] == "サークル":
                producer = ''.join(row.xpath(".//dd/a/text()"))
            elif key[0] == "ジャンル":
                genre = row.xpath(".//dd/a/text()")
            elif key[0] == "配信開始日":
                date = row.xpath(".//dd/text()")
                date_str = ''.join(date)
                date_time = time.strptime(date_str, "%Y年%m月%d日")
                publish_date = time.strftime("%Y-%m-%d", date_time)

        plot = tree.xpath("//div[@class='unit_DetailLead']/p/text()")[0]
        
        movie.title = get_movie_title(tree)
        movie.cover = get_movie_img(tree, 0)
        movie.preview_pics = get_movie_img(tree)
        movie.dvdid = id_uc
        movie.url = url
        movie.producer = producer
        # movie.actress = actress
        # movie.duration = duration
        movie.publish_date = publish_date
        movie.genre = genre
        movie.plot = plot


if __name__ == "__main__":

    async def test_main():
        crawler = await GyuttoCrawler.create()
        movie = MovieInfo('gyutto-266923')
        try:
          await crawler.crawl_and_fill(movie)
          print(movie)
        except Exception as e:
          print(repr(e))

    import asyncio
    asyncio.run(test_main())
