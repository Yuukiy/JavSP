"""从jav321抓取数据"""
import re
import logging


from javsp.crawlers.exceptions import MovieNotFoundError
from javsp.datatype import MovieInfo
from javsp.network.utils import resolve_site_fallback
from javsp.network.client import get_client
from javsp.crawlers.interface import Crawler
from javsp.config import CrawlerID
from lxml import html


logger = logging.getLogger(__name__)

class Jav321Crawler(Crawler):
    id = CrawlerID.jav321

    @classmethod
    async def create(cls): 
        self = cls()
        url = await resolve_site_fallback(self.id, 'https://www.jav321.com')
        self.base_url = str(url)
        self.client = get_client(url)
        return self

    async def crawl_and_fill(self, movie: MovieInfo) -> None:

        """解析指定番号的影片数据"""
        resp = await self.client.post(f'{self.base_url}/search', data={'sn': movie.dvdid})
        tree = html.fromstring(resp.text)
        page_url = tree.xpath("//ul[@class='dropdown-menu']/li/a/@href")[0]
        #TODO: 注意cid是dmm的概念。如果影片来自MGSTAGE，这里的cid很可能是jav321自己添加的，例如 345SIMM-542
        cid = page_url.split('/')[-1]   # /video/ipx00177
        # 如果从URL匹配到的cid是'search'，说明还停留在搜索页面，找不到这部影片
        if cid == 'search':
            raise MovieNotFoundError(__name__, movie.dvdid)
        title = tree.xpath("//div[@class='panel-heading']/h3/text()")[0]
        info = tree.xpath("//div[@class='col-md-9']")[0]
        # jav321的不同信息字段间没有明显分隔，只能通过url来匹配目标标签
        company_tags = info.xpath("a[contains(@href,'/company/')]/text()")
        if company_tags:
            movie.producer = company_tags[0]
        # actress, actress_pics
        # jav321现在连女优信息都没有了，首页通过女优栏跳转过去也全是空白
        actress, actress_pics = [], {}
        actress_tags = tree.xpath("//div[@class='thumbnail']/a[contains(@href,'/star/')]/img")
        for tag in actress_tags:
            name = tag.tail.strip()
            pic_url = tag.get('src')
            actress.append(name)
            # jav321的女优头像完全是应付了事：即使女优实际没有头像，也会有一个看起来像模像样的url，
            # 因而无法通过url判断女优头像图片是否有效。有其他选择时最好不要使用jav321的女优头像数据
            actress_pics[name] = pic_url
        # genre, genre_id
        genre_tags = info.xpath("a[contains(@href,'/genre/')]")
        genre, genre_id = [], []
        for tag in genre_tags:
            genre.append(tag.text)
            genre_id.append(tag.get('href').split('/')[-2]) # genre/4025/1
        dvdid = info.xpath("b[text()='品番']")[0].tail.replace(': ', '').upper()
        publish_date = info.xpath("b[text()='配信開始日']")[0].tail.replace(': ', '')
        duration_str = info.xpath("b[text()='収録時間']")[0].tail
        match = re.search(r'\d+', duration_str)
        if match:
            movie.duration = match.group(0)
        # 仅部分影片有评分且评分只能粗略到星级而没有分数，要通过星级的图片来判断，如'/img/35.gif'表示3.5星
        score_tag = info.xpath("//b[text()='平均評価']/following-sibling::img/@data-original")
        if score_tag:
            score = int(score_tag[0][5:7])/5   # /10*2
            movie.score = str(score)
        serial_tag = info.xpath("a[contains(@href,'/series/')]/text()")
        if serial_tag:
            movie.serial = serial_tag[0]
        preview_video_tag = info.xpath("//video/source/@src")
        if preview_video_tag:
            movie.preview_video = preview_video_tag[0]
        plot_tag = info.xpath("//div[@class='panel-body']/div[@class='row']/div[@class='col-md-12']/text()")
        if plot_tag:
            movie.plot = plot_tag[0]
        preview_pics = tree.xpath("//div[@class='col-xs-12 col-md-12']/p/a/img[@class='img-responsive']/@src")
        if len(preview_pics) == 0:
            # 尝试搜索另一种布局下的封面，需要使用onerror过滤掉明明没有封面时网站往里面塞的默认URL
            preview_pics = tree.xpath("//div/div/div[@class='col-md-3']/img[@onerror and @class='img-responsive']/@src")
        # 有的图片链接里有多个//，网站质量堪忧……
        preview_pics = [i[:8] + i[8:].replace('//', '/') for i in preview_pics]
        # 磁力和ed2k链接是依赖js脚本加载的，无法通过静态网页来解析

        movie.url = page_url
        movie.cid = cid
        movie.dvdid = dvdid
        movie.title = title
        movie.actress = actress
        movie.actress_pics = actress_pics
        movie.genre = genre
        movie.genre_id = genre_id
        movie.publish_date = publish_date
        # preview_pics的第一张图始终是封面，剩下的才是预览图
        if len(preview_pics) > 0:
            movie.cover = preview_pics[0]
            movie.preview_pics = preview_pics[1:]


if __name__ == "__main__":

    async def test_main():
        crawler = await Jav321Crawler.create()
        movie = MovieInfo('SCUTE-1177')
        try:
          await crawler.crawl_and_fill(movie)
          print(movie)
        except Exception as e:
          print(repr(e))

    import asyncio
    asyncio.run(test_main())
