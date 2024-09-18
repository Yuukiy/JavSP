"""从fanza抓取数据"""
import os
import re
import sys
import json
import logging
from typing import Dict, List, Tuple


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


_PRODUCT_PRIORITY = {'digital': 10, 'mono': 5, 'monthly': 2, 'rental': 1}
_TYPE_PRIORITY = {'videoa': 10, 'anime': 8, 'nikkatsu': 6, 'doujin': 4, 'dvd': 3, 'ppr': 2, 'paradisetv': 1}
def sort_search_result(result: List[Dict]):
    """排序搜索结果"""
    scores = {i['url']:(_PRODUCT_PRIORITY.get(i['product'], 0), _TYPE_PRIORITY.get(i['type'], 0)) for i in result}
    sorted_result = sorted(result, key=lambda x:scores[x['url']], reverse=True)
    return sorted_result


def get_urls_of_cid(cid: str) -> Tuple[str, str]:
    """搜索cid可能的影片URL"""
    r = request.get(f"https://www.dmm.co.jp/search/?redirect=1&enc=UTF-8&category=&searchstr={cid}&commit.x=0&commit.y=0")
    if r.status_code == 404:
        raise MovieNotFoundError(__name__, cid)
    r.raise_for_status()
    html = resp2html_wrapper(r)
    result = html.xpath("//ul[@id='list']/li/div/p/a/@href")
    parsed_result = {}
    for url in result:
        items = url.split('/')
        type_, cid = None, None
        for i, part in enumerate(items):
            if part == '-':
                product, type_ = items[i-2], items[i-1]
            elif part.startswith('cid='):
                cid = part[4:]
                new_url = '/'.join(i for i in items if not i.startswith('?')) + '/'
                parsed_result.setdefault(cid, []).append({'product': product, 'type': type_, 'url': new_url})
                break
    if cid not in parsed_result:
        if len(result) > 0:
            logger.debug(f"Unknown URL in search result: " + ', '.join(result))
        raise MovieNotFoundError(__name__, cid)
    sorted_result = sort_search_result(parsed_result[cid])
    return sorted_result


def resp2html_wrapper(resp):
    html = resp2html(resp)
    if 'not available in your region' in html.text_content():
        raise SiteBlocked('FANZA不允许从当前IP所在地区访问，请检查你的网络和代理服务器设置')
    elif '/login/' in resp.url:
        raise SiteBlocked('FANZA要求当前IP登录账号才可访问，请尝试更换为日本IP')
    return html


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    default_url = f'{base_url}/digital/videoa/-/detail/=/cid={movie.cid}/'
    r0 = request.get(default_url, delay_raise=True)
    if r0.status_code == 404:
        urls = get_urls_of_cid(movie.cid)
        for d in urls:
            func_name = f"parse_{d['type']}_page"
            if func_name in globals():
                parse_func = globals()[func_name]
            else:
                logger.debug(f"不知道怎么解析 fanza {d['type']} 的页面: {d['url']}")
                continue
            r = request.get(d['url'])
            html = resp2html_wrapper(r)
            try:
                parse_func(movie, html)
                movie.url = d['url']
                break
            except:
                logger.debug(f"Fail to parse {d['url']}", exc_info=True)
                if d is urls[-1]:
                    logger.warning(f"在fanza查找到的cid={movie.cid}的影片页面均解析失败")
                    raise
    else:
        html = resp2html_wrapper(r0)
        parse_videoa_page(movie, html)
        movie.url = default_url


def parse_videoa_page(movie: MovieInfo, html):
    """解析AV影片的页面布局"""
    title = html.xpath("//div[@class='hreview']/h1/text()")[0]
    # 注意: 浏览器在渲染时会自动加上了'tbody'字段，但是原始html网页中并没有，因此xpath解析时还是要按原始网页的来
    container = html.xpath("//table[@class='mg-b12']/tr/td")[0]
    cover = container.xpath("//div[@id='sample-video']/a/@href")[0]
    # 采用'配信開始日'作为发布日期: https://www.zhihu.com/question/57513172/answer/153219083
    date_tag = container.xpath("//td[text()='配信開始日：']/following-sibling::td/text()")
    if date_tag:
        movie.publish_date = date_tag[0].strip().replace('/', '-')
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
    genre_tags = container.xpath("//td[text()='ジャンル：']/following-sibling::td/a[contains(@href,'?keyword=') or contains(@href,'article=keyword')]")
    genre, genre_id = [], []
    for tag in genre_tags:
        genre.append(tag.text.strip())
        genre_id.append(tag.get('href').split('=')[-1].strip('/'))
    cid = container.xpath("//td[text()='品番：']/following-sibling::td/text()")[0].strip()
    plot = container.xpath("//div[contains(@class, 'mg-b20 lh4')]/text()")[0].strip()
    preview_pics = container.xpath("//a[@name='sample-image']/img/@src")
    score_tag = container.xpath("//p[@class='d-review__average']/strong/text()")
    if score_tag:
        match = re.search(r'\d+', score_tag[0].strip())
        if match:
            score = float(match.group()) * 2
            movie.score = f'{score:.2f}'
    else:
        score_img = container.xpath("//td[text()='平均評価：']/following-sibling::td/img/@src")[0]
        movie.score = int(score_img.split('/')[-1].split('.')[0]) # 00, 05 ... 50
    
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
    movie.title = title
    movie.cover = cover
    movie.actress = actress
    movie.genre = genre
    movie.genre_id = genre_id
    movie.plot = plot
    movie.preview_pics = preview_pics
    movie.uncensored = False    # 服务器在日本且面向日本国内公开发售，不会包含无码片


def parse_anime_page(movie: MovieInfo, html):
    """解析动画影片的页面布局"""
    title = html.xpath("//h1[@id='title']/text()")[0]
    container = html.xpath("//table[@class='mg-b12']/tr/td")[0]
    cover = container.xpath("//img[@name='package-image']/@src")[0]
    date_str = container.xpath("//td[text()='発売日：']/following-sibling::td/text()")[0].strip()
    publish_date = date_str.replace('/', '-')
    duration_tag = container.xpath("//td[text()='収録時間：']/following-sibling::td/text()")
    if duration_tag:
        movie.duration = duration_tag[0].strip().replace('分', '')
    serial_tag = container.xpath("//td[text()='シリーズ：']/following-sibling::td/a/text()")
    if serial_tag:
        movie.serial = serial_tag[0].strip()
    producer_tag = container.xpath("//td[text()='メーカー：']/following-sibling::td/a/text()")
    if producer_tag:
        movie.producer = producer_tag[0].strip()
    genre_tags = container.xpath("//td[text()='ジャンル：']/following-sibling::td/a[contains(@href,'article=keyword')]")
    genre, genre_id = [], []
    for tag in genre_tags:
        genre.append(tag.text.strip())
        genre_id.append(tag.get('href').split('=')[-1].strip('/'))
    cid = container.xpath("//td[text()='品番：']/following-sibling::td/text()")[0].strip()
    plot = container.xpath("//div[@class='mg-b20 lh4']/p")[0].text_content().strip()
    preview_pics = container.xpath("//a[@name='sample-image']/img/@data-lazy")
    score_img = container.xpath("//td[text()='平均評価：']/following-sibling::td/img/@src")[0]
    score = int(score_img.split('/')[-1].split('.')[0]) # 00, 05 ... 50

    movie.cid = cid
    movie.title = title
    movie.cover = cover
    movie.publish_date = publish_date
    movie.genre = genre
    movie.genre_id = genre_id
    movie.plot = plot
    movie.score = f'{score/5:.2f}'  # 转换为10分制
    movie.preview_pics = preview_pics
    movie.uncensored = False    # 服务器在日本且面向日本国内公开发售，不会包含无码片


# parse_dvd_page = parse_videoa_page    # 118wtktabf067
parse_ppr_page = parse_videoa_page
parse_nikkatsu_page = parse_videoa_page
parse_doujin_page = parse_anime_page


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo(cid='d_aisoft3356')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
