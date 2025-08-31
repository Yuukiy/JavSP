"""从MISSAV抓取数据"""
import os
import sys
import glob
import time
import shutil
import subprocess
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import get_html
from web.exceptions import *
from core.config import cfg
from core.datatype import MovieInfo

from lxml import html as LH  # 用于解析本地缓存 html

logger = logging.getLogger(__name__)
base_url = 'https://missav.ai'
# 备用链接：https://missav.ws 
CUR_DIR = os.path.dirname(__file__)
CACHE_DIR = os.path.join(CUR_DIR, 'cache')
CACHE_BUILDER = os.path.join(CUR_DIR, 'missav_cache.py')


def _normalize_full_id(raw: str) -> (str, bool):
    """规整 full_id，但不改变既有参数与最终数据的对外表现"""
    fid = raw.strip()
    is_fc2 = fid.startswith('FC2-')
    # 去掉结尾 C/U
    if fid.endswith(("C", "c", "U", "u")):
        fid = fid[:-1]
    # 去掉中间 -C / -U
    for suf in ("-C", "-c", "-U", "-u"):
        if suf in fid:
            fid = fid.replace(suf, "")
    # FC2 特例：搜索/缓存用 FC2-PPV-
    if is_fc2:
        fid = fid.replace('FC2-', 'FC2-PPV-')
    return fid, is_fc2


def _run_cache_builder(full_id: str):
    """调用 missav_cache.py 同步生成缓存；若脚本不存在则静默跳过"""
    if not os.path.isfile(CACHE_BUILDER):
        logger.debug("missav_cache.py 不存在，跳过缓存构建。")
        return
    try:
        # 以当前 Python 解释器同步调用，传入 full_id
        logger.debug(f"启动缓存构建：{CACHE_BUILDER} {full_id}")
        subprocess.run([sys.executable, CACHE_BUILDER, full_id],
                       cwd=CUR_DIR,
                       check=True,
                       env=os.environ.copy()
                       )
    except subprocess.CalledProcessError as e:
        logger.warning(f"missav_cache.py 运行失败（忽略并继续在线抓取）：{e}")


def _iter_cached_detail_files(norm_full_id: str):
    """遍历 cache 中可能的 detail 文件（顺序稳定），不并发"""
    if not os.path.isdir(CACHE_DIR):
        return []
    # 兼容大小写的简单策略：列出所有 *_detail_*.html 再筛选前缀
    pattern = os.path.join(CACHE_DIR, "*_detail_*.html")
    candidates = sorted(glob.glob(pattern))
    wanted_prefixes = {
        f"{norm_full_id}_detail_".lower(),
        f"{norm_full_id}_detail_".upper(),
        f"{norm_full_id}_detail_",
    }
    results = [p for p in candidates
               if os.path.basename(p).startswith(tuple(wanted_prefixes))]
    return results


def _clear_cache_dir():
    """清空 cache 目录内容，但保留目录本身"""
    if not os.path.isdir(CACHE_DIR):
        return
    for name in os.listdir(CACHE_DIR):
        path = os.path.join(CACHE_DIR, name)
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            logger.debug(f"清理缓存文件失败：{path} -> {e}")


def _fill_movie_from_doc(doc, movie: MovieInfo, is_fc2: bool):
    """从已解析的详情 doc 中抽取字段并写入 movie（与原逻辑一致）"""
    url          = doc.xpath("string(//meta[@property='og:url']/@content)")
    
    title = doc.xpath("string(//meta[@property='og:title']/@content)").split(" ", 1)[1] \
        if " " in doc.xpath("string(//meta[@property='og:title']/@content)") \
        else doc.xpath("string(//meta[@property='og:title']/@content)")
    
    plot         = doc.xpath("string(//meta[@property='og:description']/@content)")
    cover        = doc.xpath("string(//meta[@property='og:image']/@content)")
    director     = doc.xpath("string(//meta[@property='og:video:director']/@content)")
    publish_date = doc.xpath("string(//meta[@property='og:video:release_date']/@content)")
    duration_raw = doc.xpath("string(//meta[@property='og:video:duration']/@content)")
    try:
        duration_min = str(int(duration_raw) // 60)
    except (ValueError, TypeError):
        duration_min = ""

    dvdid        = doc.xpath("string(//div[@class='text-secondary'][span[normalize-space()='品番:']]/span[@class='font-medium'])")
#   规整dvdId中的特殊子串
    replacements = {
        "FC2-PPV-": "FC2-",
        "-UNCENSORED-LEAK": "",
        "-CHINESE-SUBTITLE": "",
        "-ENGLISH-SUBTITLE": "",
    }
    for old, new in replacements.items():
        dvdid = dvdid.replace(old, new)
    
    producer = doc.xpath("string(//div[@class='text-secondary'][span[normalize-space()='メーカー:']]/a)")
    serial   = doc.xpath("string(//div[@class='text-secondary'][span[normalize-space()='シリーズ:']]/a)")
    actress  = [a.strip() for a in doc.xpath("//div[@class='text-secondary'][span[normalize-space()='女優:']]//a/text()")]
    genre    = [g.strip() for g in doc.xpath("//div[@class='text-secondary'][span[normalize-space()='ジャンル:']]//a/text()")]
        # if '-U' in dvdid:
        # movie.uncensored = True
        # genre.append('UNCENSORED')

    # 赋值保持原有语义
    movie.dvdid = dvdid
    movie.url = url
    movie.title = title
    movie.plot = plot
    movie.cover = cover
    movie.director = director
    movie.publish_date = publish_date
    movie.duration = duration_min
    movie.genre = genre
    movie.actress = actress

    if is_fc2:
        movie.producer = serial
    else:
        movie.producer = producer
        movie.serial = serial


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    # —— 统一在“搜索/缓存之前”把 full_id 规整完毕 ——
    # 说明：此处只影响内部抓取方式，不改变对外字段和值的呈现。
    norm_full_id, is_fc2 = _normalize_full_id(movie.dvdid)

    # 1) 先尝试调用缓存构建器
    _run_cache_builder(norm_full_id)

    # 2) 尝试读取缓存
    cached_files = _iter_cached_detail_files(norm_full_id)
    logger.debug(f"缓存明细文件数量：{len(cached_files)}")

    # 标记：是否走了缓存路径，用于事后清理
    used_cache_flow = False

    if cached_files:
        used_cache_flow = True
        # 3) 依次（不并发）解析缓存文件，优先选择“品番”匹配度最高的一个
        best_doc = None
        best_match = False

        for fp in cached_files:
            try:
                with open(fp, 'rb') as f:
                    content = f.read()
                doc = LH.fromstring(content)

                # 粗判品番是否匹配（去除 FC2-PPV- 与 C/U 等差异）
                cached_dvdid = doc.xpath("string(//div[@class='text-secondary'][span[normalize-space()='品番:']]/span[@class='font-medium'])").strip()
                cached_cmp = cached_dvdid.replace('FC2-PPV-', 'FC2-').lower()
                want_cmp = movie.dvdid.strip().lower().rstrip('cCuU').replace('-c', '').replace('-u', '')

                if cached_cmp == want_cmp and not best_match:
                    # 第一优先：直接匹配，立刻用它
                    _fill_movie_from_doc(doc, movie, is_fc2)
                    best_match = True
                    best_doc = None  # 已经写入，不需要备用
                    break
                else:
                    # 作为备用（若后面都不匹配，就用第一个可解析的）
                    if best_doc is None:
                        best_doc = doc
            except Exception as e:
                logger.debug(f"解析缓存文件失败：{fp} -> {e}")

        if not best_match and best_doc is not None:
            _fill_movie_from_doc(best_doc, movie, is_fc2)

        # 若缓存解析失败（极端情况），回退到线上流程
        if not movie.title:
            logger.debug("缓存存在但未成功解析，回退到在线抓取。")
        else:
            # 缓存路径已完成解析，准备清理缓存后返回
            _clear_cache_dir()
            return

    # —— 以下为你的原有“在线抓取”逻辑（保持不变） ——

    # 搜索页
    html = get_html(f'{base_url}/ja/search/{norm_full_id}')

    # 从搜索结果中定位目标卡片
    ids = html.xpath("//div[contains(@class,'aspect-w-16') and contains(@class,'aspect-h-9')]//img/@alt")
    urls = html.xpath("//div[contains(@class,'aspect-w-16') and contains(@class,'aspect-h-9')]//a[@href]/@href")
    ids_lower = [i.strip().lower() for i in ids]

    if norm_full_id.lower() in ids_lower:
        url = urls[ids_lower.index(norm_full_id.lower())]
        # 相对路径 -> 绝对路径
        if url.startswith('/'):
            url = base_url + url
        # 语言路径调整（如需）
        url = url.replace('/tw/', '/cn/', 1)
    else:
        # 在线搜索失败，若先前使用了缓存流程，仍清空缓存再抛错
        if used_cache_flow:
            _clear_cache_dir()
        raise MovieNotFoundError(__name__, movie.dvdid, ids)

    # 详情页
    doc = get_html(url)
    _fill_movie_from_doc(doc, movie, is_fc2)

    # 在线抓取路径结束后，如果之前走过缓存构建器，也清一次缓存
    if used_cache_flow:
        _clear_cache_dir()


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logger.root.handlers[1].level = logging.DEBUG

    movie = MovieInfo('082713-417')
    try:
        parse_data(movie)
        print(movie)
    except CrawlerError as e:
        logger.error(e, exc_info=1)
