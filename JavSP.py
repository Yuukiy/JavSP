import os
import sys
import time
import logging
import requests
import threading

import colorama
import pretty_errors
from tqdm import tqdm


from core.datatype import ColoredFormatter


class TqdmOut:
    """用于将logging的stream输出重定向到tqdm"""
    @classmethod
    def write(cls, s, file=None, nolock=False):
        tqdm.write(s, file=file, end='', nolock=nolock)


pretty_errors.configure(display_link=True)

# 禁用导入的模块中的日志（仅对此时已执行导入模块的生效）
for i in logging.root.manager.loggerDict:
    logging.getLogger(i).disabled = True
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(filename='JavSP.log', mode='w', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    fmt='%(asctime)s %(name)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
console_handler = logging.StreamHandler(stream=TqdmOut)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ColoredFormatter(fmt='%(message)s'))
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)


from core.nfo import write_nfo
from core.file import select_folder, get_movies
from core.config import cfg
from core.image import crop_poster
from core.datatype import Movie, MovieInfo
from web.base import download


# 爬虫是IO密集型任务，可以通过多线程提升效率
def parallel_crawler(movie: Movie, tqdm_bar=None):
    """使用多线程抓取不同网站的数据"""
    def wrapper(parser, info: MovieInfo):
        """对抓取器函数进行包装，便于更新提示信息和自动重试"""
        crawler_name = threading.current_thread().name
        task_info = f'Thread: {crawler_name}: {info.dvdid}'
        retry = 0
        while (retry < cfg.Network.retry):
            retry += 1
            try:
                parser(info)
                logger.debug(f'{task_info}: 抓取成功')
                if isinstance(tqdm_bar, tqdm):
                    tqdm_bar.set_description(f'{crawler_name}: 抓取完成')
                break
            except requests.exceptions.RequestException as e:
                logger.debug(f'{task_info}: 网络错误，正在重试 ({retry}/{cfg.Network.retry}): \n{e}')
                if isinstance(tqdm_bar, tqdm):
                    tqdm_bar.set_description(f'{crawler_name}: 网络错误，正在重试')
            except Exception as e:
                logger.exception(f'{task_info}: 未处理的异常: {e}')

    # 根据影片的数据源获取对应的抓取器
    crawler_mods = cfg.Priority[movie.data_src]
    all_info = {i: MovieInfo(movie.dvdid) for i in crawler_mods}
    thread_pool = []
    for mod, info in all_info.items():
        parser = getattr(sys.modules[mod], 'parse_data')
        # 将all_info中的info实例传递给parser，parser抓取完成后，info实例的值已经完成更新
        th = threading.Thread(target=wrapper, name=mod, args=(parser, info))
        th.start()
        thread_pool.append(th)
    # 等待所有线程结束
    for th in thread_pool:
        th.join()
    return all_info


def info_summary(movie: Movie, all_info):
    """汇总多个来源的在线数据生成最终数据"""
    # 多线程下，all_info中的键值顺序不一定和爬虫的启动顺序一致，因此要重新获取优先级
    crawlers = cfg.Priority[movie.data_src]
    # 按照优先级取出各个爬虫获取到的信息
    final_info = MovieInfo(movie.dvdid)
    attrs = [i for i in dir(final_info) if not i.startswith('_')]
    for c in crawlers:
        absorbed = []
        crawlered_info = all_info[c]
        # 遍历所有属性，如果某一属性当前值为空而爬取的数据中含有该属性，则采用爬虫的属性
        for attr in attrs:
            current = getattr(final_info, attr)
            incoming = getattr(crawlered_info, attr)
            if (not current) and (incoming):
                setattr(final_info, attr, incoming)
                absorbed.append(attr)
        if absorbed:
            logger.debug(f"从'{c}'中获取了字段: " + ' '.join(absorbed))
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
    d = {'num': info.dvdid}
    d['title'] = info.title if info.title else cfg.NamingRule.null_for_title
    if info.actress:
        d['actor'] = ','.join(info.actress)
    else:
        d['actor'] = cfg.NamingRule.null_for_actor
    remaining_keys = ['socre', 'serial', 'director', 'producer', 'publisher', 'publish_date']
    for i in remaining_keys:
        value = getattr(info, i, None)
        if value:
            d[i] = value
        else:
            d[i] = cfg.NamingRule.null_for_others
    # 生成相关文件的路径
    folderpath = os.path.normpath(cfg.NamingRule.folderpath.substitute(**d))
    basename = os.path.normpath(cfg.NamingRule.filename.substitute(**d))
    new_filepath = os.path.join(folderpath, basename + os.path.splitext(movie.files[0])[1])
    nfo_file = os.path.join(folderpath, f'{basename}.nfo')
    fanart = os.path.join(folderpath, f'{basename}-fanart.jpg')
    poster = os.path.join(folderpath, f'{basename}-poster.jpg')
    setattr(movie, 'folderpath', folderpath)
    setattr(movie, 'nfo_file', nfo_file)
    setattr(movie, 'fanart_file', fanart)
    setattr(movie, 'poster_file', poster)
    setattr(movie, 'new_filepath', new_filepath)


if __name__ == "__main__":
    colorama.init(autoreset=True)
    logger = logging.getLogger('main')
    root = select_folder()
    if not root:
        logger.warning('未选择文件夹，脚本退出')
        os.system('pause')
        os._exit(1)
    os.chdir(root)

    all_movies = get_movies(root)
    logger.info(f'共找到{len(all_movies)}部影片\n')

    outer_bar = tqdm(all_movies, ascii=True, leave=False)
    for movie in outer_bar:
        outer_bar.set_description(f'正在整理影片: {movie.dvdid}')
        inner_bar = tqdm(total=6, desc='步骤', ascii=True, leave=False)
        # 执行具体的抓取和整理任务
        inner_bar.set_description(f'启动并行任务抓取数据')
        all_info = parallel_crawler(movie, inner_bar)
        inner_bar.update()

        inner_bar.set_description('汇总数据')
        has_required_keys = info_summary(movie, all_info)
        inner_bar.update()
        if has_required_keys:
            inner_bar.set_description('移动影片文件')
            generate_names(movie)
            os.makedirs(movie.folderpath)
            os.rename(movie.files[0], movie.new_filepath)
            inner_bar.update()

            inner_bar.set_description('下载封面图片')
            download(movie.info.cover, movie.fanart_file)
            inner_bar.update()

            inner_bar.set_description('裁剪海报封面')
            crop_poster(movie.fanart_file, movie.poster_file)
            time.sleep(1)
            inner_bar.update()

            inner_bar.set_description('写入NFO')
            write_nfo(movie.info, movie.nfo_file)
            inner_bar.update()

            logger.info(f'整理完成: {movie.dvdid}')
            logger.info(f'相关文件已保存到: ' + movie.folderpath)
        else:
            logger.error('整理失败')
        inner_bar.close()
