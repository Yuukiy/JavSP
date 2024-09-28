"""从NJAV抓取数据"""
import re
import logging
from typing import List

from javsp.crawlers.exceptions import MovieNotFoundError
from javsp.datatype import MovieInfo
from javsp.network.utils import resolve_site_fallback
from javsp.network.client import get_client
from javsp.crawlers.interface import Crawler
from javsp.config import CrawlerID
from javsp.lib import strftime_to_minutes
from lxml import html


logger = logging.getLogger(__name__)

def get_list_first(list: List):
    return list[0] if list and len(list) > 0 else None

class NjavCrawler(Crawler):
    id = CrawlerID.njav

    @classmethod
    async def create(cls): 
        self = cls()
        url = await resolve_site_fallback(self.id, 'https://www.njav.tv/')
        self.base_url = str(url)
        self.client = get_client(url)
        return self

    async def search_video(self, movie: MovieInfo) -> str:
        id_uc = movie.dvdid
        # 抓取网页
        url = f'{self.base_url}ja/search?keyword={id_uc}'
        resp = await self.client.get(url)
        tree = html.fromstring(resp.text)
        list = tree.xpath("//div[@class='box-item']/div[@class='detail']/a")
        video_url = None
        for item in list:
            search_title = item.xpath("text()")[0]
            if id_uc in search_title:
                video_url = item.xpath("@href")
                break
            if id_uc.startswith("FC2-"):
                fc2id = id_uc.replace('FC2-', '')
                if "FC2" in search_title and fc2id in search_title:
                    video_url = item.xpath("@href")
                    break
        
        return get_list_first(video_url)
    async def crawl_and_fill(self, movie: MovieInfo) -> None:
        """解析指定番号的影片数据"""
        # 抓取网页
        url = await self.search_video(movie)
        url = self.base_url + "ja/" + url
        if not url:
            raise MovieNotFoundError(__name__, movie.dvdid)
        resp = await self.client.get(url)
        tree = html.fromstring(resp.text)
        container = tree.xpath("//div[@class='container']/div/div[@class='col']")
        if len(container) > 0:
            container = container[0]
        else:
            raise MovieNotFoundError(__name__, movie.dvdid)
        
        title = container.xpath("//div[@class='d-flex justify-content-between align-items-start']/div/h1/text()")[0]
        thumb_pic = container.xpath("//div[@id='player']/@data-poster")
        plot = " ".join(container.xpath("//div[@class='description']/p/text()"))
        magnet = container.xpath("//div[@class='magnet']/a/@href")
        real_id = None
        publish_date = None
        duration_str = None
        uncensored = None
        preview_pics = None
        preview_video = None
        serial = None
        publisher = None
        producer = None
        genre = []
        actress = []

        for item in container.xpath("//div[@class='detail-item']/div"):
            item_title = item.xpath('span/text()')[0]
            if "タグ:" in item_title:
                genre += item.xpath("span")[1].xpath("a/text()")
            elif "ジャンル:" in item_title:
                genre += item.xpath("span")[1].xpath("a/text()")
            elif "レーベル:" in item_title:
                genre += item.xpath("span")[1].xpath("a/text()")    
            elif "女優:" in item_title:
                actress = item.xpath("span")[1].xpath("a/text()")
            elif "シリーズ:" in item_title:
                serial = get_list_first(item.xpath("span")[1].xpath("a/text()"))
            elif "メーカー:" in item_title:
                producer = get_list_first(item.xpath("span")[1].xpath("a/text()"))
            elif "コード:" in item_title:
                real_id = get_list_first(item.xpath("span")[1].xpath("text()"))
            elif "公開日:" in item_title:
                publish_date = get_list_first(item.xpath("span")[1].xpath("text()"))
            elif "再生時間:" in item_title:
                duration_str = get_list_first(item.xpath("span")[1].xpath("text()"))
        
        # 清除标题里的番号字符
        keywords = [real_id, " "]
        if movie.dvdid.startswith("FC2"):
            keywords += ["FC2","PPV","-"] + [movie.dvdid.split("-")[-1]]
        for keyword in keywords:
           title = re.sub(re.escape(keyword), "", title, flags=re.I)

        # 判断是否无码
        uncensored_arr = magnet + [title]
        for uncensored_str in uncensored_arr:
            if 'uncensored' in uncensored_str.lower():
                uncensored = True

        movie.url = url
        movie.title = title
        movie.genre = genre
        movie.actress = actress
        movie.duration = str(strftime_to_minutes(duration_str))
        movie.publish_date = publish_date
        movie.publisher = publisher
        movie.producer = producer
        movie.uncensored = uncensored
        movie.preview_pics = preview_pics
        movie.preview_video = preview_video
        movie.plot = plot
        movie.serial = serial
        movie.magnet = magnet

        # FC2的封面是220x220的，和正常封面尺寸、比例都差太多。如果有预览图片，则使用第一张预览图作为封面
        if movie.preview_pics:
            movie.cover = preview_pics[0]
        else:
            movie.cover = get_list_first(thumb_pic)

if __name__ == "__main__":

    async def test_main():
        crawler = await NjavCrawler.create()
        movie = MovieInfo('012023_002')
        try:
          await crawler.crawl_and_fill(movie)
          print(movie)
        except Exception as e:
          print(repr(e))

    import asyncio
    asyncio.run(test_main())
