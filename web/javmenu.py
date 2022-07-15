"""从JavMenu抓取数据"""
import os
import sys
import logging
from core.config import cfg
from core.func import remove_trail_actor_in_title

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import Request, resp2html
from web.exceptions import *
from core.datatype import MovieInfo


request = Request()

logger = logging.getLogger(__name__)
base_url = 'https://mrzyx.xyz'


def parse_data(movie: MovieInfo):
    """从网页抓取并解析指定番号的数据
    Args:
        movie (MovieInfo): 要解析的影片信息，解析后的信息直接更新到此变量内
    """
    # JavMenu网页做得不怎么走心，将就了
    url = f'{base_url}/{movie.dvdid}'
    r = request.get(url)
    if r.history:
        # 被重定向到主页说明找不到影片资源
        raise MovieNotFoundError(__name__, movie.dvdid)

    html = resp2html(r)
    container = html.xpath("//div[@class='col-md-8 px-0']")[0]
    title = container.xpath("div[@class='col-12 mb-3']/h1/strong/text()")[0]
    cover_tag = container.xpath("//div[@class='single-video']")[0]
    video_tag = cover_tag.find('video')
    if video_tag is not None:
        # URL首尾竟然也有空格……
        movie.cover = video_tag.get('data-poster').strip()
        movie.preview_video = video_tag.find('source').get('src').strip()
    else:
        movie.cover = container.xpath("//img[@class='lazy rounded']/@data-src")[0].strip()
    info = container.xpath("//div[@class='card-body']")[0]
    publish_date = info.xpath("div/span[contains(text(), '日期:')]")[0].getnext().text
    duration = info.xpath("div/span[contains(text(), '時長:')]")[0].getnext().text.replace('分鐘', '')
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
        # genra的链接中含有censored字段，但是无法用来判断影片是否有码，因为完全不可靠……
    actress = info.xpath("div/span[contains(text(), '女優:')]/following-sibling::*/a/text()") or None
    magnet_table = container.xpath("//div[@id='download-tab']//tbody")
    if magnet_table:
        magnet_links = magnet_table[0].xpath("tr/td/a/@href")
        # 它的FC2数据是从JavDB抓的，JavDB更换图片服务器后它也跟上了，似乎数据更新频率还可以
        movie.magnet = [i.replace('[javdb.com]','') for i in magnet_links]
    preview_pics = container.xpath("//a[@data-fancybox='gallery']/@href")

    movie.url = url
    movie.title = title.replace(movie.dvdid, '').strip()
    movie.preview_pics = preview_pics
    movie.publish_date = publish_date
    movie.duration = duration
    movie.genre = genre
    movie.genre_id = genre_id
    movie.actress = actress

def parse_clean_data(movie: MovieInfo):
    """解析指定番号的影片数据并进行清洗"""
    try:
        parse_data(movie)
    except SiteBlocked:
        raise
        logger.error('JavDB: 可能触发了反爬虫机制，请稍后再试')
    # 将此功能放在各个抓取器以保持数据的一致，避免影响转换（写入nfo时的信息来自多个抓取器的汇总，数据来源一致性不好）
    if cfg.Crawler.title__remove_actor:
        new_title = remove_trail_actor_in_title(movie.title, movie.actress)
        if new_title != movie.title:
            movie.ori_title = movie.title
            movie.title = new_title


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('082713-417')
    try:
        parse_clean_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
