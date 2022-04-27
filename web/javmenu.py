"""从JavMenu抓取数据"""
import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import Request, resp2html
from core.datatype import MovieInfo


request = Request()

logger = logging.getLogger(__name__)
base_url = 'https://mrzyx.xyz'


def parse_data(movie: MovieInfo):
    """从网页抓取并解析指定番号的数据
    Args:
        movie (MovieInfo): 要解析的影片信息，解析后的信息直接更新到此变量内
    Returns:
        bool: True 表示解析成功，movie中携带有效数据；否则为 False
    """
    # JavMenu网页做得不怎么走心，将就了
    url = f'{base_url}/{movie.dvdid}'
    r = request.get(url)
    if r.status_code != 200:
        return False
    elif r.history:
        logger.debug('无影片')
        return False
    html = resp2html(r)
    container = html.xpath("//div[@class='col-md-8 px-0']")[0]
    title = container.xpath("div[@class='col-12 mb-3']/h1/strong/text()")[0]
    cover = container.xpath("//img[@class='lazy rounded']/@data-src")[0]
    info = container.xpath("//div[@class='card-body']")[0]
    publish_date = info.xpath("div/span[contains(text(), '日期:')]")[0].getnext().text
    duration = info.xpath("div/span[contains(text(), '時長:')]")[0].getnext().text.replace('分鐘', '')
    producer = info.xpath("div/span[contains(text(), '製作:')]/following-sibling::a/span/text()")[0]
    genre_tags = info.xpath("//a[@class='genre']")
    genre, genre_id = [], []
    for tag in genre_tags:
        items = tag.get('href').split('/')
        pre_id = items[-3] + '/' + items[-1]
        genre.append(tag.text.strip())
        genre_id.append(pre_id)
        # 判定影片有码/无码
        movie.uncensored = items[-3] == 'uncensored'
    actress = info.xpath("div/span[contains(text(), '女優:')]/following-sibling::*/span/text()")
    magnet_table = container.xpath("//div[@id='download-tab']//tbody")[0]
    magnet_links = magnet_table.xpath("tr/td/a/@href")
    preview_pics = container.xpath("//a[@data-fancybox='gallery']/@href")

    movie.url = url
    movie.title = title.replace(movie.dvdid, '').strip()
    movie.cover = cover
    movie.preview_pics = preview_pics
    movie.publish_date = publish_date
    movie.duration = duration
    movie.producer = producer
    movie.genre = genre
    movie.genre_id = genre_id
    if actress[0] != '暫無女優資料':
        movie.actress = actress
    # 它的FC2数据是从JavDB抓的，不知道后面是否能正常更新
    movie.magnet = [i.replace('[javdb.com]','') for i in magnet_links]
    return True


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    movie = MovieInfo('FC2-1899973')
    if parse_data(movie):
        print(movie)
    else:
        print('未抓取到数据: ' + repr(movie))
