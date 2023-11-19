"""从av-wiki抓取数据"""
import os
import sys
import logging


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import *
from web.exceptions import *
from core.datatype import MovieInfo

logger = logging.getLogger(__name__)
base_url = 'https://av-wiki.net'


def parse_data(movie: MovieInfo):
    """从网页抓取并解析指定番号的数据
    Args:
        movie (MovieInfo): 要解析的影片信息，解析后的信息直接更新到此变量内
    """
    movie.url = url = f'{base_url}/{movie.dvdid}'
    resp = request_get(url, delay_raise=True)
    if resp.status_code == 404:
        raise MovieNotFoundError(__name__, movie.dvdid)
    html = resp2html(resp)

    cover_tag = html.xpath("//header/div/a[@class='image-link-border']/img")
    if cover_tag:
        try:
            srcset = cover_tag[0].get('srcset').split(', ')
            src_set_urls = {}
            for src in srcset:
                url, width = src.split()
                width = int(width.rstrip('w'))
                src_set_urls[width] = url
            max_pic = sorted(src_set_urls.items(), key=lambda x:x[0], reverse=True)
            movie.cover = max_pic[0][1]
        except:
            movie.cover = cover_tag[0].get('src')
    body = html.xpath("//section[@class='article-body']")[0]
    title = body.xpath("div/p/text()")[0]
    title = title.replace(f"【{movie.dvdid}】", '')
    cite_url = body.xpath("div/cite/a/@href")[0]
    cite_url = cite_url.split('?aff=')[0]
    info = body.xpath("dl[@class='dltable']")[0]
    dt_txt_ls, dd_tags = info.xpath("dt/text()"), info.xpath("dd")
    data = {}
    for dt_txt, dd in zip(dt_txt_ls, dd_tags):
        a_tag = dd.xpath('a')
        if len(a_tag) == 0:
            dd_txt = dd.text
        else:
            dd_txt = a_tag[0].text
        data[dt_txt.strip()] = dd_txt.strip()

    ATTR_MAP = {'メーカー': 'producer', 'AV女優名': 'actress', 'メーカー品番': 'dvdid', 'シリーズ': 'serial', '配信開始日': 'publish_date'}
    for key, attr in ATTR_MAP.items():
        setattr(movie, attr, data.get(key))
    movie.title = title
    movie.uncensored = False    # 服务器在日本且面向日本国内公开发售，不会包含无码片


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)

    movie = MovieInfo('259LUXU-593')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
