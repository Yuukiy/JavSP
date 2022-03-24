"""从avsox抓取数据"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import get_html
from core.config import cfg
from core.datatype import MovieInfo


base_url = cfg.ProxyFree.avsox


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # avsox无法直接跳转到影片的网页，因此先搜索再从搜索结果中寻找目标网页
    html = get_html(f'{base_url}/cn/search/{movie.dvdid}')
    ids = html.xpath("//div[@class='photo-info']/span/date[1]/text()")
    urls = html.xpath("//a[contains(@class, 'movie-box')]/@href")
    ids_lower = list(map(str.lower, ids))
    try:
        url = urls[ids_lower.index(movie.dvdid.lower())]
    except ValueError:
        # ValueError 表明找不到这部影片，直接返回
        return

    # 提取影片信息
    html = get_html(url)
    container = html.xpath("/html/body/div[@class='container']")[0]
    title = container.xpath("h3/text()")[0]
    cover = container.xpath("//a[@class='bigImage']/@href")[0]
    info = container.xpath("div/div[@class='col-md-3 info']")[0]
    dvdid = info.xpath("p/span[@style]/text()")[0]
    publish_date = info.xpath("p/span[text()='发行时间:']")[0].tail.strip()
    duration = info.xpath("p/span[text()='长度:']")[0].tail.replace('分钟', '').strip()
    producer_tag = info.xpath("p[text()='制作商: ']")[0].getnext().xpath("a")
    if producer_tag:
        movie.producer = producer_tag[0].text_content()
    serial_tag = info.xpath("p[text()='系列:']")
    if serial_tag:
        movie.serial = serial_tag[0].getnext().xpath("a/text()")[0]
    genre = info.xpath("p/span[@class='genre']/a/text()")
    actress = container.xpath("//a[@class='avatar-box']/span/text()")

    movie.dvdid = dvdid
    movie.url = url
    movie.title = title.replace(dvdid, '').strip()
    movie.cover = cover
    movie.publish_date = publish_date
    movie.duration = duration
    movie.genre = genre
    movie.actress = actress


if __name__ == "__main__":
    movie = MovieInfo('130614-KEIKO')
    parse_data(movie)
    print(movie)
