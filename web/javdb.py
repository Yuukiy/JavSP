"""从JavDB抓取数据"""
import os
import re
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import *
from core.func import *
from core.config import cfg
from core.datatype import MovieInfo, GenreMap


logger = logging.getLogger(__name__)
genre_map = GenreMap('data/genre_javdb.csv')
permanent_url = 'https://javdb.com'
# javdb的永久地址上也套了CloudFlare的保护，因此即使启用了代理也不访问永久地址
base_url = cfg.ProxyFree.javdb


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # JavDB搜索番号时会有多个搜索结果，从中查找匹配番号的那个
    url = f'{base_url}/videos/search_autocomplete.json?q={movie.dvdid}'
    r = request_get(url).json()
    num_list = [i['number'].lower() for i in r]
    try:
        uid = r[num_list.index(movie.dvdid.lower())]['uid']
        new_url = f'{base_url}/v/{uid}'
    except ValueError:
        logger.debug(f'搜索结果中未找到目标影片({movie.dvdid}): ' + ', '.join(num_list))
        return

    html = get_html(new_url)
    container = html.xpath("/html/body/section/div[@class='container']")[0]
    info = container.xpath("div/div/div/nav")[0]
    title = container.xpath("h2/strong/text()")[0]
    cover = container.xpath("//img[@class='video-cover']/@src")[0]
    preview_pics = container.xpath("//a[@class='tile-item'][@data-fancybox='gallery']/@href")
    preview_video_tag = container.xpath("//video[@id='preview-video']/source/@src")
    if preview_video_tag:
        preview_video = preview_video_tag[0]
        if preview_video.startswith('//'):
            preview_video = 'https:' + preview_video
        movie.preview_video = preview_video
    dvdid = info.xpath("div/span")[0].text_content()
    publish_date = info.xpath("div/strong[text()='日期:']")[0].getnext().text
    duration = info.xpath("div/strong[text()='時長:']")[0].getnext().text.replace('分鍾', '').strip()
    director_tag = info.xpath("div/strong[text()='導演:']")
    if director_tag:
        movie.director = director_tag[0].getnext().text_content().strip()
    producer_tag = info.xpath("div/strong[text()='片商:']")
    if producer_tag:
        movie.producer = producer_tag[0].getnext().text_content().strip()
    publisher_tag = info.xpath("div/strong[text()='發行:']")
    if publisher_tag:
        movie.publisher = publisher_tag[0].getnext().text_content().strip()
    serial_tag = info.xpath("div/strong[text()='系列:']")
    if serial_tag:
        movie.serial = serial_tag[0].getnext().text
    score_tag = info.xpath("//span[@class='score-stars']")
    if score_tag:
        score_str = score_tag[0].tail
        score = re.search(r'([\d.]+)分', score_str).group(1)
        movie.score = "{:.2f}".format(float(score)*2)
    genre_tags = info.xpath("//strong[text()='類別:']/../span/a")
    genre, genre_id = [], []
    for tag in genre_tags:
        pre_id = tag.get('href').split('/')[-1]
        genre.append(tag.text)
        genre_id.append(pre_id)
        # 判定影片有码/无码
        subsite = pre_id.split('?')[0]
        movie.uncensored = {'uncensored': True, 'tags':False}.get(subsite)
    actress = info.xpath("//strong[text()='演員:']/../span/a/text()")
    magnet = container.xpath("//td[@class='magnet-name']/a/@href")

    movie.url = new_url.replace(base_url, permanent_url)
    movie.title = title.replace(dvdid, '').strip()
    movie.cover = cover
    movie.preview_pics = preview_pics
    movie.publish_date = publish_date
    movie.duration = duration
    movie.genre = genre
    movie.genre_id = genre_id
    movie.actress = actress
    movie.magnet = [i.replace('[javdb.com]','') for i in magnet]


def parse_clean_data(movie: MovieInfo):
    """解析指定番号的影片数据并进行清洗"""
    parse_data(movie)
    movie.genre_norm = genre_map.map(movie.genre_id)
    movie.genre_id = None   # 没有别的地方需要再用到，清空genre id（暗示已经完成转换）
    # 将此功能放在各个抓取器以保持数据的一致，避免影响转换（写入nfo时的信息来自多个抓取器的汇总，数据来源一致性不好）
    if cfg.Crawler.title__remove_actor:
        new_title = remove_trail_actor_in_title(movie.title, movie.actress)
        if new_title != movie.title:
            movie.ori_title = movie.title
            movie.title = new_title


if __name__ == "__main__":
    movie = MovieInfo('ION-020')
    parse_clean_data(movie)
    print(movie)
