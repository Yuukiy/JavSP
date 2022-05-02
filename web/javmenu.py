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
        logger.debug(f"'{movie.dvdid}': JavMenu无资源")
        return False
    html = resp2html(r)
    container = html.xpath("//div[@class='col-md-8 px-0']")[0]
    title = container.xpath("div[@class='col-12 mb-3']/h1/strong/text()")[0]
    cover_tag = container.xpath("//div[@class='single-video']")[0]
    if video_tag := cover_tag.find('video'):
        # URL首尾竟然也有空格……
        movie.cover = video_tag.get('data-poster').strip()
        movie.preview_video = video_tag.find('source').get('src').strip()
    else:
        movie.cover = container.xpath("//img[@class='lazy rounded']/@data-src")[0].strip()
    info = container.xpath("//div[@class='card-body']")[0]
    publish_date = info.xpath("div/span[contains(text(), '日期:')]")[0].getnext().text
    duration = info.xpath("div/span[contains(text(), '時長:')]")[0].getnext().text.replace('分鐘', '')
    producer = info.xpath("div/span[contains(text(), '製作:')]/following-sibling::a/span/text()")
    if producer:
        movie.producer = producer[0]
    genre_tags = info.xpath("//a[@class='genre']")
    genre, genre_id = [], []
    for tag in genre_tags:
        items = tag.get('href').split('/')
        pre_id = items[-3] + '/' + items[-1]
        genre.append(tag.text.strip())
        genre_id.append(pre_id)
        # genra的链接中含有censored字段，但是无法用来判断影片是否有码，因为完全不可靠……
    actress = info.xpath("div/span[contains(text(), '女優:')]/following-sibling::*/a/text()") or None
    magnet_table = container.xpath("//div[@id='download-tab']//tbody")
    if magnet_table:
        magnet_links = magnet_table[0].xpath("tr/td/a/@href")
        # 它的FC2数据是从JavDB抓的，不知道后面是否能正常更新
        movie.magnet = [i.replace('[javdb.com]','') for i in magnet_links]
    preview_pics = container.xpath("//a[@data-fancybox='gallery']/@href")

    movie.url = url
    movie.title = title.replace(movie.dvdid, '').strip()
    movie.preview_pics = preview_pics
    movie.publish_date = publish_date
    movie.duration = duration
    movie.genre = genre
    movie.genre_id = genre_id
    movie.actress = actress
    return True


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    movie = MovieInfo('082713-417')
    if parse_data(movie):
        print(movie)
    else:
        print('未抓取到数据: ' + repr(movie))
