"""从JavLibrary抓取数据"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import get_html
from core.datatype import Movie


base_url = 'https://www.b49t.com'
permanent_url = 'https://www.javlib.com'


def parse_data(movie: Movie):
    """解析指定番号的影片数据"""
    html = get_html(f'{base_url}/cn/vl_searchbyid.php?keyword={movie.dvdid}')
    container = html.xpath("/html/body/div/div[@id='rightcolumn']")[0]
    title = container.xpath("div/h3/a/text()")[0]
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
    score = info.xpath("//span[@class='score']/text()")[0].strip('()')
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
    movie.score = score
    movie.genre = genre
    movie.actress = actress


if __name__ == "__main__":
    movie = Movie('IPX-177')
    parse_data(movie)
    print(movie)
