"""从fanza抓取数据"""
import os
import re
import sys
import json
import logging


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import Request, resp2html
from web.exceptions import *
from core.config import cfg
from core.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_url = 'https://www.dmm.co.jp'
# 初始化Request实例（要求携带已通过R18认证的cookies，否则会被重定向到认证页面）
request = Request()
request.cookies = {'age_check_done': '1'}
request.headers['Accept-Language'] = 'ja,en-US;q=0.9'


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    url = f'{base_url}/digital/videoa/-/detail/=/cid={movie.cid}/'
    resp = request.get(url, delay_raise=True)
    # 404错误表明没有这部影片的数据
    if resp.status_code == 404:
        raise MovieNotFoundError(__name__, movie.cid)
    resp.raise_for_status()
    html = resp2html(resp)
    if 'not available in your region' in html.text_content():
        raise SiteBlocked('FANZA不允许从当前IP所在地区访问，请检查你的网络和代理服务器设置')

    title = html.xpath("//h1[@id='title']/text()")[0]
    # 注意: 浏览器在渲染时会自动加上了'tbody'字段，但是原始html网页中并没有，因此xpath解析时还是要按原始网页的来
    container = html.xpath("//table[@class='mg-b12']/tr/td")[0]
    cover = container.xpath("//div[@id='sample-video']/a/@href")[0]
    # 采用'配信開始日'作为发布日期: https://www.zhihu.com/question/57513172/answer/153219083
    date_str = container.xpath("//td[text()='配信開始日：']/following-sibling::td/text()")[0].strip()
    publish_date = date_str.replace('/', '-')
    duration_str = container.xpath("//td[text()='収録時間：']/following-sibling::td/text()")[0].strip()
    match = re.search(r'\d+', duration_str)
    if match:
        movie.duration = match.group(0)
    # 女优、导演、系列：字段不存在时，匹配将得到空列表。暂未发现有名字不显示在a标签中的情况
    actress = container.xpath("//span[@id='performer']/a/text()")
    director_tag = container.xpath("//td[text()='監督：']/following-sibling::td/a/text()")
    if director_tag:
        movie.director = director_tag[0].strip()
    serial_tag = container.xpath("//td[text()='シリーズ：']/following-sibling::td/a/text()")
    if serial_tag:
        movie.serial = serial_tag[0].strip()
    producer_tag = container.xpath("//td[text()='メーカー：']/following-sibling::td/a/text()")
    if producer_tag:
        movie.producer = producer_tag[0].strip()
    # label: 大意是某个系列策划用同样的番号，例如ABS打头的番号label是'ABSOLUTELY PERFECT'，暂时用不到
    # label_tag = container.xpath("//td[text()='レーベル：']/following-sibling::td/a/text()")
    # if label_tag:
    #     label = label_tag[0].strip()
    # fanza会把促销信息也写进genre……因此要根据tag指向的链接类型进行筛选
    genre_tags = container.xpath("//td[text()='ジャンル：']/following-sibling::td/a[contains(@href,'article=keyword')]")
    genre, genre_id = [], []
    for tag in genre_tags:
        genre.append(tag.text.strip())
        genre_id.append(tag.get('href').split('=')[-1].strip('/'))
    cid = container.xpath("//td[text()='品番：']/following-sibling::td/text()")[0].strip()
    plot = container.xpath("//div[@class='mg-b20 lh4']/text()")[0].strip()
    preview_pics = container.xpath("//a[@name='sample-image']/img/@src")
    score_str = container.xpath("//p[@class='d-review__average']/strong/text()")[0].strip()
    match = re.search(r'\d+', score_str)
    if match:
        score = float(match.group()) * 2
        movie.score = f'{score:.2f}'
    
    if cfg.Crawler.hardworking_mode:
        # 预览视频是动态加载的，不在静态网页中
        video_url = f'{base_url}/service/digitalapi/-/html5_player/=/cid={movie.cid}'
        html2 = request.get_html(video_url)
        # 目前用到js脚本的地方不多，所以不使用专门的js求值模块，先用正则提取文本然后用json解析数据
        script = html2.xpath("//script[contains(text(),'getElementById(\"dmmplayer\")')]/text()")[0].strip()
        match = re.search(r'\{.*\}', script)
        # 主要是为了捕捉json.loads的异常，但是也借助try-except判断是否正则表达式是否匹配
        try:
            data = json.loads(match.group())
            video_url = data.get('src')
            if video_url and video_url.startswith('//'):
                video_url = 'https:' + video_url
            movie.preview_video = video_url
        except Exception as e:
            logger.debug('解析视频地址时异常: ' + repr(e))

    movie.cid = cid
    movie.url = url
    movie.title = title
    movie.cover = cover
    movie.publish_date = publish_date
    movie.actress = actress
    movie.genre = genre
    movie.genre_id = genre_id
    movie.plot = plot
    movie.preview_pics = preview_pics
    movie.uncensored = False    # 服务器在日本且面向日本国内公开发售，不会包含无码片


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo(cid='sqte00300')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
