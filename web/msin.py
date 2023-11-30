"""从db.msin.jp抓取数据"""
import os
import sys
import logging
import requests


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import *
from web.exceptions import *
from core.config import cfg
from core.lib import strftime_to_minutes
from core.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_url = 'https://db.msin.jp'
cookies = {'age': 'off'}


def normal_parser(movie: MovieInfo, html):
    container = html.xpath("//div[@id='center_main']")[0]
    info = container.xpath("div/div/div/div[@class='movie_info_ditail']")[0]
    avid = info.xpath("div[@class='mv_pn']/text()")[0]
    cid = info.xpath("div[@class='mv_fileName']/text()")[0]
    title = info.xpath("div[contains(@class, 'mv_title')]/text()")[0]
    cover_tag = container.xpath("//div[@class='movie_top']/img/@src")
    if cover_tag:
        movie.cover = cover_tag[0]
    genre = info.xpath("div[@class='mv_genre']/label/text()")
    actress, actress_pics = [], {}
    actress_tags = info.xpath("div[contains(text(),'出演者：')]/following-sibling::div[1]/div[@class='performer_box']")
    for tag in actress_tags:
        name = tag.xpath("div[@class='performer_text']/a/text()")[0]
        name = name.replace('（FC2動画）', '')
        pic_url = tag.xpath("div[@class='performer_image']/a/img/@src")[0]
        actress.append(name)
        actress_pics[name] = pic_url
    duration_tag = info.xpath("div[@class='mv_duration']/text()")
    if duration_tag:
        movie.duration = str(strftime_to_minutes(duration_tag[0]))
    publish_date_tag = info.xpath("a[@class='mv_createDate']/text()")
    if publish_date_tag:
        movie.publish_date = publish_date_tag[0]
    director_tag = info.xpath("//a[contains(@href, '/jp.page/director?')]/text()")
    if director_tag:
        movie.director = director_tag[0]
    serial_tag = info.xpath("a[@class='mv_series']/text()")
    if serial_tag:
        movie.serial = serial_tag[0]
    producer_tag = info.xpath("//a[@class='mv_mfr']/text()")
    if producer_tag:
        movie.producer = producer_tag[0]
    preview_pics = info.xpath("div[contains(@class, 'mv_com1')]/div/text()")
    if preview_pics:
        movie.preview_pics = [i for i in preview_pics if i.startswith('https://')]

    if cfg.Crawler.hardworking_mode and False:  # iframe嵌套太多了，目前用不到预览视频就先不解析了
        play_tag = container.xpath("//a[@class='playbutton popup']/@href")
        if play_tag:
            play_url = play_tag[0]
            r2 = request_get(play_url)
            TARGET_TXT = 'iframe.contentDocument.location.replace("'
            begin = r2.text.find(TARGET_TXT) + len(TARGET_TXT)
            end = r2.text.find('"', begin)
            iframe_url = r2.text[begin:end]
            iframe = get_html(iframe_url)

    movie.cid = cid
    movie.dvdid = avid
    movie.title = title.replace(avid, '').strip()
    movie.genre = [i.strip() for i in genre]
    movie.actress = actress
    movie.actress_pics = actress_pics
    movie.uncensored = False


def fc2_parser(movie: MovieInfo, html):
    container = html.xpath("//div[@id='top_content']")[0]
    info = container.xpath("div/div/div[@id='movie_info_ditail']")[0]
    avid = info.xpath("div[@class='mv_fileName']/text()")[0].upper()
    title = info.xpath("div[contains(@class, 'mv_title')]/text()")[0]
    # 部分影片有预览图，但是是跳转到FC2进行预览的，且预览地址是通过js脚本解析的（带有key）
    cover_tag = container.xpath("//div[@class='movie_top']/img/@src")
    if cover_tag:
        movie.cover = cover_tag[0]
    genre = info.xpath("div[@class='mv_tag']/label/text()")
    actress, actress_pics = [], {}
    actress_tags = info.xpath("div[contains(text(),'出演者：')]/following-sibling::div[1]/div[@class='performer_box']")
    for tag in actress_tags:
        name = tag.xpath("div[@class='performer_text']/a/text()")[0]
        name = name.replace('（FC2動画）', '')
        pic_url = tag.xpath("div[@class='performer_image']/a/img/@src")[0]
        actress.append(name)
        actress_pics[name] = pic_url
    duration_tag = info.xpath("div[@class='mv_duration']/text()")
    if duration_tag:
        movie.duration = str(strftime_to_minutes(duration_tag[0]))

    publish_date = info.xpath("a[@class='mv_createDate']/text()")
    if publish_date:
        movie.publish_date = publish_date[0]
    producer = info.xpath("a[@class='mv_writer']/text()")
    if producer:
        movie.producer = producer[0]

    movie.title = title.replace(avid, '').strip()
    movie.genre = [i.strip() for i in genre]
    movie.actress = actress
    movie.actress_pics = actress_pics


def parse_data(movie: MovieInfo):
    """从网页抓取并解析指定番号的数据
    Args:
        movie (MovieInfo): 要解析的影片信息，解析后的信息直接更新到此变量内
    """
    full_id = movie.dvdid
    if full_id.startswith('FC2-'):
        full_id = full_id.lower().replace('fc2-', 'fc2-ppv-')
        url = f"{base_url}/search/movie?str={full_id}"  # 海外：品番検索
    else:
        url = f"{base_url}/branch/search?sort=jp.movie&str={full_id}"   # 国内：品番検索
    r = request_get(url, cookies=cookies, delay_raise=True)
    # 404说明曾经有这部影片但是下架了，如果是200但网页内容是No Results说明是完全找不到影片
    if r.status_code == 404:
        raise MovieNotFoundError(__name__, movie.dvdid)
    html = resp2html(r)
    error_string = html.xpath("//div[@class='error_string']/text()")
    if error_string:
        if error_string[0].strip() == 'No Results':
            raise MovieNotFoundError(__name__, movie.dvdid)

    movie.url = r.url
    if full_id.startswith('fc2-'):
        fc2_parser(movie, html)
    else:
        normal_parser(movie, html)


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)

    movie = MovieInfo('hjmo00214')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
