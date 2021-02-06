"""从JavBus抓取数据"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import get_html
from core.func import *
from core.config import cfg
from core.datatype import MovieInfo, GenreMap


base_url = cfg.ProxyFree.javbus
genre_map = GenreMap('data/genre_javbus.csv')
permanent_url = 'https://www.javbus.com'


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    html = get_html(f'{base_url}/{movie.dvdid}')
    container = html.xpath("/html/body/div[@class='container']")[0]
    title = container.xpath("h3/text()")[0]
    cover = container.xpath("//a[@class='bigImage']/img/@src")[0]
    preview_pics = container.xpath("//div[@id='sample-waterfall']/a/@href")
    info = container.xpath("//div[@class='col-md-3 info']")[0]
    dvdid = info.xpath("p/span[text()='識別碼:']")[0].getnext().text
    publish_date = info.xpath("p/span[text()='發行日期:']")[0].tail.strip()
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
    # JavBus的磁力链接是依赖js脚本加载的，在静态网页中没有，因此实际上并不能解析
    # magnet = html.xpath("//table[@id='magnet-table']/tr/td[1]/a/@href")
    # actress, actress_pics
    actress, actress_pics = [], {}
    actress_tags = html.xpath("//a[@class='avatar-box']/div/img")
    for tag in actress_tags:
        name = tag.get('title')
        pic_url = tag.get('src')
        actress.append(name)
        if not pic_url.endswith('nowprinting.gif'):     # 略过默认的头像
            actress_pics[name] = pic_url
    # genre, genre_norm
    genre, genre_id = [], []
    for tag in genre_tags:
        tag_url = tag.get('href')
        pre_id = tag_url.split('/')[-1]
        genre.append(tag.text)
        if 'uncensored' in tag_url:
            movie.uncensored = True
            genre_id.append('uncensored-' + pre_id)
        else:
            movie.uncensored = False
            genre_id.append(pre_id)
    # 整理数据并更新movie的相应属性
    movie.title = title.replace(dvdid, '').strip()
    movie.cover = cover
    movie.preview_pics = preview_pics
    movie.publish_date = publish_date
    movie.duration = duration
    movie.producer = producer
    movie.publisher = publisher
    movie.genre = genre
    movie.genre_id = genre_id
    movie.actress = actress
    movie.actress_pics = actress_pics


def parse_clean_data(movie: MovieInfo):
    """解析指定番号的影片数据并进行清洗"""
    parse_data(movie)
    movie.genre_norm = genre_map.map(movie.genre_id)
    movie.genre_id = None   # 没有别的地方需要再用到，清空genre id（暗示已经完成转换）
    movie.title = remove_trail_actor_in_title(movie.title, movie.actress)


if __name__ == "__main__":
    movie = MovieInfo('IPX-177')
    parse_clean_data(movie)
    print(movie)
