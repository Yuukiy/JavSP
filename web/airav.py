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


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # airav也提供简体，但是部分影片的简介只在繁体界面下有，因此抓取繁体页面的数据
    html = get_html(f'{base_url}/video/{movie.dvdid}')
    # airav的部分网页样式是通过js脚本生成的，调试和解析xpath时要根据未经脚本修改的原始网页来筛选元素
    if html.xpath("/html/head/title") == 'AIRAV-WIKI':
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
    plot = info.xpath("//div[@class='synopsis']/p/text()")[0]

    if cfg.Crawler.hardworking_mode:
        video_url = f'{base_url}/api/video/getVideoMedia?barcode={movie.dvdid}'
        resp = request_get(video_url).json()
        # 如果失败，结果如 {'msg': 'fail', 'status': 'fail'}
        if 'data' in resp:
            # 此外还有url_cdn, url_hlx, url_hls_cdn字段，后两者为m3u8格式。目前将url作为预览视频的地址
            movie.preview_video = resp['data'].get('url')

    movie.title = title
    movie.cover = cover
    movie.preview_pics = preview_pics
    movie.publish_date = publish_date
    movie.genre = genre
    movie.actress = actress
    movie.plot = plot
    # airav上部分影片会被标记为'馬賽克破壞版'，这些影片的title、plot和genre都不再准确
    if '馬賽克破壞版' in title or '馬賽克破壞版' in plot:
        movie.title = None
        movie.plot = None
        movie.genre = None


if __name__ == "__main__":
    movie = MovieInfo('IPX-177')
    parse_data(movie)
    print(movie)