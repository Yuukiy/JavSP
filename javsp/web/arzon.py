"""从arzon抓取数据"""
import os
import sys
import logging
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from javsp.web.base import request_get
from javsp.web.exceptions import *
from javsp.core.datatype import MovieInfo
import requests
from lxml import html

logger = logging.getLogger(__name__)
base_url = "https://www.arzon.jp"

def get_cookie():
    # https://www.arzon.jp/index.php?action=adult_customer_agecheck&agecheck=1&redirect=https%3A%2F%2Fwww.arzon.jp%2F
    skip_verify_url = "http://www.arzon.jp/index.php?action=adult_customer_agecheck&agecheck=1"
    session = requests.Session()
    session.get(skip_verify_url, timeout=(12, 7))
    return session.cookies.get_dict()

def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    full_id = movie.dvdid
    cookies = get_cookie()
    url = f'{base_url}/itemlist.html?t=&m=all&s=&q={full_id}'
    # url = f'{base_url}/imagelist.html?q={full_id}'
    r = request_get(url, cookies, delay_raise=True)
    if r.status_code == 404:
      raise MovieNotFoundError(__name__, movie.dvdid)
    # https://stackoverflow.com/questions/15830421/xml-unicode-strings-with-encoding-declaration-are-not-supported
    data = html.fromstring(r.content)

    urls = data.xpath("//h2/a/@href")
    if len(urls) == 0:
        raise MovieNotFoundError(__name__, movie.dvdid)

    item_url = base_url + urls[0]
    e = request_get(item_url, cookies, delay_raise=True)
    item =  html.fromstring(e.content)

    title = item.xpath("//div[@class='detail_title_new2']//h1/text()")[0]
    cover = item.xpath("//td[@align='center']//a/img/@src")[0]
    item_text = item.xpath("//div[@class='item_text']/text()")
    plot = [item.strip() for item in item_text if item.strip() != ''][0]
    preview_pics_arr = item.xpath("//div[@class='detail_img']//img/@src")
    # 使用列表推导式添加 "http:" 并去除 "m_"
    preview_pics = [("https:" + url).replace("m_", "") for url in preview_pics_arr]

    container = item.xpath("//div[@class='item_register']/table//tr")
    for row in container:
      key = row.xpath("./td[1]/text()")[0]
      contents = row.xpath("./td[2]//text()")
      content = [item.strip() for item in contents if item.strip() != '']
      index = 0
      value = content[index] if content and index < len(content) else None
      if key == "AV女優：":
        movie.actress = content
      if key == "AVメーカー：":
        movie.producer = value
      if key == "AVレーベル：":
        video_type = value
      if key == "シリーズ：":
        movie.serial = value
      if key == "監督：":
        movie.director = value
      if key == "発売日：" and value:
        movie.publish_date = re.search(r"\d{4}/\d{2}/\d{2}", value).group(0).replace("/", "-")
      if key == "収録時間：" and value:
        movie.duration = re.search(r'([\d.]+)分', value).group(1)
      if key == "品番：":
        dvd_id = value
      elif key == "タグ：":
        genre  = value

    genres = ''
    if video_type:
      genres = [video_type]
    if(genre != None):
      genres.append(genre)

    movie.genre = genres
    movie.url = item_url
    movie.title = title
    movie.plot = plot
    movie.cover = f'https:{cover}'
    movie.preview_pics = preview_pics

if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('csct-011')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
