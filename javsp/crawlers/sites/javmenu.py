"""从JavMenu抓取数据"""
import logging

from javsp.crawlers.exceptions import MovieNotFoundError
from javsp.datatype import MovieInfo
from javsp.network.utils import resolve_site_fallback
from javsp.network.client import get_session
from javsp.crawlers.interface import Crawler
from javsp.config import CrawlerID
from lxml import html

logger = logging.getLogger(__name__)

class JavMenuCrawler(Crawler):
    id = CrawlerID.javmenu

    @classmethod
    async def create(cls): 
        self = cls()
        url = await resolve_site_fallback(self.id, 'https://www.javmenu.com')
        self.base_url = str(url)
        self.client = get_session(url)
        return self

    async def crawl_and_fill(self, movie: MovieInfo) -> None:
        """从网页抓取并解析指定番号的数据
        Args:
            movie (MovieInfo): 要解析的影片信息，解析后的信息直接更新到此变量内
        """
        # JavMenu网页做得很不走心，将就了
        url = f'{self.base_url}zh/{movie.dvdid}'
        r = await self.client.get(url)
        if r.history:
            # 被重定向到主页说明找不到影片资源
            raise MovieNotFoundError(__name__, movie.dvdid)

        tree = html.fromstring(await r.text())
        container = tree.xpath("//div[@class='col-md-9 px-0']")[0]
        title = container.xpath("div[@class='col-12 mb-3']/h1/strong/text()")[0]
        # 竟然还在标题里插广告，真的疯了。要不是我已经写了抓取器，才懒得维护这个破站
        title = title.replace('  | JAV目錄大全 | 每日更新', '')
        title = title.replace(' 免費在線看', '').replace(' 免費AV在線看', '')
        cover_tag = container.xpath("//div[@class='single-video']")
        if len(cover_tag) > 0:
            video_tag = cover_tag[0].find('video')
            # URL首尾竟然也有空格……
            movie.cover = video_tag.get('data-poster').strip()
            # 预览影片改为blob了，无法获取
            # movie.preview_video = video_tag.find('source').get('src').strip()
        else:
            cover_img_tag = container.xpath("//img[@class='lazy rounded']/@data-src")
            if cover_img_tag:
                movie.cover = cover_img_tag[0].strip()
        info = container.xpath("//div[@class='card-body']")[0]
        publish_date = info.xpath("div/span[contains(text(), '日期:')]")[0].getnext().text
        duration = info.xpath("div/span[contains(text(), '时长:')]")[0].getnext().text.replace('分钟', '')
        producer = info.xpath("div/span[contains(text(), '製作:')]/following-sibling::a/span/text()")
        if producer:
            movie.producer = producer[0]
        genre_tags = info.xpath("//a[@class='genre']")
        genre, genre_id = [], []
        for tag in genre_tags:
            items = tag.get('href').split('/')
            pre_id = items[-3] + '/' + items[-1]
            genre.append(tag.text.strip())
            genre_id.append(pre_id)
            # genre的链接中含有censored字段，但是无法用来判断影片是否有码，因为完全不可靠……
        actress = info.xpath("div/span[contains(text(), '女优:')]/following-sibling::*/a/text()") or None
        magnet_table = container.xpath("//table[contains(@class, 'magnet-table')]/tbody")
        if magnet_table:
            magnet_links = magnet_table[0].xpath("tr/td/a/@href")
            # 它的FC2数据是从JavDB抓的，JavDB更换图片服务器后它也跟上了，似乎数据更新频率还可以
            movie.magnet = [i.replace('[javdb.com]','') for i in magnet_links]
        preview_pics = container.xpath("//a[@data-fancybox='gallery']/@href")

        if (not movie.cover) and preview_pics:
            movie.cover = preview_pics[0]
        movie.url = url
        movie.title = title.replace(movie.dvdid, '').strip()
        movie.preview_pics = preview_pics
        movie.publish_date = publish_date
        movie.duration = duration
        movie.genre = genre
        movie.genre_id = genre_id
        movie.actress = actress


if __name__ == "__main__":

    async def test_main():
        crawler = await JavMenuCrawler.create()
        movie = MovieInfo('FC2-718323')
        # try:
        await crawler.crawl_and_fill(movie)
        print(movie)
        # except Exception as e:
        #   print(repr(e))

    import asyncio
    asyncio.run(test_main())
