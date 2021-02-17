"""与文件相关的各类功能"""
import os
import sys
from typing import List
from tkinter import filedialog, Tk


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.avid import get_id
from core.config import cfg
from core.datatype import Movie


__all__ = ['select_folder', 'get_movies', 'get_fmt_size']


def select_folder(default_dir=''):
    """使用文件对话框提示用户选择一个文件夹"""
    directory_root = Tk()
    directory_root.withdraw()
    path = filedialog.askdirectory(initialdir=default_dir)
    if path != '':
        return os.path.normpath(path)


def get_movies(root: str) -> List[Movie]:
    """获取文件夹内的所有影片的列表（自动探测分片，但要求分片在同一文件夹内）"""
    movies = []
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames:
            if name.startswith('.') or name in cfg.File.ignore_folder:
                dirnames.remove(name)
        for file in filenames:
            ext = os.path.splitext(file)[1]
            if ext in cfg.File.media_ext:
                dvdid = get_id(file)
                m = Movie(dvdid)
                m.files.append(os.path.join(dirpath, file))
                movies.append(m)
    return movies


def get_fmt_size(file_or_size) -> str:
    """获取格式化后的文件大小

    Args:
        file_or_size (str or int): 文件路径或者文件大小

    Returns:
        str: e.g. 20.21 MiB
    """
    if isinstance(file_or_size, int):
        size = file_or_size
    else:
        size = os.path.getsize(file_or_size)
    for unit in ['','Ki','Mi','Gi','Ti']:
        # 1023.995: to avoid rounding bug when format str, e.g. 1048571 -> 1024.0 KiB
        if abs(size) < 1023.995:
            return f"{size:3.2f} {unit}B"
        size /= 1024.0


if __name__ == "__main__":
    print(get_fmt_size(1048571))
