"""从JavBus抓取数据"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import get_html
from core.datatype import Movie


base_url = 'https://www.busfan.club'
permanent_url = 'https://www.javbus.com'


def parse_data(movie: Movie):
    """解析指定番号的影片数据"""
    html = get_html(f'{base_url}/{movie.dvdid}')
    container = html.xpath("/html/body/div[@class='container']")[0]
    title = container.xpath("h3/text()")[0]
    cover = container.xpath("//a[@class='bigImage']/img/@src")
    preview_pics = container.xpath("div[@id='sample-waterfall']/a/div/img/@src")
    info = container.xpath("//div[@class='col-md-3 info']")[0]
    dvdid = info.xpath("p/span[text()='識別碼:']")[0].getnext().text
    date_str = info.xpath("p/span[text()='發行日期:']")[0].tail.strip()
    duration = info.xpath("p/span[text()='長度:']")[0].tail.replace('分鐘', '').strip()
    director_tag = info.xpath("p/span[text()='導演:']")
    if director_tag:    # xpath没有匹配时将得到空列表
        movie.director = director_tag[0].getnext().text.strip()
    producer = info.xpath("p/span[text()='製作商:']")[0].getnext().text.strip()
    publisher = info.xpath("p/span[text()='發行商:']")[0].getnext().text.strip()
    serial_tag = info.xpath("p/span[text()='系列:']")
    if serial_tag:
        movie.serial = serial_tag[0].getnext().text
    genre_tags = info.xpath("p[text()='類別:']")[0].getnext().xpath("span/a")
    actress = info.xpath("//div[@class='star-name']/a/@title")
    magnet = html.xpath("//table[@id='magnet-table']/tr/td[1]/a/@href")
    genre = [i.text for i in genre_tags]
    # 整理数据并更新movie的相应属性
    movie.title = title.replace(dvdid, '').strip()
    movie.cover = cover
    movie.preview_pics = preview_pics
    movie.publish_date = date.fromisoformat(date_str)
    movie.duration = duration
    movie.producer = producer
    movie.publisher = publisher
    movie.genre = genre
    movie.actress = actress
    movie.magnet = magnet


if __name__ == "__main__":
    movie = Movie('IPX-177')
    parse_data(movie)
    print(movie)
