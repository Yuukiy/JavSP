"""从JavDB抓取数据"""
import json
import os
import re
import logging
import time

import lxml.html

from javsp.web.base import Request, resp2html, open_in_chrome
from javsp.web.exceptions import *
from javsp.config import Cfg
from javsp.datatype import MovieInfo, GenreMap

# 初始化Request实例。使用scraper绕过CloudFlare后，需要指定网页语言，否则可能会返回其他语言网页，影响解析
request = Request(use_scraper=False)

cookie = Cfg().cookie.fantia
request.headers['Cookie'] = cookie
request.headers['x-requested-with'] = 'XMLHttpRequest'

API_POST = 'https://fantia.jp/api/v1/posts/{}'

logger = logging.getLogger(__name__)
base_url = 'https://fantia.jp/posts'

prefix = "fantia-post-"


# base_url ='https://fantia.jp/api/v1/posts'

def get_csrf_token(url) -> str | None:
    r = request.get(url, delay_raise=True)
    # 从meta中取出csrf-token, 重新发请求
    html = resp2html(r)
    csrf_token = html.xpath('//meta[@name="csrf-token"]')
    if len(csrf_token) > 0:
        csrf_token = csrf_token[0].get('content')
        if csrf_token:
            return csrf_token
        else:
            return None
    else:
        return None


def get_movie_preview_pics(post: json) -> None | list[str]:
    blog_comment_str = post.get('blog_comment')

    if not blog_comment_str:
        return None
    try:
        blog_comment = json.loads(blog_comment_str)
    except json.decoder.JSONDecodeError:
        logger.error(f"解析blog comment出错, blog_comment_str: {blog_comment_str}")
        return None

    pics = []
    for item in blog_comment.get('ops'):
        if item.get('insert') is None or type(item['insert']).__name__ != 'dict':
            continue
        img = item['insert'].get('image', '')
        if len(img) > 0:
            pics.append(img)

    return pics


def get_movie_actress(post: json) -> None | list[str]:
    if post.get('fanclub') and post['fanclub'].get('fanclub_name_with_creator_name'):
        actress = post['fanclub']['fanclub_name_with_creator_name']
        return [actress]

    return None


def get_movie_actress_pics(post: json) -> None | dict:
    actress = get_movie_actress(post)
    if actress is None or len(actress) == 0:
        return None

    actress = actress[0]

    if (post.get('fanclub')
            and post['fanclub'].get('icon')
            and post['fanclub']['icon'].get('original')
    ):
        actress_cover = post['fanclub']['icon']['original']
        return {actress: actress_cover}
    else:
        return None


def get_movie_genre(post: json) -> None | list[str]:
    # tags
    tags = []
    for tag in post.get('tags'):
        tag = tag.get('name', '')
        if len(tag) > 0:
            tags.append(tag)

    if len(tags) == 0:
        return None
    return tags


def parse_data(movie: MovieInfo):
    """从网页抓取并解析指定番号的数据
    Args:
        movie (MovieInfo): 要解析的影片信息，解析后的信息直接更新到此变量内
    """
    id = movie.dvdid.lower()
    if not id.startswith(prefix):
        raise ValueError(f"Invalid Fantia Post number: " + movie.dvdid)
    fantia_num = id.replace(prefix, '')
    post_url = f'{base_url}/{fantia_num}'

    csrf_token = get_csrf_token(post_url)

    if not csrf_token:
        raise WebsiteError(f"无法从页面中获取 fantia-post-{fantia_num} 的 csrf-token")

    request.headers['x-csrf-token'] = csrf_token
    url = API_POST.format(fantia_num)
    data = request.get(url, delay_raise=True).json()

    post = data.get('post')
    if post is None:
        raise ValueError(f'无法获取fantia-post-{fantia_num}的数据')

    # cover
    cover = ''
    if post.get('thumb') and post['thumb'].get('original'):
        cover = post['thumb']['original']


    movie.title = post.get('title', '')
    movie.plot = post.get('comment', '')

    movie.cover = cover
    movie.genre = get_movie_genre(post)
    movie.actress = get_movie_actress(post)
    movie.actress_pics = get_movie_actress_pics(post)
    movie.preview_pics = get_movie_preview_pics(post)

    movie.url = post_url
    movie.uncensored = False


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

    movie = MovieInfo('fantia-post-786061')
    try:
        parse_clean_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
