"""从FC2官网抓取数据"""
import logging

from lxml import html


from javsp.crawlers.exceptions import *
from javsp.config import Cfg
from javsp.lib import strftime_to_minutes
from javsp.datatype import MovieInfo
from javsp.crawlers.interface import Crawler
from javsp.network.utils import resolve_site_fallback
from javsp.network.client import get_session
from javsp.config import CrawlerID


logger = logging.getLogger(__name__)

class Fc2Crawler(Crawler):
    id = CrawlerID.fc2

    @classmethod
    async def create(cls): 
        self = cls()
        url = await resolve_site_fallback(self.id, 'https://adult.contents.fc2.com')
        self.base_url = str(url)
        self.client = get_session(url)
        return self

    async def get_movie_score(self, fc2_id: str) -> float | None:
        """通过评论数据来计算FC2的影片评分（10分制），无法获得评分时返回None"""
        resp = await self.client.get(f'{self.base_url}/article/{fc2_id}/review')
        tree = html.fromstring(await resp.text())
        review_tags = tree.xpath("//ul[@class='items_comment_headerReviewInArea']/li")
        reviews = {}
        for tag in review_tags:
            score = int(tag.xpath("div/span/text()")[0])
            vote = int(tag.xpath("span")[0].text_content())
            reviews[score] = vote
        total_votes = sum(reviews.values())
        if (total_votes >= 2):   # 至少也该有两个人评价才有参考意义一点吧
            summary = sum([k*v for k, v in reviews.items()])
            final_score = summary / total_votes * 2   # 乘以2转换为10分制
            return final_score


    async def crawl_and_fill(self, movie: MovieInfo) -> None:
        """解析指定番号的影片数据"""
        # 去除番号中的'FC2'字样
        id_uc = movie.dvdid.upper()
        if not id_uc.startswith('FC2-'):
            raise ValueError('Invalid FC2 number: ' + movie.dvdid)
        fc2_id = id_uc.replace('FC2-', '')
        # 抓取网页
        url = f'{self.base_url}/article/{fc2_id}/'
        resp = await self.client.get(url)
        if '/id.fc2.com/' in str(resp.url):
            raise SiteBlocked('FC2要求当前IP登录账号才可访问，请尝试更换为日本IP')
        tree = html.fromstring(await resp.text())
        container = tree.xpath("//div[@class='items_article_left']")
        if len(container) > 0:
            container = container[0]
        else:
            raise MovieNotFoundError(__name__, movie.dvdid)
        # FC2 标题增加反爬乱码，使用数组合并标题
        title_arr = container.xpath("//div[@class='items_article_headerInfo']/h3/text()")
        title = ''.join(title_arr)
        thumb_tag = container.xpath("//div[@class='items_article_MainitemThumb']")[0]
        thumb_pic = thumb_tag.xpath("span/img/@src")[0]
        duration_str = thumb_tag.xpath("span/p[@class='items_article_info']/text()")[0]
        # FC2没有制作商和发行商的区分，作为个人市场，影片页面的'by'更接近于制作商
        producer = container.xpath("//li[text()='by ']/a/text()")[0]
        genre = container.xpath("//a[@class='tag tagTag']/text()")
        date_str = container.xpath("//div[@class='items_article_Releasedate']/p/text()")[0]
        publish_date = date_str[-10:].replace('/', '-')  # '販売日 : 2017/11/30'
        preview_pics = container.xpath("//ul[@data-feed='sample-images']/li/a/@href")

        if Cfg().crawler.hardworking:
            # 通过评论数据来计算准确的评分
            score = await self.get_movie_score(fc2_id)
            if score:
                movie.score = f'{score:.2f}'
            # 预览视频是动态加载的，不在静态网页中
            desc_frame_url = container.xpath("//section[@class='items_article_Contents']/iframe/@src")[0]
            key = desc_frame_url.split('=')[-1]     # /widget/article/718323/description?ac=60fc08fa...
            api_url = f'{self.base_url}/api/v2/videos/{fc2_id}/sample?key={key}'
            resp = await self.client.get(api_url)
            j = await resp.json()
            movie.preview_video = j['path']
        else:
            # 获取影片评分。影片页面的评分只能粗略到星级，且没有分数，要通过类名来判断，如'items_article_Star5'表示5星
            score_tag_attr = container.xpath("//a[@class='items_article_Stars']/p/span/@class")[0]
            score = int(score_tag_attr[-1]) * 2
            movie.score = f'{score:.2f}'

        movie.dvdid = id_uc
        movie.url = url
        movie.title = title
        movie.genre = genre
        movie.producer = producer
        movie.duration = str(strftime_to_minutes(duration_str))
        movie.publish_date = publish_date
        movie.preview_pics = preview_pics
        # FC2的封面是220x220的，和正常封面尺寸、比例都差太多。如果有预览图片，则使用第一张预览图作为封面
        if movie.preview_pics:
            movie.cover = preview_pics[0]
        else:
            movie.cover = thumb_pic


if __name__ == "__main__":

    async def test_main():
        crawler = await Fc2Crawler.create()
        movie = MovieInfo("FC2-718323")
        await crawler.crawl_and_fill(movie)
        print(movie)

    import asyncio
    asyncio.run(test_main())
