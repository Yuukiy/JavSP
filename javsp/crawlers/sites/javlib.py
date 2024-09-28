"""从JavLibrary抓取数据"""
import logging
from urllib.parse import urlsplit

from httpx._transports import base

from javsp.crawlers.exceptions import MovieDuplicateError, MovieNotFoundError
from javsp.datatype import MovieInfo
from javsp.network.utils import resolve_site_fallback
from javsp.network.client import get_client
from javsp.crawlers.interface import Crawler
from javsp.config import CrawlerID
from lxml import html

logger = logging.getLogger(__name__)

class JavLibCrawler(Crawler):
    id = CrawlerID.jav321

    @classmethod
    async def create(cls): 
        self = cls()
        url = await resolve_site_fallback(self.id, 'https://www.javlibrary.com')
        self.base_url = str(url)
        self.client = get_client(url)
        return self

    # TODO: 发现JavLibrary支持使用cid搜索，会直接跳转到对应的影片页面，也许可以利用这个功能来做cid到dvdid的转换
    async def crawl_and_fill(self, movie: MovieInfo) -> None:
        """解析指定番号的影片数据"""
        url = new_url = f'{self.base_url}/cn/vl_searchbyid.php?keyword={movie.dvdid}'
        resp = await self.client.get(url)
        tree = html.fromstring(resp.text)
        if resp.history and urlsplit(str(resp.url)).netloc == urlsplit(self.base_url).netloc:
            # 出现301重定向通常且新老地址netloc相同时，说明搜索到了影片且只有一个结果
            new_url = resp.url
        else:   # 如果有多个搜索结果则不会自动跳转，此时需要程序介入选择搜索结果
            video_tags = tree.xpath("//div[@class='video'][@id]/a")
            # 通常第一部影片就是我们要找的，但是以免万一还是遍历所有搜索结果
            pre_choose = []
            for tag in video_tags:
                tag_dvdid = tag.xpath("div[@class='id']/text()")[0]
                if tag_dvdid.upper() == movie.dvdid.upper():
                    pre_choose.append(tag)
            pre_choose_urls = [i.get('href') for i in pre_choose]
            match_count = len(pre_choose)
            if match_count == 0:
                raise MovieNotFoundError(__name__, movie.dvdid)
            elif match_count == 1:
                new_url = pre_choose_urls[0]
            elif match_count == 2:
                no_blueray = []
                for tag in pre_choose:
                    if 'ブルーレイディスク' not in tag.get('title'):    # Blu-ray Disc
                        no_blueray.append(tag)
                no_blueray_count = len(no_blueray)
                if no_blueray_count == 1:
                    new_url = no_blueray[0].get('href')
                    logger.debug(f"'{movie.dvdid}': 存在{match_count}个同番号搜索结果，已自动选择封面比例正确的一个: {new_url}")
                else:
                    # 两个结果中没有谁是蓝光影片，说明影片番号重复了
                    raise MovieDuplicateError(__name__, movie.dvdid, match_count, pre_choose_urls)
            else:
                # 存在不同影片但是番号相同的情况，如MIDV-010
                raise MovieDuplicateError(__name__, movie.dvdid, match_count, pre_choose_urls)
            # 重新抓取网页
            resp = await self.client.get(new_url)
            tree = html.fromstring(resp.text)
        container = tree.xpath("/html/body/div/div[@id='rightcolumn']")[0]
        title_tag = container.xpath("div/h3/a/text()")
        title = title_tag[0]
        cover = container.xpath("//img[@id='video_jacket_img']/@src")[0]
        info = container.xpath("//div[@id='video_info']")[0]
        dvdid = info.xpath("div[@id='video_id']//td[@class='text']/text()")[0]
        publish_date = info.xpath("div[@id='video_date']//td[@class='text']/text()")[0]
        duration = info.xpath("div[@id='video_length']//span[@class='text']/text()")[0]
        director_tag = info.xpath("//span[@class='director']/a/text()")
        if director_tag:
            movie.director = director_tag[0]
        producer = info.xpath("//span[@class='maker']/a/text()")[0]
        publisher_tag = info.xpath("//span[@class='label']/a/text()")
        if publisher_tag:
            movie.publisher = publisher_tag[0]
        score_tag = info.xpath("//span[@class='score']/text()")
        if score_tag:
            movie.score = score_tag[0].strip('()')
        genre = info.xpath("//span[@class='genre']/a/text()")
        actress = info.xpath("//span[@class='star']/a/text()")

        movie.dvdid = dvdid
        movie.url = new_url
        movie.title = title.replace(dvdid, '').strip()
        if cover.startswith('//'):  # 补全URL中缺少的协议段
            cover = 'https:' + cover
        movie.cover = cover
        movie.publish_date = publish_date
        movie.duration = duration
        movie.producer = producer
        movie.genre = genre
        movie.actress = actress


if __name__ == "__main__":

    async def test_main():
        crawler = await JavLibCrawler.create()
        movie = MovieInfo('IPX-177')
        try:
          await crawler.crawl_and_fill(movie)
          print(movie)
        except Exception as e:
          print(repr(e))

    import asyncio
    asyncio.run(test_main())
