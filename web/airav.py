"""从airav抓取数据"""
import os
import sys
import logging
from datetime import date


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import *
from core.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_url = 'https://www.airav.wiki'


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # airav也提供简体，但是部分影片的简介只在繁体界面下有，因此抓取繁体页面的数据
    html = get_html(f'{base_url}/video/{movie.dvdid}')
    # airav的部分网页样式是通过js脚本生成的，调试和解析xpath时要根据未经脚本修改的原始网页来筛选元素
    if html.xpath("/html/head/title") == 'AIRAV-WIKI':
        logger.debug(f"'{movie.dvdid}': airav无资源")
        return
    container = html.xpath("//div[@class='min-h-500 row']")[0]
    cover = html.xpath("/html/head/meta[@property='og:image']/@content")[0]
    info = container.xpath("//div[@class='d-flex videoDataBlock']")[0]
    preview_pics = info.xpath("div[@class='mobileImgThumbnail']/a/@href")
    # airav部分资源也有预览片，但是预览片似乎是通过js获取的blob链接，无法通过静态网页解析来获取
    title = info.xpath("h5/text()")[0]
    dvdid = info.xpath("h5/text()")[1]
    genre = info.xpath("//div[@class='tagBtnMargin']/a/text()")
    actress = info.xpath("//li[@class='videoAvstarListItem']/a/text()")
    producer = info.xpath("//li[text()='廠商']/a/text()")[0]
    date_str = info.xpath("//li[text()='發片日期']/text()[last()]")[0]
    plot = info.xpath("//div[@class='synopsis']/p/text()")[0]

    movie.title = title
    movie.cover = cover
    movie.preview_pics = preview_pics
    movie.publish_date = date.fromisoformat(date_str)
    movie.producer = producer
    movie.genre = genre
    movie.actress = actress
    movie.plot = plot


if __name__ == "__main__":
    movie = MovieInfo('IPX-177')
    parse_data(movie)
    print(movie)