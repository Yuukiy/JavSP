import os
import sys
import time
import logging
from threading import Thread

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
file_handler = logging.FileHandler(filename='JavSP.log', mode='a', encoding='utf-8')
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
def parallel_crawler(movie: MovieInfo, tqdm_bar=None):
    """使用多线程抓取不同网站的数据"""
    # 根据影片的数据源获取对应的抓取器
    crawlers = cfg.Priority[movie.data_src]
    all_info = {}
    for i in crawlers:
        parser = getattr(sys.modules[i], 'parse_data')
        info = MovieInfo(movie.dvdid)
        logger.debug(f'使用抓取器{i}抓取: {movie.dvdid}')
        th = Thread(target=parser, name=i, args=(info, ))
        th.start()
        th.join()
        all_info[i] = info
        if isinstance(tqdm_bar, tqdm):
            tqdm_bar.set_description(f'{i}: 抓取完成')
    return all_info


def info_summary(movie: Movie, all_info):
    """汇总多个来源的在线数据生成最终数据，生成本地资源的相关文件名"""
    info = all_info['web.javbus']
    d = {'title': info.title, 'actor': ','.join(info.actress), 'num': info.dvdid}
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
    return info


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
        info = info_summary(movie, all_info)
        inner_bar.update()

        inner_bar.set_description('移动影片文件')
        os.makedirs(movie.folderpath)
        os.rename(movie.files[0], movie.new_filepath)
        inner_bar.update()

        inner_bar.set_description('下载封面图片')
        download(info.cover, movie.fanart_file)
        inner_bar.update()

        inner_bar.set_description('裁剪海报封面')
        crop_poster(movie.fanart_file, movie.poster_file)
        time.sleep(1)
        inner_bar.update()

        inner_bar.set_description('写入NFO')
        write_nfo(info, movie.nfo_file)
        inner_bar.update()

        logger.info(f'整理完成: {movie.dvdid}')
        logger.info(f'相关文件已保存到: ' + movie.folderpath)
        inner_bar.close()
