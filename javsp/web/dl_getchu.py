"""从dl.getchu官网抓取数据"""
import re
import logging

from javsp.web.base import resp2html, request_get
from javsp.web.exceptions import *
from javsp.core.datatype import MovieInfo

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
        for cell in row.xpath('.//td/div'):
            # 获取单元格文本内容
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


DURATION_PATTERN = re.compile(r'(?:動画)?(\d+)分')
def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # 去除番号中的'GETCHU'字样
    id_uc = movie.dvdid.upper()
    if not id_uc.startswith('GETCHU-'):
        raise ValueError('Invalid GETCHU number: ' + movie.dvdid)
    getchu_id = id_uc.replace('GETCHU-', '')
    # 抓取网页
    url = f'{base_url}/i/item{getchu_id}'
    r = request_get(url, delay_raise=True)
    if r.status_code == 404:
        raise MovieNotFoundError(__name__, movie.dvdid)
    html = resp2html(r, base_encode)
    container = html.xpath("//form[@action='https://dl.getchu.com/cart/']/div/table[3]")
    if len(container) > 0:
        container = container[0]
    # 将表格提取为键值对
    rows = container.xpath('.//table/tr')
    kv_rows = [i for i in rows if len(i) == 2]
    data = {}
    for row in kv_rows:
        # 获取单元格文本内容
        key = row.xpath("td[@class='bluetext']/text()")[0]
        # 是否包含a标签: 有的属性是用<a>表示的，不是text
        a_tags = row.xpath("td[2]/a")
        if a_tags:
            value = [i.text for i in a_tags]
        else:
            # 获取第2个td标签的内容（下标从1开始计数）
            value = row.xpath("td[2]/text()")
        data[key] = value

    for key, value in data.items():
        if key == 'サークル':
            movie.producer = value[0]
        elif key == '作者':
            # 暂时没有在getchu找到多个actress的片子
            movie.actress = [i.strip() for i in value]
        elif key == '画像数&ページ数':
            match = DURATION_PATTERN.search(' '.join(value))
            if match:
                movie.duration = match.group(1)
        elif key == '配信開始日':
            movie.publish_date = value[0].replace('/', '-')
        elif key == '趣向':
            movie.genre = value
        elif key == '作品内容':
            idx = -1
            for i, line in enumerate(value):
                if line.lstrip().startswith('※'):
                    idx = i
                    break
            movie.plot = ''.join(value[:idx])

    movie.title = get_movie_title(html)
    movie.cover = get_movie_img(html, getchu_id)
    movie.preview_pics = get_movie_preview(html, getchu_id)
    movie.dvdid = id_uc
    movie.url = url


if __name__ == "__main__":
    import pretty_errors

    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('getchu-4041026')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
