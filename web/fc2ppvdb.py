"""从FC2PPVDB抓取数据"""
import os
import sys
import logging
from typing import List


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import get_html, request_get
from web.exceptions import *
from core.config import cfg
from core.lib import strftime_to_minutes
from core.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_url = 'https://fc2ppvdb.com'


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # 去除番号中的'FC2'字样
    id_uc = movie.dvdid.upper()
    if not id_uc.startswith('FC2-'):
        raise ValueError('Invalid FC2 number: ' + movie.dvdid)
    fc2_id = id_uc.replace('FC2-', '')
    # 抓取网页
    url = f'{base_url}/articles/{fc2_id}'
    html = get_html(url)
    container = html.xpath("//div[@class='container lg:px-5 px-2 py-12 mx-auto']/div[1]")
    if len(container) > 0:
        container = container[0]
    else:
        raise MovieNotFoundError(__name__, movie.dvdid)
    
    title = container.xpath("//h2/a/text()")
    thumb_pic = container.xpath(f"//img[@alt='{fc2_id}']/@src")
    duration_str = container.xpath("//div[starts-with(text(),'収録時間：')]/span/text()")
    actress = container.xpath("//div[starts-with(text(),'女優：')]/span/a/text()")
    genre = container.xpath("//div[starts-with(text(),'タグ：')]/span/a/text()")
    publish_date = container.xpath("//div[starts-with(text(),'販売日：')]/span/text()")
    publisher = container.xpath("//div[starts-with(text(),'販売者：')]/span/a/text()")
    uncensored_str = container.xpath("//div[starts-with(text(),'モザイク：')]/span/text()")
    uncensored_str_f = get_list_first(uncensored_str);
    uncensored = True if uncensored_str_f == '無' else False if uncensored_str_f == '有' else None
    preview_pics = None
    preview_video = container.xpath("//a[starts-with(text(),'サンプル動画')]/@href")

    movie.dvdid = id_uc
    movie.url = url
    movie.title = get_list_first(title)
    movie.genre = genre
    movie.actress = actress
    movie.duration = str(strftime_to_minutes(get_list_first(duration_str)))
    movie.publish_date = get_list_first(publish_date)
    movie.publisher = get_list_first(publisher)
    movie.uncensored = uncensored
    movie.preview_pics = preview_pics
    movie.preview_video = get_list_first(preview_video)

    # FC2的封面是220x220的，和正常封面尺寸、比例都差太多。如果有预览图片，则使用第一张预览图作为封面
    if movie.preview_pics:
        movie.cover = preview_pics[0]
    else:
        movie.cover = get_list_first(thumb_pic)

def get_list_first(list:List):
    return list[0] if list and len(list) > 0 else None

if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('FC2-4497837')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
