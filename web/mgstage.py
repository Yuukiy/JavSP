"""从蚊香社-mgstage抓取数据"""
import os
import re
import sys
import logging


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import Request, resp2html
from web.exceptions import *
from core.config import cfg
from core.datatype import MovieInfo


logger = logging.getLogger(__name__)
base_url = 'https://www.mgstage.com'
# 初始化Request实例（要求携带已通过R18认证的cookies，否则会被重定向到认证页面）
request = Request()
request.cookies = {'adc': '1'}


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    url = f'{base_url}/product/product_detail/{movie.dvdid}/'
    resp = request.get(url, delay_raise=True)
    if resp.status_code == 403:
        raise SiteBlocked('mgstage不允许从当前IP所在地区访问，请尝试更换为日本地区代理')
    # url不存在时会被重定向至主页。history非空时说明发生了重定向
    elif resp.history:
        raise MovieNotFoundError(__name__, movie.dvdid)

    html = resp2html(resp)
    # mgstage的文本中含有大量的空白字符（'\n \t'），需要使用strip去除
    title = html.xpath("//div[@class='common_detail_cover']/h1/text()")[0].strip()
    container = html.xpath("//div[@class='detail_left']")[0]
    cover = container.xpath("//a[@id='EnlargeImage']/@href")[0]
    # 有链接的女优和仅有文本的女优匹配方法不同，因此分别匹配以后合并列表
    actress_text = container.xpath("//th[text()='出演：']/following-sibling::td/text()")
    actress_link = container.xpath("//th[text()='出演：']/following-sibling::td/a/text()")
    actress = [i.strip() for i in actress_text + actress_link]
    actress = [i for i in actress if i]     # 移除空字符串
    producer = container.xpath("//th[text()='メーカー：']/following-sibling::td/a/text()")[0].strip()
    duration_str = container.xpath("//th[text()='収録時間：']/following-sibling::td/text()")[0]
    match = re.search(r'\d+', duration_str)
    if match:
        movie.duration = match.group(0)
    dvdid = container.xpath("//th[text()='品番：']/following-sibling::td/text()")[0]
    date_str = container.xpath("//th[text()='配信開始日：']/following-sibling::td/text()")[0]
    publish_date = date_str.replace('/', '-')
    serial_tag = container.xpath("//th[text()='シリーズ：']/following-sibling::td/a/text()")
    if serial_tag:
        movie.serial = serial_tag[0].strip()
    # label: 大意是某个系列策划用同样的番号，例如ABS打头的番号label是'ABSOLUTELY PERFECT'，暂时用不到
    # label = container.xpath("//th[text()='レーベル：']/following-sibling::td/text()")[0].strip()
    genre_tags = container.xpath("//th[text()='ジャンル：']/following-sibling::td/a")
    genre = [i.text.strip() for i in genre_tags]
    score_str = container.xpath("//td[@class='review']/span")[0].tail.strip()
    match = re.search(r'^[\.\d]+', score_str)
    if match:
        score = float(match.group()) * 2
        movie.score = f'{score:.2f}'
    # plot可能含有嵌套格式，为了保留plot中的换行关系，手动处理plot中的各个标签
    plots = []
    plot_p_tags = container.xpath("//dl[@id='introduction']/dd/p[not(@class='more')]")
    for p in plot_p_tags:
        children = p.getchildren()
        # 没有children时表明plot不含有格式，此时简单地提取文本就可以
        if not children:
            plots.append(p.text_content())
            continue
        for child in children:
            if child.tag == 'br' and plots[-1] != '\n':
                plots.append('\n')
            else:
                if child.text:
                    plots.append(child.text)
                if child.tail:
                    plots.append(child.tail)
    plot = ''.join(plots).strip()
    preview_pics = container.xpath("//a[@class='sample_image']/@href")

    if cfg.Crawler.hardworking_mode:
        # 预览视频是点击按钮后再加载的，不在静态网页中
        btn_url = container.xpath("//a[@class='button_sample']/@href")[0]
        video_pid = btn_url.split('/')[-1]
        req_url = f'{base_url}/sampleplayer/sampleRespons.php?pid={video_pid}'
        resp = request.get(req_url).json()
        video_url = resp.get('url')
        if video_url:
            # /sample/shirouto/siro/3093/SIRO-3093_sample.ism/request?uid=XXX&amp;pid=XXX
            preview_video = video_url.split('.ism/')[0] + '.mp4'
            movie.preview_video = preview_video

    movie.dvdid = dvdid
    movie.url = url
    movie.title = title
    movie.cover = cover
    movie.actress = actress
    movie.producer = producer
    movie.publish_date = publish_date
    movie.genre = genre
    movie.plot = plot
    movie.preview_pics = preview_pics
    movie.uncensored = False    # 服务器在日本且面向日本国内公开发售，不会包含无码片


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('HRV-045')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
