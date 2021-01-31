"""从JavLibrary抓取数据"""
import os
import sys
import logging
from datetime import date
from urllib.parse import urljoin


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import get_html
from core.config import cfg
from core.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_url = cfg.ProxyFree.javlib
permanent_url = 'https://www.javlib.com'


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    url = f'{base_url}/cn/vl_searchbyid.php?keyword={movie.dvdid}'
    html = get_html(url)
    container = html.xpath("/html/body/div/div[@id='rightcolumn']")[0]
    title_tag = container.xpath("div/h3/a/text()")
    if not title_tag:
        # 在有多个结果时，JavLibrary不会自动跳转（此时无法获取到标题），需要进一步处理
        video_tags = html.xpath("//div[@class='video'][@id]/a")
        # 通常第一部影片就是我们要找的，但是以免万一还是遍历所有搜索结果
        for tag in video_tags:
            tag_dvdid = tag.xpath("div[@class='id']/text()")[0]
            if tag_dvdid == movie.dvdid:
                new_url = urljoin(url, tag.xpath("@href")[0])
                html = get_html(new_url)
                container = html.xpath("/html/body/div/div[@id='rightcolumn']")[0]
                title_tag = container.xpath("div/h3/a/text()")
                logger.debug(f"'{movie.dvdid}'存在多个搜索结果，已自动选择: {new_url}")
                break
        else:
            logger.error(f"'{movie.dvdid}': 无法获取到影片结果")
    title = title_tag[0]
    cover = container.xpath("//img[@id='video_jacket_img']/@src")[0]
    info = container.xpath("//div[@id='video_info']")[0]
    dvdid = info.xpath("div[@id='video_id']//td[@class='text']/text()")[0]
    date_str = info.xpath("div[@id='video_date']//td[@class='text']/text()")[0]
    duration = info.xpath("div[@id='video_length']//span[@class='text']/text()")[0]
    director_tag = info.xpath("//span[@class='director']/a/text()")
    if director_tag:
        movie.director = director_tag[0]
    producer = info.xpath("//span[@class='maker']/a/text()")[0]
    publisher = info.xpath("//span[@class='label']/a/text()")[0]
    score_tag = info.xpath("//span[@class='score']/text()")
    if score_tag:
        movie.score = score_tag[0].strip('()')
    genre = info.xpath("//span[@class='genre']/a/text()")
    actress = info.xpath("//span[@class='star']/a/text()")

    movie.title = title.replace(dvdid, '').strip()
    if cover.startswith('//'):  # 补全URL中缺少的协议段
        cover = 'https:' + cover
    movie.cover = cover
    movie.publish_date = date.fromisoformat(date_str)
    movie.duration = duration
    movie.producer = producer
    movie.publisher = publisher
    movie.genre = genre
    movie.actress = actress


if __name__ == "__main__":
    movie = MovieInfo('IPZ-037')
    parse_data(movie)
    print(movie)
