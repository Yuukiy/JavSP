"""从airav抓取数据"""
import re
import logging
from html import unescape


from javsp.web.base import Request
from javsp.web.exceptions import *
from javsp.core.config import cfg
from javsp.core.datatype import MovieInfo

# 初始化Request实例
request = Request(use_scraper=True)
request.headers['Accept-Language'] = 'zh-TW,zh;q=0.9'
# 近期airav服务器似乎不稳定，时好时坏，单次查询平均在17秒左右，timeout时间增加到20秒
request.timeout = 20


logger = logging.getLogger(__name__)
base_url = 'https://www.airav.wiki'


def search_movie(dvdid):
    """通过搜索番号获取指定的影片在网站上的ID"""
    # 部分影片的ID并不直接等于番号（如012717-360），此时需要尝试通过搜索来寻找影片
    page = 0
    count = 1
    result = []
    while len(result) < count:
        url = f'{base_url}/api/video/list?lang=zh-TW&lng=zh-TW&search={dvdid}&page={page}'
        r = request.get(url).json()
        # {"offset": 2460, "count": 12345, "result": [...], "status": "ok"}
        if r['result']:
            result.extend(r['result'])
            count = r['count']
            page += 1
        else: # 结果为空，结束循环
            break
    # 如果什么都没搜索到，直接返回
    if not result:
        raise MovieNotFoundError(__name__, dvdid)
    # 排序，以优先选择更符合预期的结果（如'012717_472'对应的'1pondo_012717_472'和'_1pondo_012717_472'）
    result.sort(key=lambda x:x['barcode'])
    # 从所有搜索结果中选择最可能的番号，返回它的URL
    target = dvdid.replace('-', '_')
    for item in result:
        # {'vid': '', 'slug': '', 'name': '', 'url': '', 'view': '', 'img_url': '', 'barcode': ''}
        barcode = item['barcode'].replace('-', '_')
        if target in barcode:
            return item['barcode']
    raise MovieNotFoundError(__name__, dvdid, result)


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # airav也提供简体，但是为了尽量保持女优名等与其他站点一致，抓取繁体的数据
    url = f'{base_url}/api/video/barcode/{movie.dvdid}?lng=zh-TW'
    resp = request.get(url).json()
    # 只在番号是纯数字时，尝试进行搜索，否则可能导致搜索到错误的影片信息
    if resp['count'] == 0 and re.match(r'\d{6}[-_]\d{2,3}', movie.dvdid):
        barcode = search_movie(movie.dvdid)
        if barcode:
            url = f'{base_url}/api/video/barcode/{barcode}?lng=zh-TW'
            resp = request.get(url).json()
    if resp['count'] == 0:
        raise MovieNotFoundError(__name__, movie.dvdid, resp)

    # 从API返回的数据中提取需要的字段
    # TODO: 数据中含有更多信息（如女优的中文&日文名对照），可能有助于未来功能扩展
    data = resp['result']
    dvdid = data['barcode']
    movie.dvdid = dvdid
    movie.url = base_url + '/video/' + dvdid
    # plot和title中可能含有HTML的转义字符，需要进行解转义处理
    movie.plot = unescape(data['description']) or None
    movie.cover = data['img_url']
    # airav的genre是以搜索关键词的形式组织的，没有特定的genre_id
    movie.genre = [i['name'] for i in data['tags']]
    movie.title = unescape(data['name'])
    movie.actress = [i['name'] for i in data['actors']]
    movie.publish_date = data['publish_date']
    movie.preview_pics = data['images'] or []
    if data['factories']:
        movie.producer = data['factories'][0]['name']

    if cfg.Crawler.hardworking_mode:
        # 注意这里用的是获取的dvdid，而不是传入的movie.dvdid（如'1pondo_012717_472'与'012717_472'）
        video_url = f"{base_url}/api/video/getVideoMedia?barcode={dvdid}&vid={data['vid']}"
        resp = request.get(video_url).json()
        # 如果失败，结果如 {'msg': 'fail', 'status': 'fail'}
        if 'data' in resp:
            # 除url外还有url_cdn, url_hlx, url_hls_cdn字段，后两者为m3u8格式。目前将url作为预览视频的地址
            # TODO: 发现部分影片（如080719-976）的传统格式预览片错误
            movie.preview_video = resp['data'].get('url')

    # airav上部分影片会被标记为'馬賽克破壞版'等，这些影片的title、plot和genre都不再准确
    for keyword in ('馬賽克破壞版', '馬賽克破解版', '無碼流出版'):
        if movie.title and keyword in movie.title:
            movie.title = None
            movie.genre = []
        if movie.plot and keyword in movie.plot:
            movie.plot = None
            movie.genre = []
        if not any([movie.title, movie.plot, movie.genre]):
            break


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('DSAD-938')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
