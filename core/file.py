"""与文件相关的各类功能"""
import os
import sys
from tkinter import filedialog, Tk

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.avid import get_id
from core.config import cfg
from core.datatype import Movie


def select_folder(default_dir=''):
    """使用文件对话框提示用户选择一个文件夹"""
    directory_root = Tk()
    directory_root.withdraw()
    path = filedialog.askdirectory(initialdir=default_dir)
    if path != '':
        return os.path.normpath(path)


def get_movies(root: str):
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


if __name__ == "__main__":
    get_movies(select_folder())
