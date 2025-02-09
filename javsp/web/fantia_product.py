"""从JavDB抓取数据"""
import os
import re
import logging

import lxml.html

from javsp.web.base import Request, resp2html
from javsp.web.exceptions import *
from javsp.config import Cfg
from javsp.datatype import MovieInfo, GenreMap

# 初始化Request实例。使用scraper绕过CloudFlare后，需要指定网页语言，否则可能会返回其他语言网页，影响解析
request = Request(use_scraper=False)

cookie = Cfg().cookie.fantia
request.headers['Cookie'] = cookie

logger = logging.getLogger(__name__)
base_url = 'https://fantia.jp/products'


def get_html_wrapper(url):
    """包装外发的request请求并负责转换为可xpath的html，同时处理Cookies无效等问题"""
    global request, cookies_pool
    if len(cookie) == 0:
        raise ValueError('检测到fantia-product-的影片, 但fantia cookie为空')
    r = request.get(url, delay_raise=True)
    if r.status_code == 200:
        html = resp2html(r)
        return html
    else:
        raise WebsiteError(f'fantia product: {r.status_code} 非预期状态码: {url}')


def parse_data(movie: MovieInfo):
    """从网页抓取并解析指定番号的数据
    Args:
        movie (MovieInfo): 要解析的影片信息，解析后的信息直接更新到此变量内
    """
    id = movie.dvdid.lower()
    prefix = "fantia-product-"
    if not id.startswith(prefix):
        raise ValueError(f"Invalid Fantia Product number: " + movie.dvdid)
    fantia_num = id.replace(prefix, '')
    url = f'{base_url}/{fantia_num}'

    try:
        html: lxml.html.HtmlComment = get_html_wrapper(url)
    except (SitePermissionError, CredentialError):
        return

    # title
    title = html.xpath("//div[@class='product-header']/h1")
    if len(title) > 0:
        title = title[0].text_content()

    # plot
    plot_vec = html.xpath("//div[@class='product-description']/div/p")
    plot = ''
    for line in plot_vec:
        plot += line.text

    # cover
    cover = html.xpath("//picture/img[@class='img-fluid ']")
    if len(cover) > 0:
        cover = str(cover[0].get('src')).strip()

    # actress
    actress = html.xpath("//h1[@class='fanclub-name']/a")
    actress_str = actress[0].text.strip() if actress else None
    actress = [actress_str] if actress_str else []

    # actress_pic
    # 为了使用actress_alias.json,需要有演员头像,好在fantia都能获取到
    actress_pics = {}
    actress_pic = html.xpath("//div[@class='fanclub-header']/a/picture/img")
    if len(actress_pic) > 0:
        actress_pic = str(actress_pic[0].get('data-src')).strip()
        print(actress_pic)
        actress_pics[actress_str] = actress_pic

    # genre
    genres = []
    tags_1 = html.xpath("//div[@class='product-header']/div/div/a")
    for genre in tags_1:
        genre = str(genre.text).removeprefix('#').strip()
        if len(genre) > 0:
            genres.append(genre)
    tags_2 = html.xpath("//div[@class='product-header']/div/a")
    for genre in tags_2:
        genre = str(genre.text).removeprefix('#').strip()
        if len(genre) > 0:
            genres.append(genre)

    # preview_pics

    movie.title = title
    movie.dvdid = id
    movie.url = url
    movie.cover = cover
    movie.plot = plot
    movie.actress = actress
    movie.genre = genres
    movie.actress_pics = actress_pics
    movie.uncensored = False  # 没在fantia上看到过无码的


def parse_clean_data(movie: MovieInfo):
    """解析指定番号的影片数据并进行清洗"""
    try:
        parse_data(movie)
        # 检查封面URL是否真的存在对应图片
        if movie.cover is not None:
            r = request.head(movie.cover)
            if r.status_code != 200:
                movie.cover = None
    except SiteBlocked:
        raise
        logger.error('unexpected error')




if __name__ == "__main__":
    import pretty_errors

    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('fantia-product-648810')
    try:
        parse_clean_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
