"""从jav321抓取数据"""
import os
import re
import sys
import logging


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import post_html
from core.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_url = 'https://www.jav321.com'


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    html = post_html(f'{base_url}/search', data={'sn': movie.dvdid})
    page_url = html.xpath("//ul[@class='dropdown-menu']/li/a/@href")[0]
    cid = page_url.split('/')[-1]   # /video/ipx00177
    # 如果从URL匹配到的cid是'search'，说明还停留在搜索页面，找不到这部影片
    if cid == 'search':
        return
    title = html.xpath("//div[@class='panel-heading']/h3/text()")[0]
    info = html.xpath("//div[@class='col-md-9']")[0]
    # jav321的不同信息字段间没有明显分隔，只能通过url来匹配目标标签
    producer = info.xpath("a[contains(@href,'/company/')]/text()")[0]
    # actress, actress_pics
    actress, actress_pics = [], {}
    actress_tags = html.xpath("//div[@class='thumbnail']/a[contains(@href,'/star/')]/img")
    for tag in actress_tags:
        name = tag.tail.strip()
        pic_url = tag.get('src')
        actress.append(name)
        # jav321的女优头像完全是应付了事：即使女优实际没有头像，也会有一个看起来像模像样的url，
        # 因而无法通过url判断女优头像图片是否有效。有其他选择时最好不要使用jav321的女优头像数据
        actress_pics[name] = pic_url
    # genre, genre_id
    genre_tags = info.xpath("a[contains(@href,'/genre/')]")
    genre, genre_id = [], []
    for tag in genre_tags:
        genre.append(tag.text)
        genre_id.append(tag.get('href').split('/')[-2]) # genre/4025/1
    dvdid = info.xpath("b[text()='品番']")[0].tail.replace(': ', '').upper()
    publish_date = info.xpath("b[text()='配信開始日']")[0].tail.replace(': ', '')
    duration_str = info.xpath("b[text()='収録時間']")[0].tail
    match = re.search(r'\d+', duration_str)
    if match:
        movie.duration = match.group(0)
    # 仅部分影片有评分且评分只能粗略到星级而没有分数，要通过星级的图片来判断，如'/img/35.gif'表示3.5星
    score_tag = info.xpath("//b[text()='平均評価']/following-sibling::img/@data-original")
    if score_tag:
        score = int(score_tag[0][5:7])/5   # /10*2
        movie.score = score
    serial_tag = info.xpath("a[contains(@href,'/series/')]/text()")
    if serial_tag:
        movie.serial = serial_tag[0]
    preview_video_tag = info.xpath("//video/source/@src")
    if preview_video_tag:
        movie.preview_video = preview_video_tag[0]

    plot = info.xpath("//div[@class='panel-body']/div[@class='row']/div[@class='col-md-12']/text()")[0]
    preview_pics = html.xpath("//div[@class='col-xs-12 col-md-12']/p/a/img[@class='img-responsive']/@src")
    # 磁力和ed2k链接是依赖js脚本加载的，无法通过静态网页来解析

    movie.url = page_url
    movie.cid = cid
    movie.title = title
    movie.actress = actress
    movie.actress_pics = actress_pics
    movie.producer = producer
    movie.genre = genre
    movie.genre_id = genre_id
    movie.publish_date = publish_date
    # preview_pics的第一张图始终是封面，剩下的才是预览图
    movie.cover = preview_pics[0]
    movie.preview_pics = preview_pics[1:]
    movie.plot = plot


if __name__ == "__main__":
    movie = MovieInfo('IPX-177')
    parse_data(movie)
    print(movie)
