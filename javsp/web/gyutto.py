"""从https://gyutto.com/官网抓取数据"""
import logging
import time

from javsp.web.base import resp2html, request_get
from javsp.web.exceptions import *
from javsp.core.datatype import MovieInfo

logger = logging.getLogger(__name__)

# https://dl.gyutto.com/i/item266923
base_url = 'http://gyutto.com'
base_encode = 'euc-jp'

def get_movie_title(html):
    container = html.xpath("//h1")
    if len(container) > 0:
        container = container[0]
    title = container.text
    
    return title

def get_movie_img(html, index = 1):
    images = []
    container = html.xpath("//a[@class='highslide']/img")
    if len(container) > 0:
        if index == 0:
            return container[0].get('src')
        
        for row in container:
            images.append(row.get('src'))

    return images

def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # 去除番号中的'gyutto'字样
    id_uc = movie.dvdid.upper()
    if not id_uc.startswith('GYUTTO-'):
        raise ValueError('Invalid gyutto number: ' + movie.dvdid)
    gyutto_id = id_uc.replace('GYUTTO-', '')
    # 抓取网页
    url = f'{base_url}/i/item{gyutto_id}?select_uaflag=1'
    r = request_get(url, delay_raise=True)
    if r.status_code == 404:
        raise MovieNotFoundError(__name__, movie.dvdid)
    html = resp2html(r, base_encode)
    container = html.xpath("//dl[@class='BasicInfo clearfix']")

    for row in container:
        key = row.xpath(".//dt/text()")
        if key[0] == "サークル":
            producer = ''.join(row.xpath(".//dd/a/text()"))
        elif key[0] == "ジャンル":
            genre = row.xpath(".//dd/a/text()")
        elif key[0] == "配信開始日":
            date = row.xpath(".//dd/text()")
            date_str = ''.join(date)
            date_time = time.strptime(date_str, "%Y年%m月%d日")
            publish_date = time.strftime("%Y-%m-%d", date_time)

    plot = html.xpath("//div[@class='unit_DetailLead']/p/text()")[0]
    
    movie.title = get_movie_title(html)
    movie.cover = get_movie_img(html, 0)
    movie.preview_pics = get_movie_img(html)
    movie.dvdid = id_uc
    movie.url = url
    movie.producer = producer
    # movie.actress = actress
    # movie.duration = duration
    movie.publish_date = publish_date
    movie.genre = genre
    movie.plot = plot

if __name__ == "__main__":
    import pretty_errors

    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG
    movie = MovieInfo('gyutto-266923')

    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
