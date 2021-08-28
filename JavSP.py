import os
import sys
import time
import logging
import requests
import threading
from shutil import copyfile

import colorama
import pretty_errors
from tqdm import tqdm


pretty_errors.configure(display_link=True)


from core.print import TqdmOut
from core.datatype import ColoredFormatter


# 配置 logging StreamHandler
root_logger = logging.getLogger()
console_handler = logging.StreamHandler(stream=TqdmOut)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ColoredFormatter(fmt='%(message)s'))
root_logger.addHandler(console_handler)

logger = logging.getLogger('main')


from core.nfo import write_nfo
from core.config import cfg, args
from core.file import *
from core.func import *
from core.image import *
from core.datatype import Movie, MovieInfo
from web.base import download
from web.translate import translate_movie_info


def import_crawlers(cfg):
    """按配置文件的抓取器顺序将该字段转换为抓取器的函数列表"""
    unknown_mods = []
    for typ, cfg_str in cfg.CrawlerSelect.items():
        mods = cfg_str.split(',')
        valid_mods = []
        for name in mods:
            try:
                # 导入fc2fan抓取器的前提: 配置了fc2fan的本地路径
                if name == 'fc2fan' and (not os.path.isdir(cfg.Crawler.fc2fan_local_path)):
                    logger.debug('由于未配置有效的fc2fan路径，已跳过该抓取器')
                    continue
                import_name = 'web.' + name
                __import__(import_name)
                valid_mods.append(import_name)  # 抓取器有效: 使用完整模块路径，便于程序实际使用
            except ModuleNotFoundError:
                unknown_mods.append(name)       # 抓取器无效: 仅使用模块名，便于显示
        cfg._sections['CrawlerSelect'][typ] = tuple(valid_mods)
    if unknown_mods:
        logger.warning('配置的抓取器无效: ' + ', '.join(unknown_mods))


# 爬虫是IO密集型任务，可以通过多线程提升效率
def parallel_crawler(movie: Movie, tqdm_bar=None):
    """使用多线程抓取不同网站的数据"""
    def wrapper(parser, info: MovieInfo, retry):
        """对抓取器函数进行包装，便于更新提示信息和自动重试"""
        crawler_name = threading.current_thread().name
        task_info = f'Crawler: {crawler_name}: {info.dvdid}'
        for cnt in range(retry):
            try:
                parser(info)
                logger.debug(f'{task_info}: 抓取成功')
                if isinstance(tqdm_bar, tqdm):
                    tqdm_bar.set_description(f'{crawler_name}: 抓取完成')
                break
            except requests.exceptions.RequestException as e:
                logger.debug(f'{task_info}: 网络错误，正在重试 ({cnt+1}/{retry}): \n{e}')
                if isinstance(tqdm_bar, tqdm):
                    tqdm_bar.set_description(f'{crawler_name}: 网络错误，正在重试')
            except Exception as e:
                logger.exception(f'{task_info}: 未处理的异常: {e}')
                break

    # 根据影片的数据源获取对应的抓取器
    crawler_mods = cfg.CrawlerSelect[movie.data_src]
    all_info = {i: MovieInfo(movie) for i in crawler_mods}
    thread_pool = []
    for mod, info in all_info.items():
        parser = getattr(sys.modules[mod], 'parse_data')
        # 将all_info中的info实例传递给parser，parser抓取完成后，info实例的值已经完成更新
        # TODO: 抓取器如果带有parse_data_raw，说明它已经自行进行了重试处理，此时将重试次数设置为1
        if hasattr(sys.modules[mod], 'parse_data_raw'):
            th = threading.Thread(target=wrapper, name=mod, args=(parser, info, 1))
        else:
            th = threading.Thread(target=wrapper, name=mod, args=(parser, info, cfg.Network.retry))
        th.start()
        thread_pool.append(th)
    # 等待所有线程结束
    timeout = cfg.Network.retry * cfg.Network.timeout
    for th in thread_pool:
        th.join(timeout=timeout)
    # 删除all_info中键名中的'web.'
    all_info = {k[4:]:v for k,v in all_info.items()}
    return all_info


def info_summary(movie: Movie, all_info):
    """汇总多个来源的在线数据生成最终数据"""
    final_info = MovieInfo(movie)
    ########## 部分字段配置了专门的选取逻辑，先处理这些字段 ##########
    # genre
    if 'javdb' in all_info:
        final_info.genre = all_info['javdb'].genre

    ########## 然后检查所有字段，如果某个字段还是默认值，则按照优先级选取数据 ##########
    # parser直接更新了all_info中的项目，而初始all_info是按照优先级生成的，已经符合配置的优先级顺序了
    # 按照优先级取出各个爬虫获取到的信息
    attrs = [i for i in dir(final_info) if not i.startswith('_')]
    for name, data in all_info.items():
        absorbed = []
        # 遍历所有属性，如果某一属性当前值为空而爬取的数据中含有该属性，则采用爬虫的属性
        for attr in attrs:
            current = getattr(final_info, attr)
            incoming = getattr(data, attr)
            if (not current) and (incoming):
                setattr(final_info, attr, incoming)
                absorbed.append(attr)
        if absorbed:
            logger.debug(f"从'{name}'中获取了字段: " + ' '.join(absorbed))
    ########## 部分字段放在最后进行检查 ##########
    # title
    if cfg.Crawler.title__chinese_first and 'airav' in all_info:
        if all_info['airav'].title and final_info.title != all_info['airav'].title:
            final_info.ori_title = final_info.title
            final_info.title = all_info['airav'].title
    # 检查是否所有必需的字段都已经获得了值
    for attr in cfg.Crawler.required_keys:
        if not getattr(final_info, attr, None):
            logger.error(f"所有爬虫均未获取到字段: '{attr}'，抓取失败")
            return False
    # 必需字段均已获得了值：将最终的数据附加到movie
    movie.info = final_info
    return True


def generate_names(movie: Movie):
    """按照模板生成相关文件的文件名"""
    info = movie.info
    # 准备用来填充命名模板的字典
    d = {}
    d['num'] = info.dvdid or info.cid
    d['title'] = info.title or cfg.NamingRule.null_for_title
    d['rawtitle'] = info.ori_title or d['title']
    d['actress'] = ','.join(info.actress) if info.actress else cfg.NamingRule.null_for_actress
    d['score'] = info.score or '0'
    d['serial'] = info.serial or cfg.NamingRule.null_for_serial
    d['director'] = info.director or cfg.NamingRule.null_for_director
    d['producer'] = info.producer or cfg.NamingRule.null_for_producer
    d['publisher'] = info.publisher or cfg.NamingRule.null_for_publisher
    d['date'] = info.publish_date or '0000-00-00'
    d['year'] = d['date'].split('-')[0]
    # cid中不会出现'-'，可以直接从d['num']拆分出label
    num_items = d['num'].split('-')
    d['label'] = num_items[0] if len(num_items) > 1 else '---'

    # 处理字段：替换不能作为文件名的字符，移除首尾的空字符
    for k, v in d.items():
        d[k] = replace_illegal_chars(v.strip())

    # 使用字典填充模板，生成相关文件的路径
    if hasattr(info, 'title_break'):
        copyd = d.copy()
        title_break = info.title_break
        for end in range(len(title_break), 0, -1):
            copyd['title'] = ''.join(title_break[:end])
            save_dir = os.path.normpath(cfg.NamingRule.save_dir.substitute(**copyd)).strip()
            basename = os.path.normpath(cfg.NamingRule.filename.substitute(**copyd)).strip()
            fanart_file = os.path.join(save_dir, f'{basename}-fanart.jpg')
            if check_path_len(fanart_file):
                movie.save_dir = save_dir
                movie.basename = basename
                movie.nfo_file = os.path.join(save_dir, f'{basename}.nfo')
                movie.fanart_file = fanart_file
                movie.poster_file = os.path.join(save_dir, f'{basename}-poster.jpg')
                logger.info(f"自动截短标题为:\n{copyd['title']}")
                break
    else:
        save_dir = os.path.normpath(cfg.NamingRule.save_dir.substitute(**d)).strip()
        basename = os.path.normpath(cfg.NamingRule.filename.substitute(**d)).strip()
        movie.save_dir = save_dir
        movie.basename = basename
        movie.nfo_file = os.path.join(save_dir, f'{basename}.nfo')
        movie.fanart_file = os.path.join(save_dir, f'{basename}-fanart.jpg')
        movie.poster_file = os.path.join(save_dir, f'{basename}-poster.jpg')
    # 生成nfo文件中的影片标题
    nfo_title = cfg.NamingRule.nfo_title.substitute(**d)
    setattr(info, 'nfo_title', nfo_title)


def postStep_videostation(movie: Movie):
    """使用群晖Video Station时，生成额外的影片poster、fanart文件"""
    fanart_ext = os.path.splitext(movie.fanart_file)[1]
    for file in movie.new_paths:
        # 创建与影片同名的fanart
        samename_fanart = os.path.splitext(file)[0] + fanart_ext
        copyfile(movie.fanart_file, samename_fanart)
        # 将fanart裁剪为png格式作为poster
        samename_poster = os.path.splitext(file)[0] + '.png'
        crop_poster(movie.fanart_file, samename_poster)


def RunNormalMode(all_movies):
    """普通整理模式"""
    def check_step(result):
        """检查一个整理步骤的结果，并负责更新tqdm的进度"""
        if result:
            inner_bar.update()
        else:
            raise Exception('步骤错误')

    outer_bar = tqdm(all_movies, desc='整理影片', ascii=True, leave=False)
    total_step = 7 if cfg.Translate.engine else 6
    for movie in outer_bar:
        try:
            # 初始化本次循环要整理影片任务
            filenames = [os.path.split(i)[1] for i in movie.files]
            logger.info('正在整理: ' + ', '.join(filenames))
            inner_bar = tqdm(total=total_step, desc='步骤', ascii=True, leave=False)
            # 依次执行各个步骤
            inner_bar.set_description(f'启动并发任务')
            all_info = parallel_crawler(movie, inner_bar)
            check_step(all_info)

            inner_bar.set_description('汇总数据')
            has_required_keys = info_summary(movie, all_info)
            check_step(has_required_keys)

            if cfg.Translate.engine:
                inner_bar.set_description('翻译影片信息')
                success = translate_movie_info(movie.info)
                check_step(success)
            
            inner_bar.set_description('移动影片文件')
            generate_names(movie)
            os.makedirs(movie.save_dir)
            movie.rename_files()
            check_step(True)

            inner_bar.set_description('下载封面图片')
            success = download_cover(movie.info.cover, movie.fanart_file, movie.info.big_cover)
            check_step(success)

            inner_bar.set_description('裁剪海报封面')
            crop_poster(movie.fanart_file, movie.poster_file)
            check_step(True)

            if 'video_station' in cfg.NamingRule.media_servers:
                postStep_videostation(movie)

            inner_bar.set_description('写入NFO')
            write_nfo(movie.info, movie.nfo_file)
            check_step(True)

            logger.info(f'整理完成，相关文件已保存到: {movie.save_dir}\n')
        except:
            logger.error('整理失败\n')
        finally:
            inner_bar.close()


def download_cover(cover_url, fanart_path, big_cover_url=None):
    """下载封面图片"""
    used_url = cover_url
    for _ in range(cfg.Network.retry):
        if big_cover_url:
            try:
                download(big_cover_url, fanart_path)
                used_url = big_cover_url
            except requests.exceptions.HTTPError:
                download(cover_url, fanart_path)
        else:
            download(cover_url, fanart_path)
        # 检查图片是否完整
        if valid_pic(fanart_path):
            if used_url == big_cover_url:
                filesize = get_fmt_size(fanart_path)
                width, height = get_pic_size(fanart_path)
                logger.info(f"已下载高清封面: {width}x{height}, {filesize}")
            # 图片完整时直接返回
            return True
        else:
            logger.debug(f"图片不完整，尝试重新下载: '{cover_url}'")
    else:
        logger.error(f"下载封面图片失败: '{cover_url}'")

    return False


def error_exit(success, err_info):
    """检查业务逻辑是否成功完成，如果失败则报错退出程序"""
    if not success:
        logger.error(err_info)
        sys_exit(1)


def sys_exit(code):
    # 脚本退出机制：检查是否需要关机 → 若不需要，检查是否需要保持当前窗口
    if args.shutdown:
        shutdown()
    elif not args.auto_exit:
        os.system('pause')
    # 最后传退出码退出
    sys.exit(code)


if __name__ == "__main__":
    colorama.init(autoreset=True)
    # 检查更新
    check_update(allow_check=cfg.Other.check_update)
    # 如果未配置有效代理，则显示相应提示
    if not cfg.Network.proxy:
        logger.warning('未配置有效代理，程序会努力继续运行，但是部分功能可能受限：\n'
                       ' - 将尝试自动获取部分站点的免代理地址，没有免代理地址的站点抓取器将无法工作\n'
                       ' - 抓取fanza的数据时，有一小部分影片仅能在日本归属的IP下抓取到')
    root = get_scan_dir(cfg.File.scan_dir)
    error_exit(root, '未选择要扫描的文件夹')
    # 导入抓取器，必须在chdir之前
    import_crawlers(cfg)
    os.chdir(root)

    print(f'扫描影片文件...')
    all_movies = scan_movies(root)
    movie_count = len(all_movies)
    error_exit(movie_count, '未找到影片文件')
    logger.info(f'扫描影片文件：共找到 {movie_count} 部影片')
    print('')

    RunNormalMode(all_movies)

    sys_exit(0)
