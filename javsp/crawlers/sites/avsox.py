"""从avsox抓取数据"""

from javsp.crawlers.exceptions import MovieNotFoundError
from javsp.datatype import MovieInfo
from javsp.network.utils import resolve_site_fallback
from javsp.network.client import get_session
from javsp.crawlers.interface import Crawler
from javsp.config import CrawlerID
from lxml import html

class AvsoxCrawler(Crawler):
    id = CrawlerID.avsox

    @classmethod
    async def create(cls): 
        self = cls()
        url = await resolve_site_fallback(self.id, "https://avsox.click/")
        self.base_url = str(url)
        self.client = get_session(url)
        return self

    async def crawl_and_fill(self, movie: MovieInfo) -> None:
        full_id: str = movie.dvdid
        if full_id.startswith('FC2-'):
            full_id = full_id.replace('FC2-', 'FC2-PPV-')
        resp = await self.client.get(f'{self.base_url}tw/search/{full_id}')
        tree = html.fromstring(await resp.text())
        tree.make_links_absolute(str(resp.url), resolve_base_href=True)
        ids = tree.xpath("//div[@class='photo-info']/span/date[1]/text()")
        urls = tree.xpath("//a[contains(@class, 'movie-box')]/@href")
        ids_lower = list(map(str.lower, ids))
        if full_id.lower() not in ids_lower:
            raise MovieNotFoundError(__name__, movie.dvdid, ids)

        url = urls[ids_lower.index(full_id.lower())]
        url = url.replace('/tw/', '/cn/', 1)

        # 提取影片信息
        resp = await self.client.get(url)
        tree = html.fromstring(await resp.text())
        container = tree.xpath("/html/body/div[@class='container']")[0]
        title = container.xpath("h3/text()")[0]
        cover = container.xpath("//a[@class='bigImage']/@href")[0]
        info = container.xpath("div/div[@class='col-md-3 info']")[0]
        dvdid = info.xpath("p/span[@style]/text()")[0]
        publish_date = info.xpath("p/span[text()='发行时间:']")[0].tail.strip()
        duration = info.xpath("p/span[text()='长度:']")[0].tail.replace('分钟', '').strip()
        producer, serial = None, None
        producer_tag = info.xpath("p[text()='制作商: ']")[0].getnext().xpath("a")
        if producer_tag:
            producer = producer_tag[0].text_content()
        serial_tag = info.xpath("p[text()='系列:']")
        if serial_tag:
            serial = serial_tag[0].getnext().xpath("a/text()")[0]
        genre = info.xpath("p/span[@class='genre']/a/text()")
        actress = container.xpath("//a[@class='avatar-box']/span/text()")

        movie.dvdid = dvdid.replace('FC2-PPV-', 'FC2-')
        movie.url = url
        movie.title = title.replace(dvdid, '').strip()
        movie.cover = cover
        movie.publish_date = publish_date
        movie.duration = duration
        movie.genre = genre
        movie.actress = actress
        if full_id.startswith('FC2-'):
            # avsox把FC2作品的拍摄者归类到'系列'而制作商固定为'FC2-PPV'，这既不合理也与其他的站点不兼容，因此进行调整
            movie.producer = serial
        else:
            movie.producer = producer
            movie.serial = serial


if __name__ == "__main__":

    async def test_main():
        crawler = await AvsoxCrawler.create()
        movie = MovieInfo("082713-417")
        try:
          await crawler.crawl_and_fill(movie)
          print(movie)
        except Exception as e:
          print(repr(e))

    import asyncio
    asyncio.run(test_main())
