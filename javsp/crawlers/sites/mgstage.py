"""从蚊香社-mgstage抓取数据"""
import re
import logging


from javsp.crawlers.exceptions import MovieNotFoundError, SiteBlocked
from javsp.datatype import MovieInfo
from javsp.network.utils import resolve_site_fallback
from javsp.network.client import get_client
from javsp.crawlers.interface import Crawler
from javsp.config import Cfg, CrawlerID
from lxml import html


logger = logging.getLogger(__name__)

class MgstageCrawler(Crawler):
    id = CrawlerID.mgstage

    @classmethod
    async def create(cls): 
        self = cls()
        url = await resolve_site_fallback(self.id, 'https://www.mgstage.com')
        self.base_url = str(url)
        self.client = get_client(url)
        # 初始化Request实例（要求携带已通过R18认证的cookies，否则会被重定向到认证页面）
        self.client.cookies = {'adc': '1'}
        return self

    async def crawl_and_fill(self, movie: MovieInfo) -> None:
        """解析指定番号的影片数据"""
        url = f'{self.base_url}/product/product_detail/{movie.dvdid}/'
        resp = await self.client.get(url)
        if resp.status_code == 403:
            raise SiteBlocked('mgstage不允许从当前IP所在地区访问，请尝试更换为日本地区代理')
        # url不存在时会被重定向至主页。history非空时说明发生了重定向
        elif resp.history:
            raise MovieNotFoundError(__name__, movie.dvdid)

        tree = html.fromstring(resp.text)
        # mgstage的文本中含有大量的空白字符（'\n \t'），需要使用strip去除
        title = tree.xpath("//div[@class='common_detail_cover']/h1/text()")[0].strip()
        container = tree.xpath("//div[@class='detail_left']")[0]
        cover = container.xpath("//a[@id='EnlargeImage']/@href")[0]
        # 有链接的女优和仅有文本的女优匹配方法不同，因此分别匹配以后合并列表
        actress_text = container.xpath("//th[text()='出演：']/following-sibling::td/text()")
        actress_link = container.xpath("//th[text()='出演：']/following-sibling::td/a/text()")
        actress = [i.strip() for i in actress_text + actress_link]
        actress = [i for i in actress if i]     # 移除空字符串
        producer = container.xpath("//th[text()='メーカー：']/following-sibling::td/a/text()")[0].strip()
        duration_str = container.xpath("//th[text()='収録時間：']/following-sibling::td/text()")[0]
        match = re.search(r'\d+', duration_str)
        if match:
            movie.duration = match.group(0)
        dvdid = container.xpath("//th[text()='品番：']/following-sibling::td/text()")[0]
        date_str = container.xpath("//th[text()='配信開始日：']/following-sibling::td/text()")[0]
        publish_date = date_str.replace('/', '-')
        serial_tag = container.xpath("//th[text()='シリーズ：']/following-sibling::td/a/text()")
        if serial_tag:
            movie.serial = serial_tag[0].strip()
        # label: 大意是某个系列策划用同样的番号，例如ABS打头的番号label是'ABSOLUTELY PERFECT'，暂时用不到
        # label = container.xpath("//th[text()='レーベル：']/following-sibling::td/text()")[0].strip()
        genre_tags = container.xpath("//th[text()='ジャンル：']/following-sibling::td/a")
        genre = [i.text.strip() for i in genre_tags]
        score_str = container.xpath("//td[@class='review']/span")[0].tail.strip()
        match = re.search(r'^[\.\d]+', score_str)
        if match:
            score = float(match.group()) * 2
            movie.score = f'{score:.2f}'
        # plot可能含有嵌套格式，为了保留plot中的换行关系，手动处理plot中的各个标签
        plots = []
        plot_p_tags = container.xpath("//dl[@id='introduction']/dd/p[not(@class='more')]")
        for p in plot_p_tags:
            children = p.getchildren()
            # 没有children时表明plot不含有格式，此时简单地提取文本就可以
            if not children:
                plots.append(p.text_content())
                continue
            for child in children:
                if child.tag == 'br' and plots[-1] != '\n':
                    plots.append('\n')
                else:
                    if child.text:
                        plots.append(child.text)
                    if child.tail:
                        plots.append(child.tail)
        plot = ''.join(plots).strip()
        preview_pics = container.xpath("//a[@class='sample_image']/@href")

        if Cfg().crawler.hardworking:
            # 预览视频是点击按钮后再加载的，不在静态网页中
            btn_url = container.xpath("//a[@class='button_sample']/@href")[0]
            video_pid = btn_url.split('/')[-1]
            req_url = f'{self.base_url}/sampleplayer/sampleRespons.php?pid={video_pid}'
            resp = await self.client.get(req_url)
            j = resp.json()
            video_url = j.get('url')
            if video_url:
                # /sample/shirouto/siro/3093/SIRO-3093_sample.ism/request?uid=XXX&amp;pid=XXX
                preview_video = video_url.split('.ism/')[0] + '.mp4'
                movie.preview_video = preview_video

        movie.dvdid = dvdid
        movie.url = url
        movie.title = title
        movie.cover = cover
        movie.actress = actress
        movie.producer = producer
        movie.publish_date = publish_date
        movie.genre = genre
        movie.plot = plot
        movie.preview_pics = preview_pics
        movie.uncensored = False    # 服务器在日本且面向日本国内公开发售，不会包含无码片


if __name__ == "__main__":
    async def test_main():
        crawler = await MgstageCrawler.create()
        movie = MovieInfo('ABF-153')
        # try:
        await crawler.crawl_and_fill(movie)
        print(movie)
        # except Exception as e:
        #   print(repr(e))

    import asyncio
    asyncio.run(test_main())
