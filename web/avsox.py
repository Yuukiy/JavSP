"""从avsox抓取数据"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import get_html
from core.datatype import Movie


base_url = 'https://avsox.website'


def parse_data(movie: Movie):
    """解析指定番号的影片数据"""
    # avsox无法直接跳转到影片的网页，因此先搜索再从搜索结果中寻找目标网页
    html = get_html(f'{base_url}/cn/search/{movie.dvdid}')
    ids = html.xpath("//a[@class='movie-box mcaribbeancom']/div[@class='photo-info']/span/date[1]/text()")
    urls = html.xpath("//a[@class='movie-box mcaribbeancom']/@href")
    ids_lower = list(map(str.lower, ids))
    url = urls[ids_lower.index(movie.dvdid.lower())]
    # 提取影片信息
    html = get_html(url)
    container = html.xpath("/html/body/div[@class='container']")[0]
    title = container.xpath("h3/text()")[0]
    cover = container.xpath("//a[@class='bigImage']/@href")[0]
    info = container.xpath("div/div[@class='col-md-3 info']")[0]
    dvdid = info.xpath("p/span[@style]/text()")[0]
    date_str = info.xpath("p/span[text()='发行时间:']")[0].tail.strip()
    duration = info.xpath("p/span[text()='长度:']")[0].tail.replace('分钟', '').strip()
    producer_tags = info.xpath("p[text()='制作商: ']")[0].getnext().xpath("a")
    producer = [i.text_content() for i in producer_tags]
    serial = info.xpath("p[text()='系列:']")[0].getnext().xpath("a/text()")
    genre = info.xpath("p/span[@class='genre']/a/text()")
    actress = container.xpath("//a[@class='avatar-box']/span/text()")

    movie.title = title.replace(dvdid, '').strip()
    movie.cover = cover
    movie.publish_date = date.fromisoformat(date_str)
    movie.duration = duration
    movie.producer = producer
    movie.serial = serial
    movie.genre = genre
    movie.actress = actress


if __name__ == "__main__":
    movie = Movie('082713-417')
    parse_data(movie)
    print(movie)
