"""解析fc2fan本地镜像的数据"""
# FC2官网的影片下架就无法再抓取数据，如果用户有fc2fan的镜像，那可以尝试从镜像中解析影片数据
import os
import re
import sys
import logging
import lxml.html
import requests


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import resp2html
from web.exceptions import *
from core.config import cfg
from core.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_path = cfg.Crawler.fc2fan_local_path
use_local_mirror = os.path.exists(base_path)


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    if use_local_mirror:
        html_file = f'{base_path}/{movie.dvdid}.html'
        if not os.path.exists(html_file):
            raise MovieNotFoundError(__name__, movie.dvdid, html_file)
        html = lxml.html.parse(html_file)
    else:
        url = f"https://fc2club.top/html/{movie.dvdid}.html"
        r = requests.get(url)
        html = resp2html(r)
    container = html.xpath("//div[@class='col-sm-8']")[0]
    title = container.xpath("h3/text()")[0]
    score_str = container.xpath("h5/strong[text()='影片评分']")[0].tail.strip()
    match = re.search(r'\d+', score_str)
    if match:
        score = int(match.group()) / 10 # fc2fan站长是按100分来打分的
        movie.score = f'{score:.1f}'
    resource_info = container.xpath("h5/strong[text()='资源参数']")[0].tail
    if '无码' in resource_info:
        movie.uncensored = True
    elif '有码' in resource_info:
        movie.uncensored = False
    # FC2没有制作商和发行商的区分，作为个人市场，卖家更接近于制作商
    producer = container.xpath("h5/strong[text()='卖家信息']")[0].getnext().text.strip()
    genre = container.xpath("h5/strong[text()='影片标签']/../a/text()")
    actress = container.xpath("h5/strong[text()='女优名字']/../a/text()")
    preview_pics = container.xpath("//ul[@class='slides']/li/img/@src")
    if use_local_mirror:
        preview_pics = [os.path.normpath(os.path.join(base_path, i)) for i in preview_pics]
    # big_preview = container.xpath("//img[@id='thumbpic']/../@href")[0]    # 影片真实截图，目前暂时用不到

    movie.title = title
    movie.genre = genre
    movie.actress = actress
    movie.producer = producer
    if preview_pics:
        movie.preview_pics = preview_pics
        movie.cover = preview_pics[0]


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('FC2-1000967')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
