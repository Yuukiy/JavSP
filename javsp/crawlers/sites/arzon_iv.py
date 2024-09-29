"""从arzon_iv抓取数据"""
import re


from javsp.network.utils import resolve_site_fallback
from javsp.network.client import get_session
from javsp.crawlers.interface import Crawler
from javsp.config import CrawlerID
from javsp.crawlers.exceptions import *
from javsp.datatype import MovieInfo
from lxml import html

class ArzonIvCrawler(Crawler):
    id = CrawlerID.arzon_iv
  
    @classmethod
    async def create(cls): 
        self = cls()
        url = await resolve_site_fallback(self.id, "https://www.arzon.jp")
        self.base_url = str(url)
        self.client = get_session(url)
        # https://www.arzon.jp/index.php?action=adult_customer_agecheck&agecheck=1&redirect=https%3A%2F%2Fwww.arzon.jp%2F
        skip_verify_url = f"{self.base_url}/index.php?action=adult_customer_agecheck&agecheck=1"
        await self.client.get(skip_verify_url)
        return self

    async def crawl_and_fill(self, movie: MovieInfo) -> None:
        """解析指定番号的影片数据"""
        full_id = movie.dvdid
        url = f'{self.base_url}/imagelist.html?q={full_id}'
        # url = f'{base_url}/imagelist.html?q={full_id}'
        
        r = await self.client.get(url)
        if r.status == 404:
          raise MovieNotFoundError(__name__, movie.dvdid)
        # https://stackoverflow.com/questions/15830421/xml-unicode-strings-with-encoding-declaration-are-not-supported
        data = html.fromstring(await r.read())
    
        urls = data.xpath("//h2/a/@href")
        if len(urls) == 0:
            raise MovieNotFoundError(__name__, movie.dvdid)
    
        item_url = self.base_url[:-1] + urls[0]
        e = await self.client.get(item_url)
        item = html.fromstring(await e.read())
    
        title = item.xpath("//div[@class='detail_title_new']//h1/text()")[0]
        cover = item.xpath("//td[@align='center']//a/img/@src")[0]
        item_text = item.xpath("//div[@class='item_text']/text()")
        plot = [item.strip() for item in item_text if item.strip() != ''][0]
    
        container = item.xpath("//div[@class='item_register']/table//tr")
        for row in container:
          key = row.xpath("./td[1]/text()")[0]
          contents = row.xpath("./td[2]//text()")
          content = [item.strip() for item in contents if item.strip() != '']
          index = 0
          value = content[index] if content and index < len(content) else None
          if key == "タレント：":
            movie.actress = content
          if key == "イメージメーカー：":
            movie.producer = value
          if key == "イメージレーベル：":
            video_type = value
          if key == "監督：":
            movie.director = value
          if key == "発売日：" and value:
            movie.publish_date = re.search(r"\d{4}/\d{2}/\d{2}", value).group(0).replace("/", "-")
          if key == "収録時間：" and value:
            movie.duration = re.search(r'([\d.]+)分', value).group(1)
          if key == "品番：":
            dvd_id = value
          elif key == "タグ：":
            genre  = value
    
        genres = ''
        if video_type:
          genres = [video_type]
        if(genre != None):
          genres.append(genre)
    
        movie.genre = genres
        movie.url = item_url
        movie.title = title
        movie.plot = plot
        movie.cover = f'https:{cover}'
    
if __name__ == "__main__":

    async def test_main():
        crawler = await ArzonIvCrawler.create()
        movie = MovieInfo("KIDM-1137B")
        try:
          await crawler.crawl_and_fill(movie)
          print(movie)
        except Exception as e:
          print(repr(e))

    import asyncio
    asyncio.run(test_main())
