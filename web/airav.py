"""从airav抓取数据"""
import os
import sys
import logging


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import *
from core.config import cfg
from core.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_url = 'https://www.airav.wiki'


def search_movie(dvdid):
    """通过搜索番号获取指定的影片的URL"""
    # 部分影片的URL并不能直接通过番号得出（如012717-360），因此需要尝试通过搜索来寻找影片
    page = 0
    count = 1
    result = []
    while len(result) < count:
        url = f'{base_url}/api/video/list?lang=zh-TW&lng=zh-TW&search={dvdid}&page={page}'
        r = request_get(url).json()
        # {"offset": 2460, "count": 12345, "result": [...], "status": "ok"}
        if r['result']:
            result.extend(r['result'])
            count = r['count']
            page += 1
        else: # 结果为空，结束循环
            break
    # 如果什么都没搜索到，直接返回
    if not result:
        return
    # 从所有搜索结果中选择最可能的番号，返回它的URL
    target = dvdid.replace('-', '_')
    for item in result:
        # {'vid': '', 'slug': '', 'name': '', 'url': '', 'view': '', 'img_url': '', 'barcode': ''}
        barcode = item['barcode'].replace('-', '_')
        if target in barcode:
            # 虽然有url字段但它是空的😂所以要通过barcode来生成链接
            url = f"{base_url}/video/{item['barcode']}"
            return url
    return


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # airav也提供简体，但是部分影片的简介只在繁体界面下有，因此抓取繁体页面的数据
    # 部分网页样式是通过js脚本生成的，调试和解析xpath时要根据未经脚本修改的原始网页来筛选元素
    url = new_url = f'{base_url}/video/{movie.dvdid}'
    html, resp = get_html(url, attach_raw=True)
    # url不存在时会被重定向至主页。history非空时说明发生了重定向
    if resp.history:
        new_url = search_movie(movie.dvdid)
        if new_url:
            html = get_html(new_url)
        else:
            logger.debug(f"'{movie.dvdid}': airav无资源")
            return
    container = html.xpath("//div[@class='min-h-500 row']")[0]
    cover = html.xpath("/html/head/meta[@property='og:image']/@content")[0]
    info = container.xpath("//div[@class='d-flex videoDataBlock']")[0]
    preview_pics = info.xpath("div[@class='mobileImgThumbnail']/a/@href")
    # airav部分资源也有预览片，但是预览片似乎是通过js获取的blob链接，无法通过静态网页解析来获取
    title = info.xpath("h5/text()")[0]
    dvdid = info.xpath("h5/text()")[1]
    # airav的genre是以搜索关键词的形式组织的，没有特定的genre_id
    genre = info.xpath("//div[@class='tagBtnMargin']/a/text()")
    actress = info.xpath("//li[@class='videoAvstarListItem']/a/text()")
    producer_tag = info.xpath("//li[text()='廠商']/a/text()")
    if producer_tag:
        movie.producer = producer_tag[0]
    publish_date = info.xpath("//li[text()='發片日期']/text()[last()]")[0]
    plot_tag = info.xpath("//div[@class='synopsis']/p/text()")
    if plot_tag:
        movie.plot = plot_tag[0]

    if cfg.Crawler.hardworking_mode:
        video_url = f'{base_url}/api/video/getVideoMedia?barcode={movie.dvdid}'
        resp = request_get(video_url).json()
        # 如果失败，结果如 {'msg': 'fail', 'status': 'fail'}
        if 'data' in resp:
            # 此外还有url_cdn, url_hlx, url_hls_cdn字段，后两者为m3u8格式。目前将url作为预览视频的地址
            movie.preview_video = resp['data'].get('url')

    movie.url = new_url
    movie.title = title
    movie.cover = cover
    movie.preview_pics = preview_pics
    movie.publish_date = publish_date
    movie.genre = genre
    movie.actress = actress
    # airav上部分影片会被标记为'馬賽克破壞版'，这些影片的title、plot和genre都不再准确
    if '馬賽克破壞版' in title or (movie.plot and '馬賽克破壞版' in movie.plot):
        movie.title = None
        movie.plot = None
        movie.genre = None


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    movie = MovieInfo('SKYHD-012')
    parse_data(movie)
    print(movie)
