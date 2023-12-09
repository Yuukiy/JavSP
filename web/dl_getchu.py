"""从dl.getchu官网抓取数据"""
import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import get_html, request_get
from web.exceptions import *
from core.config import cfg
from core.lib import strftime_to_minutes
from core.datatype import MovieInfo

logger = logging.getLogger(__name__)

# https://dl.getchu.com/i/item4045373
base_url = 'https://dl.getchu.com'
# dl.getchu用utf-8会乱码
base_encode = 'euc-jp'


def get_movie_title(html):
    container = html.xpath("//form[@action='https://dl.getchu.com/cart/']/div/table[2]")
    if len(container) > 0:
        container = container[0]
    rows = container.xpath('.//tr')
    title = ''
    for row in rows:
        cell_texts = []
        for cell in row.xpath('.//td/div'):
            # 获取单元格文本内容
            cell_text = None
            if cell.text:
                title = str(cell.text).strip()
    return title


def get_movie_img(html, getchu_id):
    img_src = ''
    container = html.xpath(f'//img[contains(@src, "{getchu_id}top.jpg")]')
    if len(container) > 0:
        container = container[0]
        img_src = container.get('src')
    return img_src


def get_movie_preview(html, getchu_id):
    preview_pics = []
    container = html.xpath(f'//img[contains(@src, "{getchu_id}_")]')
    if len(container) > 0:
        for c in container:
            preview_pics.append(c.get('src'))
    return preview_pics


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # 去除番号中的'GETCHU'字样
    id_uc = movie.dvdid.upper()
    if not id_uc.startswith('GETCHU-'):
        raise ValueError('Invalid GETCHU number: ' + movie.dvdid)
    getchu_id = id_uc.replace('GETCHU-', '')
    # 抓取网页
    url = f'{base_url}/i/item{getchu_id}'
    html = get_html(url, base_encode)
    container = html.xpath("//form[@action='https://dl.getchu.com/cart/']/div/table[3]")
    if len(container) > 0:
        container = container[0]
    rows = container.xpath('.//tr')

    producer = ''
    actress = []
    publish_date = ''  # 2015/08/13
    genre = []
    plot = ''
    for row in rows:
        cell_texts = []
        for cell in row.xpath('.//td'):
            # 获取单元格文本内容
            cell_text = None
            if cell.text:
                cell_text = cell.text.strip()
            # 是否包含a标签
            # 有的属性是用<a>表示的，不是text
            has_a_link = cell.find('.//a') is not None
            if has_a_link:
                cell_text = cell.xpath('.//a/text()')
            if cell_text is None:
                continue
            cell_texts.append(cell_text)
        if len(cell_texts) != 2:
            continue

        key = cell_texts[0]
        value = cell_texts[1]

        if 'サークル' in key:
            producer = str(value)
        elif '作者' in key:
            actress.append(value)
        elif '配信開始日' in key:
            publish_date = str(value)
            publish_date = publish_date.replace('/', '-')
        elif '趣向' in key:
            genre = value
        elif '作品内容' in key:
            plot = value
    movie.title = get_movie_title(html)
    movie.cover = get_movie_img(html, getchu_id)
    movie.preview_pics = get_movie_preview(html, getchu_id)
    movie.dvdid = id_uc
    movie.url = url
    movie.producer = producer
    movie.actress = actress
    movie.publish_date = publish_date
    movie.genre = genre
    movie.plot = plot


if __name__ == "__main__":
    import pretty_errors

    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('getchu-4053720')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
