"""从JavDB抓取数据"""
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import get_html
from core.config import cfg
from core.datatype import MovieInfo, GenreMap


base_url = cfg.ProxyFree.javdb
genre_map = GenreMap('data/genre_javdb_youma.jsonc')
permanent_url = 'https://www.javdb.com'


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # JavDB搜索番号时会有多个搜索结果，从中查找匹配番号的那个
    html = get_html(f'{base_url}/search?q={movie.dvdid}')
    ids = list(map(str.lower, html.xpath("//div[@id='videos']/div/div/a/div[@class='uid']/text()")))
    paths = html.xpath("//div[@id='videos']/div/div/a/@href")
    path = paths[ids.index(movie.dvdid.lower())]

    html = get_html(f'{base_url}/{path}')
    container = html.xpath("/html/body/section/div[@class='container']")[0]
    info = container.xpath("div/div/div/nav")[0]
    title = container.xpath("h2/strong/text()")[0]
    cover = container.xpath("//img[@class='video-cover']/@src")[0]
    preview_pics = container.xpath("//a[@class='tile-item'][@data-fancybox='gallery']/@href")
    preview_video_tag = container.xpath("//video[@id='preview-video']/source/@src")
    if preview_video_tag:
        preview_video = preview_video_tag[0]
        if preview_video.startswith('//'):
            preview_video = 'https:' + preview_video
        movie.preview_video = preview_video
    dvdid = info.xpath("div/span")[0].text_content()
    date_str = info.xpath("div/strong[text()='日期:']")[0].getnext().text
    duration = info.xpath("div/strong[text()='時長:']")[0].getnext().text.replace('分鍾', '').strip()
    director_tag = info.xpath("div/strong[text()='導演:']")
    if director_tag:
        movie.director = director_tag[0].getnext().text_content().strip()
    producer = info.xpath("div/strong[text()='片商:']")[0].getnext().text_content().strip()
    publisher = info.xpath("div/strong[text()='發行:']")[0].getnext().text_content().strip()
    serial_tag = info.xpath("div/strong[text()='系列:']")
    if serial_tag:
        movie.serial = serial_tag[0].getnext().text
    score_tag = info.xpath("//span[@class='score-stars']")
    if score_tag:
        score_str = score_tag[0].tail
        score = re.search(r'([\d.]+)分', score_str).group(1)
        movie.score = "{:.2f}".format(float(score)*2)
    genre = info.xpath("//strong[text()='類別:']/../span/a/text()")
    actress = info.xpath("//strong[text()='演員:']/../span/a/text()")
    magnet = container.xpath("//td[@class='magnet-name']/a/@href")

    movie.title = title.replace(dvdid, '').strip()
    movie.cover = cover
    movie.preview_pics = preview_pics
    movie.publish_date = date.fromisoformat(date_str)
    movie.duration = duration
    movie.producer = producer
    movie.publisher = publisher
    movie.genre = genre
    movie.actress = actress
    movie.magnet = [i.replace('[javdb.com]','') for i in magnet]


def parse_clean_data(movie: MovieInfo):
    """解析指定番号的影片数据并进行清洗"""
    parse_data(movie)
    movie.genre = genre_map.map(movie.genre)


if __name__ == "__main__":
    movie = MovieInfo('IPX-177')
    parse_clean_data(movie)
    print(movie)
