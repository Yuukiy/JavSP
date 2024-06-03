"""从getchu官网抓取数据"""
import os
import re
import sys
import logging
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import resp2html, request_get
from web.exceptions import *
from core.datatype import MovieInfo

logger = logging.getLogger(__name__)
# dl.getchu用utf-8会乱码
base_encode = 'euc-jp'

def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # 去除番号中的'GETCHU'字样
    id_uc = movie.dvdid.upper()
    if not id_uc.startswith('GETCHU-'):
        raise ValueError('Invalid GETCHU number: ' + movie.dvdid)
    getchu_id = id_uc.replace('GETCHU-', '')
    # 抓取网页
    url = f'https://www.getchu.com/soft.phtml?id={getchu_id}&gc=gc'
    r = request_get(url, delay_raise=True)
    if r.status_code == 404:
        raise MovieNotFoundError(__name__, movie.dvdid)
    html = resp2html(r, base_encode)

    title = html.xpath('//*[@id="soft-title"]/text()')[0].strip()

    table = html.xpath('//table[@style="padding:1px;"]//tr')
    producer_keys = ["サークル：","ブランド："]
    for row in table:
        key = row.xpath('.//td[@valign="top"]/text()')
        if len(key) > 0:
            key = key[0]
        if key in producer_keys:
            if key == producer_keys[0]:
                producer = row.xpath('.//td[@align="top"]/text()')
            elif key == producer_keys[1]:
                producer = row.xpath('.//td[@align="top"]/a/text()')[0]
        elif key == "発売日：":
            date = row.xpath('.//td[@align="top"]/a/text()')[0]
            date_time = time.strptime(date, "%Y/%m/%d")
            publish_date = time.strftime("%Y-%m-%d", date_time)
        elif key == "サブジャンル：":
            genre = row.xpath('.//td[@align="top"]/a/text()')

    remove_genre_items = ['[一覧]']
    for item in remove_genre_items:
        if item in genre:
            genre.remove(item)

    brand = html.xpath('//*[@align="top"]/text()')[0].strip()
    description = html.xpath('//*[@class="tablebody"]/text()')
    image_url = html.xpath('//*[@class="highslide"]/img/@src')

    movie.title = title
    movie.cover = image_url[0]
    movie.preview_pics = image_url
    movie.dvdid = id_uc
    movie.url = url
    movie.producer = producer
    movie.publish_date = publish_date
    movie.genre = genre
    movie.plot = description


if __name__ == "__main__":
    import pretty_errors

    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('getchu-1280188')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
