"""从蚊香社-prestige抓取数据"""
import os
import re
import sys
import logging


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import *
from web.exceptions import *
from core.config import cfg
from core.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_url = 'https://www.prestige-av.com'
# prestige要求访问者携带已通过R18认证的cookies才能够获得完整数据，否则会被重定向到认证页面
# （其他多数网站的R18认证只是在网页上遮了一层，完整数据已经传回，不影响爬虫爬取）
cookies = {'age_auth': '1'}


def parse_data(movie: MovieInfo):
    """从网页抓取并解析指定番号的数据
    Args:
        movie (MovieInfo): 要解析的影片信息，解析后的信息直接更新到此变量内
    """
    url = f'{base_url}/goods/goods_detail.php?sku={movie.dvdid}'
    resp = request_get(url, cookies=cookies, delay_raise=True)
    if resp.status_code == 500:
        # 500错误表明prestige没有这部影片的数据，不是网络问题，因此不再重试
        raise MovieNotFoundError(__name__, movie.dvdid)
    resp.raise_for_status()
    html = resp2html(resp)
    if 'ﾊﾟﾗﾒｰﾀｴﾗｰが発生しました' in html.text_content():
        # prestige更新了找不到影片时的提示(不确定之前的HTTP 500形式是否已弃用)
        raise MovieNotFoundError(__name__, movie.dvdid)

    container = html.xpath("//div[@class='section product_layout_01']")[0]
    title = container.xpath("div/h1")[0].text_content().strip()
    cover = container.xpath("div/p/a[@class='sample_image']/@href")[0]
    # 这里使用following-sibling而不是getnext，因为getnext会获取到空格、tab等空文本
    actress = container.xpath("//dt[text()='出演：']/following-sibling::dd[1]/a/text()")
    # 移除女优名中的空格，使女优名与其他网站保持一致
    actress = [i.replace(' ', '') for i in actress]
    duration_str = container.xpath("//dt[text()='収録時間：']")[0].getnext().text_content()
    match = re.search(r'\d+', duration_str)
    if match:
        movie.duration = match.group(0)
    date_str = container.xpath("//dt[text()='発売日：']/following-sibling::dd[1]/a/text()")[0]
    publish_date = date_str.replace('/', '-')
    producer = container.xpath("//dt[text()='メーカー名：']/following-sibling::dd[1]/a/text()")[0]
    dvdid = container.xpath("//dt[text()='品番：']")[0].getnext().text_content()
    genre_tags = container.xpath("//dt[text()='ジャンル：']/following-sibling::dd[1]/a")
    genre, genre_id = [], []
    for tag in genre_tags:
        genre.append(tag.text)
        genre_id.append(tag.get('href').split('=')[-1])
    serial = container.xpath("//dt[text()='レーベル：']/following-sibling::dd[1]/a/text()")[0]
    plot = container.xpath("//h2[text()='レビュー']/following-sibling::p")[0].text.strip()
    preview_pics = container.xpath("//li/a[@class='sample_image']/@href")

    # 对于2016年开始的影片，尝试获取高清封面地址（但也并不是每部影片都有，特别是2016年早期）
    year = int(publish_date.split('-')[0])
    if year >= 2016:
        # 形如'/images/corner/goods/prestige/abp/647/pb_e_abp-647.jpg'的地址，移除其中的'_e'后即为高清封面
        big_cover = cover.replace('_e_', '_')
        movie.big_cover = big_cover

    movie.url = url
    movie.dvdid = dvdid
    movie.title = title
    movie.cover = cover
    movie.actress = actress
    movie.publish_date = publish_date
    movie.producer = producer
    movie.genre = genre
    movie.genre_id = genre_id
    movie.serial = serial
    movie.plot = plot
    movie.preview_pics = preview_pics
    movie.uncensored = False    # prestige服务器在日本且面向日本国内公开发售，不会包含无码片


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('ABP-647')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
