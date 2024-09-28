"""从av-wiki抓取数据"""

from javsp.crawlers.exceptions import MovieNotFoundError
from javsp.datatype import MovieInfo
from javsp.crawlers.interface import Crawler
from javsp.network.utils import resolve_site_fallback
from javsp.network.client import get_client
from javsp.config import CrawlerID
from lxml import html

class AvWikiCrawler(Crawler):
    id = CrawlerID.avwiki

    @classmethod
    async def create(cls): 
        self = cls()
        url = await resolve_site_fallback(self.id, 'https://av-wiki.net')
        self.base_url = str(url)
        self.client = get_client(url)
        return self

    async def crawl_and_fill(self, movie: MovieInfo) -> None:
        """从网页抓取并解析指定番号的数据
        Args:
            movie (MovieInfo): 要解析的影片信息，解析后的信息直接更新到此变量内
        """
        movie.url = url = f'{self.base_url}/{movie.dvdid}'
        
        resp = await self.client.get(url) 
        if resp.status_code == 404:
            raise MovieNotFoundError(__name__, movie.dvdid)
        tree = html.fromstring(resp.content)

        cover_tag = tree.xpath("//header/div/a[@class='image-link-border']/img")
        if cover_tag:
            try:
                srcset = cover_tag[0].get('srcset').split(', ')
                src_set_urls = {}
                for src in srcset:
                    url, width = src.split()
                    width = int(width.rstrip('w'))
                    src_set_urls[width] = url
                max_pic = sorted(src_set_urls.items(), key=lambda x:x[0], reverse=True)
                movie.cover = max_pic[0][1]
            except:
                movie.cover = cover_tag[0].get('src')
        body = tree.xpath("//section[@class='article-body']")[0]
        title = body.xpath("div/p/text()")[0]
        title = title.replace(f"【{movie.dvdid}】", '')
        cite_url = body.xpath("div/cite/a/@href")[0]
        cite_url = cite_url.split('?aff=')[0]
        info = body.xpath("dl[@class='dltable']")[0]
        dt_txt_ls, dd_tags = info.xpath("dt/text()"), info.xpath("dd")
        data = {}
        for dt_txt, dd in zip(dt_txt_ls, dd_tags):
            dt_txt = dt_txt.strip()
            a_tag = dd.xpath('a')
            if len(a_tag) == 0:
                dd_txt = dd.text.strip()
            else:
                dd_txt = [i.text.strip() for i in a_tag]
            if isinstance(dd_txt, list) and dt_txt != 'AV女優名':    # 只有女优名以列表的数据格式保留
                dd_txt = dd_txt[0]
            data[dt_txt] = dd_txt

        ATTR_MAP = {'メーカー': 'producer', 'AV女優名': 'actress', 'メーカー品番': 'dvdid', 'シリーズ': 'serial', '配信開始日': 'publish_date'}
        for key, attr in ATTR_MAP.items():
            setattr(movie, attr, data.get(key))
        movie.title = title
        movie.uncensored = False    # 服务器在日本且面向日本国内公开发售，不会包含无码片


if __name__ == "__main__":

    async def test_main():
        crawler = await AvWikiCrawler.create()
        movie = MovieInfo("259LUXU-593")
        await crawler.crawl_and_fill(movie)
        print(movie)

    import asyncio
    asyncio.run(test_main())
