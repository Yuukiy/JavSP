"""从JavDB抓取数据"""
import os
import re
import logging
from urllib.parse import urljoin

import lxml.html
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from javsp.web.base import Request
from javsp.web.exceptions import *
from javsp.func import *
from javsp.avid import guess_av_type
from javsp.config import Cfg, CrawlerID
from javsp.datatype import MovieInfo, GenreMap


logger = logging.getLogger(__name__)
genre_map = GenreMap('data/genre_javdb.csv')
permanent_url = 'https://javdb.com'
# JavDB 官方域名按版权要求屏蔽日本地区IP，而常见代理出口恰好位于日本，
# 导致"配置代理反而403"。优先使用免代理镜像（config: network.proxy_free.javdb，
# 可直连且不受地区限制）；未配置镜像时回退官方域名+代理
_mirror = Cfg().network.proxy_free.get('javdb') if Cfg().network.proxy_free else None
base_url = str(_mirror) if _mirror else permanent_url

request = Request()
request.headers['Accept-Language'] = 'zh-CN,zh;q=0.9,zh-TW;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5'

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
)


def _get_proxy_settings():
    # javdb575 为国内可直连镜像，访问它不需要代理
    if base_url != permanent_url:
        return None
    proxy_url = Cfg().network.proxy_server
    if proxy_url is None:
        return None
    server = str(proxy_url)
    # Playwright 不支持 socks5h，统一降级为 socks5 交给浏览器处理。
    if server.startswith('socks5h://'):
        server = 'socks5://' + server[len('socks5h://'):]
    return {'server': server}


def _wait_for_content(page, selectors=()):
    for selector in selectors:
        try:
            page.wait_for_selector(selector, timeout=15000)
            return
        except PlaywrightTimeoutError:
            continue


def _check_page_state(url, page):
    title = page.title()
    content = page.content()
    current_url = page.url

    if '/login' in current_url:
        raise CredentialError('JavDB: 当前页面被重定向到登录页，暂未接入登录态')
    if current_url.rstrip('/').endswith('/pay'):
        raise SitePermissionError(f"JavDB: 此资源被限制为仅VIP可见: '{url}'")
    if 'Attention Required! | Cloudflare' in title or 'cf-error-code' in content:
        raise SiteBlocked(f'JavDB: Cloudflare 拦截: {url}')
    if 'Just a moment...' in title:
        raise SiteBlocked(f'JavDB: Cloudflare 验证页: {url}')
    return content, current_url


def _page_to_html(url, page):
    content, current_url = _check_page_state(url, page)
    html = lxml.html.fromstring(content)
    html.make_links_absolute(current_url, resolve_base_href=True)
    return html, current_url


def get_html_wrapper(url, page, selectors=()):
    """使用 Playwright 打开页面并返回可 xpath 的 html"""
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
    except PlaywrightTimeoutError:
        logger.debug(f'JavDB: 页面加载超时，尝试继续解析已加载内容: {url}')
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except PlaywrightTimeoutError:
        pass
    _wait_for_content(page, selectors)
    page.wait_for_timeout(1200)
    return _page_to_html(url, page)


def _partial_parse_from_search(movie: MovieInfo, html, index, detail_url):
    box = html.xpath("//a[@class='box']")[index]
    movie.url = detail_url
    movie.title = box.get('title')
    cover = box.xpath("div/img/@src")
    if cover:
        movie.cover = cover[0]
    score_tag = box.xpath("div[@class='score']/span/span")
    if score_tag and score_tag[0].tail:
        score_match = re.search(r'([\d.]+)分', score_tag[0].tail)
        if score_match:
            movie.score = "{:.2f}".format(float(score_match.group(1)) * 2)
    publish_date = box.xpath("div[@class='meta']/text()")
    if publish_date:
        movie.publish_date = publish_date[0].strip()


def parse_data(movie: MovieInfo):
    """从网页抓取并解析指定番号的数据
    Args:
        movie (MovieInfo): 要解析的影片信息，解析后的信息直接更新到此变量内
    """
    search_url = f'{base_url}/search?q={movie.dvdid}&f=all'

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy=_get_proxy_settings(),
            args=['--disable-blink-features=AutomationControlled'],
        )
        context = browser.new_context(
            locale='zh-CN',
            user_agent=USER_AGENT,
            viewport={'width': 1440, 'height': 2400},
            java_script_enabled=True,
        )
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = window.chrome || { runtime: {} };
            """
        )
        page = context.new_page()
        try:
            # JavDB搜索番号时会有多个搜索结果，从中查找匹配番号的那个
            html, _ = get_html_wrapper(search_url, page, selectors=("a.box", "div.video-title"))
            ids = list(map(str.lower, html.xpath("//div[@class='video-title']/strong/text()")))
            movie_urls = html.xpath("//a[@class='box']/@href")
            match_count = len([i for i in ids if i == movie.dvdid.lower()])
            if match_count == 0:
                raise MovieNotFoundError(__name__, movie.dvdid, ids)
            if match_count > 1:
                raise MovieDuplicateError(__name__, movie.dvdid, match_count)

            index = ids.index(movie.dvdid.lower())
            detail_url = movie_urls[index]
            if detail_url.startswith('/'):
                detail_url = urljoin(permanent_url, detail_url)

            try:
                html2, actual_url = get_html_wrapper(
                    detail_url,
                    page,
                    selectors=("img.video-cover", "nav.panel.movie-panel-info"),
                )
            except (SitePermissionError, CredentialError):
                _partial_parse_from_search(movie, html, index, detail_url)
                return

            container = html2.xpath("/html/body/section/div/div[@class='video-detail']")[0]
            info = container.xpath("//nav[@class='panel movie-panel-info']")[0]
            title = container.xpath("h2/strong[@class='current-title']/text()")[0]
            show_orig_title = container.xpath(
                "//a[contains(@class, 'meta-link') and not(contains(@style, 'display: none'))]"
            )
            if show_orig_title:
                ori_title = container.xpath("h2/span[@class='origin-title']/text()")
                if ori_title:
                    movie.ori_title = ori_title[0]
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
            av_type = guess_av_type(movie.dvdid)
            if av_type != 'fc2':
                producer_tag = info.xpath("div/strong[text()='片商:']")
            else:
                producer_tag = info.xpath("div/strong[text()='賣家:']")
            if producer_tag:
                movie.producer = producer_tag[0].getnext().text_content().strip()
            publisher_tag = info.xpath("div/strong[text()='發行:']")
            if publisher_tag:
                movie.publisher = publisher_tag[0].getnext().text_content().strip()
            serial_tag = info.xpath("div/strong[text()='系列:']")
            if serial_tag:
                movie.serial = serial_tag[0].getnext().text_content().strip()
            score_tag = info.xpath("//span[@class='score-stars']")
            if score_tag and score_tag[0].tail:
                score = re.search(r'([\d.]+)分', score_tag[0].tail).group(1)
                movie.score = "{:.2f}".format(float(score) * 2)
            genre_tags = info.xpath("//strong[text()='類別:']/../span/a")
            genre, genre_id = [], []
            for tag in genre_tags:
                pre_id = tag.get('href').split('/')[-1]
                genre.append(tag.text)
                genre_id.append(pre_id)
                # 判定影片有码/无码
                subsite = pre_id.split('?')[0]
                movie.uncensored = {'uncensored': True, 'tags': False}.get(subsite)
            actors_tag = info.xpath("//strong[text()='演員:']/../span")
            actress = []
            if actors_tag:
                all_actors = actors_tag[0].xpath("a/text()")
                genders = actors_tag[0].xpath("strong/text()")
                actress = [i for i in all_actors if all_actors.index(i) < len(genders) and genders[all_actors.index(i)] == '♀']
            magnet = container.xpath("//div[@class='magnet-name column is-four-fifths']/a/@href")

            movie.dvdid = dvdid
            movie.url = actual_url.replace(base_url, permanent_url)
            movie.title = title.replace(dvdid, '').strip()
            movie.cover = cover
            movie.preview_pics = preview_pics
            movie.publish_date = publish_date
            movie.duration = duration
            movie.genre = genre
            movie.genre_id = genre_id
            movie.actress = actress
            movie.magnet = [i.replace('[javdb.com]', '') for i in magnet]
        finally:
            context.close()
            browser.close()


def parse_clean_data(movie: MovieInfo):
    """解析指定番号的影片数据并进行清洗"""
    try:
        parse_data(movie)
        # 检查封面URL是否真的存在对应图片
        if movie.cover is not None:
            r = request.head(movie.cover)
            if r.status_code != 200:
                movie.cover = None
    except SiteBlocked:
        raise
        logger.error('JavDB: 可能触发了反爬虫机制，请稍后再试')
    if movie.genre_id and (not movie.genre_id[0].startswith('fc2?')):
        movie.genre_norm = genre_map.map(movie.genre_id)
        movie.genre_id = None   # 没有别的地方需要再用到，清空genre id（表明已经完成转换）


def collect_actress_alias(type=0, use_original=True):
    """
    收集女优的别名
    type: 0-有码, 1-无码, 2-欧美
    use_original: 是否使用原名而非译名，True-田中レモン，False-田中檸檬
    """
    import json
    import time
    import random

    actressAliasMap = {}

    actressAliasFilePath = "data/actress_alias.json"
    # 检查文件是否存在
    if not os.path.exists(actressAliasFilePath):
        # 如果文件不存在，创建文件并写入空字典
        with open(actressAliasFilePath, "w", encoding="utf-8") as file:
            json.dump({}, file)

    typeList = ["censored", "uncensored", "western"]
    page_url = f"{base_url}/actors/{typeList[type]}"
    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    proxy=_get_proxy_settings(),
                    args=['--disable-blink-features=AutomationControlled'],
                )
                context = browser.new_context(locale='zh-CN', user_agent=USER_AGENT)
                page = context.new_page()
                html, _ = get_html_wrapper(page_url, page, selectors=("div.box.actor-box",))
                context.close()
                browser.close()
            actors = html.xpath("//div[@class='box actor-box']/a")

            count = 0
            for actor in actors:
                count += 1
                actor_name = actor.xpath("strong/text()")[0].strip()
                actor_url = actor.xpath("@href")[0]
                # actor_url = f"https://javdb.com{actor_url}"  # 构造演员主页的完整URL

                # 进入演员主页，获取更多信息
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        proxy=_get_proxy_settings(),
                        args=['--disable-blink-features=AutomationControlled'],
                    )
                    context = browser.new_context(locale='zh-CN', user_agent=USER_AGENT)
                    page = context.new_page()
                    actor_html, _ = get_html_wrapper(actor_url, page, selectors=("span.actor-section-name",))
                    context.close()
                    browser.close()
                # 解析演员所有名字信息
                names_span = actor_html.xpath("//span[@class='actor-section-name']")[0]
                aliases_span_list = actor_html.xpath("//span[@class='section-meta']")
                aliases_span = aliases_span_list[0]

                names_list = [name.strip() for name in names_span.text.split(",")]
                if len(aliases_span_list) > 1:
                    aliases_list = [
                        alias.strip() for alias in aliases_span.text.split(",")
                    ]
                else:
                    aliases_list = []

                # 将信息添加到actressAliasMap中
                actressAliasMap[names_list[-1 if use_original else 0]] = (
                    names_list + aliases_list
                )
                print(
                    f"{count} --- {names_list[-1 if use_original else 0]}: {names_list + aliases_list}"
                )

                if count == 10:
                    # 将数据写回文件
                    with open(actressAliasFilePath, "r", encoding="utf-8") as file:
                        existing_data = json.load(file)

                    # 合并现有数据和新爬取的数据
                    existing_data.update(actressAliasMap)

                    # 将合并后的数据写回文件
                    with open(actressAliasFilePath, "w", encoding="utf-8") as file:
                        json.dump(existing_data, file, ensure_ascii=False, indent=2)

                    actressAliasMap = {}  # 重置actressAliasMap

                    print(
                        f"已爬取 {count} 个女优，数据已更新并写回文件:",
                        actressAliasFilePath,
                    )

                    # 重置计数器
                    count = 0

                time.sleep(max(1, 10 * random.random()))  # 随机等待 1-10 秒

            # 判断是否有下一页按钮
            next_page_link = html.xpath(
                "//a[@rel='next' and @class='pagination-next']/@href"
            )
            if not next_page_link:
                break  # 没有下一页，结束循环
            else:
                next_page_url = f"{next_page_link[0]}"
                page_url = next_page_url

        except SiteBlocked:
            raise

    with open(actressAliasFilePath, "r", encoding="utf-8") as file:
        existing_data = json.load(file)

    # 合并现有数据和新爬取的数据
    existing_data.update(actressAliasMap)

    # 将合并后的数据写回文件
    with open(actressAliasFilePath, "w", encoding="utf-8") as file:
        json.dump(existing_data, file, ensure_ascii=False, indent=2)

    print(f"已爬取 {count} 个女优，数据已更新并写回文件:", actressAliasFilePath)


if __name__ == "__main__":
    # collect_actress_alias()
    movie = MovieInfo('FC2-2735981')
    try:
        parse_clean_data(movie)
        print(movie)
    except CrawlerError as e:
        print(repr(e))
