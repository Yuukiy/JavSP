import os
import time
import logging

import colorama
import pretty_errors
from tqdm import tqdm

from core.nfo import write_nfo
from core.file import select_folder, get_movies
from core.config import cfg
from core.image import crop_poster
from core.datatype import MovieInfo
from web.base import download
from web.javbus import parse_data


class TqdmOut:
    """用于将logging的stream输出重定向到tqdm"""
    @classmethod
    def write(cls, s, file=None, nolock=False):
        tqdm.write(s, file=file, end='', nolock=nolock)


pretty_errors.configure(display_link=True)
logging.basicConfig(stream=TqdmOut, level=logging.INFO)


if __name__ == "__main__":
    colorama.init(autoreset=True)
    root = select_folder()
    os.chdir(root)

    movies = get_movies(root)
    logging.info(f'共找到{len(movies)}部影片\n')

    outer_bar = tqdm(movies, ascii=True, leave=False)
    for m in outer_bar:
        outer_bar.set_description(f'正在整理影片: {m.dvdid}')
        inner_bar = tqdm(total=6, desc='步骤', ascii=True, leave=False)
        # 执行具体的抓取和整理任务
        info = MovieInfo(m.dvdid)
        inner_bar.set_description(f'使用JavBus抓取数据')
        parse_data(info)
        inner_bar.update()
        inner_bar.set_description(f'使用JavLibrary抓取数据')
        time.sleep(1)
        inner_bar.update()
        inner_bar.set_description('汇总数据')
        time.sleep(1)
        inner_bar.update()
        inner_bar.set_description('下载封面图片')
        download(info.cover, f'{info.dvdid}-fanart.jpg')
        inner_bar.update()
        inner_bar.set_description('裁剪海报封面')
        crop_poster(f'{info.dvdid}-fanart.jpg', f'{info.dvdid}-poster.jpg')
        time.sleep(1)
        inner_bar.update()
        inner_bar.set_description('写入NFO')
        write_nfo(info)
        inner_bar.update()
        logging.info(f'影片整理完成: {m.dvdid}')
        inner_bar.close()
