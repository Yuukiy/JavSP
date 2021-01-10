"""从JavLibrary抓取数据"""
import sys
from datetime import date

sys.path.append('../') 
from web.base import get_html
from core.datatype import Movie


base_url = 'https://www.b49t.com'
permanent_url = 'https://www.javlib.com'


def parse_data(movie: Movie):
    """解析指定番号的影片数据"""
    html = get_html(f'{base_url}/cn/vl_searchbyid.php?keyword={movie.dvdid}')
    container = html.xpath("/html/body/div/div[@id='rightcolumn']")[0]
    title = container.xpath("div/h3/a/text()")[0]
    cover = container.xpath("//img[@id='video_jacket_img']/@src")
    info = container.xpath("//div[@id='video_info']")[0]
    dvdid = info.xpath("div[@id='video_id']//td[@class='text']/text()")[0]
    date_str = info.xpath("div[@id='video_date']//td[@class='text']/text()")[0]
    duration = info.xpath("div[@id='video_length']//span[@class='text']/text()")[0]
    director = info.xpath("//span[@class='director']/a/text()")
    producer = info.xpath("//span[@class='maker']/a/text()")
    publisher = info.xpath("//span[@class='label']/a/text()")
    score = info.xpath("//span[@class='score']/text()")[0].strip('()')
    genre = info.xpath("//span[@class='genre']/a/text()")
    actress = info.xpath("//span[@class='star']/a/text()")

    movie.title = title.replace(dvdid, '').strip()
    movie.cover = cover
    movie.publish_date = date.fromisoformat(date_str)
    movie.duration = duration
    movie.director = director
    movie.producer = producer
    movie.publisher = publisher
    movie.score = score
    movie.genre = genre
    movie.actress = actress


if __name__ == "__main__":
    movie = Movie('ipx-177')
    parse_data(movie)
    pass