"""从avsox抓取数据"""
import logging

from javsp.web.base import get_html
from javsp.web.exceptions import *
from javsp.config import Cfg, CrawlerID
from javsp.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_url = Cfg().network.proxy_free[CrawlerID.avsox]


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # avsox无法直接跳转到影片的网页，因此先搜索再从搜索结果中寻找目标网页
    full_id = movie.dvdid
    if full_id.startswith('FC2-'):
        full_id = full_id.replace('FC2-', 'FC2-PPV-')
    html = get_html(f'{base_url}tw/search/{full_id}')
    ids = html.xpath("//div[@class='photo-info']/span/date[1]/text()")
    urls = html.xpath("//a[contains(@class, 'movie-box')]/@href")
    ids_lower = list(map(str.lower, ids))
    if full_id.lower() in ids_lower:
        url = urls[ids_lower.index(full_id.lower())]
        url = url.replace('/tw/', '/cn/', 1)
    else:
        raise MovieNotFoundError(__name__, movie.dvdid, ids)

    # 提取影片信息
    html = get_html(url)
    container = html.xpath("/html/body/div[@class='container']")[0]
    title = container.xpath("h3/text()")[0]
    cover = container.xpath("//a[@class='bigImage']/@href")[0]
    info = container.xpath("div/div[@class='col-md-3 info']")[0]
    dvdid = info.xpath("p/span[@style]/text()")[0]
    publish_date = info.xpath("p/span[text()='发行时间:']")[0].tail.strip()
    duration = info.xpath("p/span[text()='长度:']")[0].tail.replace('分钟', '').strip()
    producer, serial = None, None
    producer_tag = info.xpath("p[text()='制作商: ']")[0].getnext().xpath("a")
    if producer_tag:
        producer = producer_tag[0].text_content()
    serial_tag = info.xpath("p[text()='系列:']")
    if serial_tag:
        serial = serial_tag[0].getnext().xpath("a/text()")[0]
    genre = info.xpath("p/span[@class='genre']/a/text()")
    actress = container.xpath("//a[@class='avatar-box']/span/text()")

    movie.dvdid = dvdid.replace('FC2-PPV-', 'FC2-')
    movie.url = url
    movie.title = title.replace(dvdid, '').strip()
    movie.cover = cover
    movie.publish_date = publish_date
    movie.duration = duration
    movie.genre = genre
    movie.actress = actress
    if full_id.startswith('FC2-'):
        # avsox把FC2作品的拍摄者归类到'系列'而制作商固定为'FC2-PPV'，这既不合理也与其他的站点不兼容，因此进行调整
        movie.producer = serial
    else:
        movie.producer = producer
        movie.serial = serial


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('082713-417')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
