"""从JavDB抓取数据"""
import re
import sys
from datetime import date

sys.path.append('../') 
from web.base import get_html
from core.datatype import Movie


base_url = 'https://www.javdb6.com'
permanent_url = 'https://www.javdb.com'


def parse_data(movie: Movie):
    """解析指定番号的影片数据"""
    # JavDB搜索番号时会有多个搜索结果，从中查找匹配番号的那个
    html = get_html(f'{base_url}/search?q={movie.dvdid}', encoding='utf-8')
    ids = list(map(str.lower, html.xpath("//div[@id='videos']/div/div/a/div[@class='uid']/text()")))
    paths = html.xpath("//div[@id='videos']/div/div/a/@href")
    path = paths[ids.index(movie.dvdid.lower())]

    html = get_html(f'{base_url}/{path}', encoding='utf-8')
    container = html.xpath("/html/body/section/div[@class='container']")[0]
    info = container.xpath("div/div/div/nav")[0]
    title = container.xpath("h2/strong/text()")[0]
    cover = container.xpath("//img[@class='video-cover']/@src")[0]
    preview_pics = container.xpath("//a[@class='tile-item'][@data-fancybox='gallery']")
    preview_video = container.xpath("//video[@id='preview-video']/source/@src")
    dvdid = info.xpath("div/span")[0].text_content()
    date_str = info.xpath("div/strong[text()='日期:']")[0].getnext().text
    duration = info.xpath("div/strong[text()='時長:']")[0].getnext().text.replace('分鍾', '').strip()
    director = info.xpath("div/strong[text()='導演:']")[0].getnext().text_content().strip()
    producer = info.xpath("div/strong[text()='片商:']")[0].getnext().text_content().strip()
    publisher = info.xpath("div/strong[text()='發行:']")[0].getnext().text_content().strip()
    score_str = info.xpath("//span[@class='score-stars']")[0].tail
    genre = info.xpath("//strong[text()='類別:']/../span/a/text()")
    actress = info.xpath("//strong[text()='演員:']/../span/a/text()")
    score = re.search(r'([\d.]+)分', score_str).group(1)
    magnet = container.xpath("//td[@class='magnet-name']/a/@href")

    movie.title = title.replace(dvdid, '').strip()
    movie.cover = cover
    movie.preview_pics = preview_pics
    movie.preview_video = preview_video
    movie.publish_date = date.fromisoformat(date_str)
    movie.duration = duration
    movie.director = director
    movie.producer = producer
    movie.publisher = publisher
    movie.score = "{:.2f}".format(float(score)*2)
    movie.genre = genre
    movie.actress = actress
    movie.magnet = magnet


if __name__ == "__main__":
    movie = Movie('IPX-177')
    parse_data(movie)
    print(movie)
