"""与文件相关的各类功能"""
import os
import re
import sys
import logging
from typing import List
from tkinter import filedialog, Tk

__all__ = ['select_folder', 'scan_movies', 'get_fmt_size']


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.avid import get_id
from core.config import cfg
from core.datatype import Movie

logger = logging.getLogger(__name__)


def select_folder(default_dir=''):
    """使用文件对话框提示用户选择一个文件夹"""
    directory_root = Tk()
    directory_root.withdraw()
    path = filedialog.askdirectory(initialdir=default_dir)
    if path != '':
        return os.path.normpath(path)


def scan_movies(root: str) -> List[Movie]:
    """获取文件夹内的所有影片的列表（自动探测同一文件夹内的分片）"""
    # 由于实现的限制: 
    # 1. 以数字编号最多支持10个分片，字母编号最多支持26个分片
    # 2. 允许分片间的编号有公共的前导符（如编号01, 02, 03），因为求prefix时前导符也会算进去

    # 扫描所有影片文件并获取它们的番号
    dic = {}    # dvdid: [abspath1, abspath2...]
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames:
            if name.startswith('.') or name in cfg.File.ignore_folder:
                dirnames.remove(name)
        for file in filenames:
            ext = os.path.splitext(file)[1]
            if ext in cfg.File.media_ext:
                fullpath = os.path.join(dirpath, file)
                dvdid = get_id(fullpath)
                if dvdid:
                    if dvdid in dic:
                        dic[dvdid].append(fullpath)
                    else:
                        dic[dvdid] = [fullpath]
                else:
                    logger.error(f"无法提取影片番号: '{fullpath}'")
    # 检查是否有多部影片对应同一个番号
    non_slice_dup = {}  # dvdid: [abspath1, abspath2...]
    for dvdid, files in dic.copy().items():
        # 一一对应的直接略过
        if len(files) == 1:
            continue
        dirs = set([os.path.split(i)[0] for i in files])
        # 不同位置的多部影片有相同番号时，略过并报错
        if len(dirs) > 1:
            non_slice_dup[dvdid] = files
            del dic[dvdid]
            continue
        # 提取分片信息（如果正则替换成功，只会剩下单个小写字符）。相关变量都要使用同样的列表生成顺序
        basenames = [os.path.basename(i) for i in files]
        prefix = os.path.commonprefix(basenames)
        pattern = re.compile(prefix + r'\s*([a-z\d])\s*\.\w+$', flags=re.I)
        remaining = [pattern.sub(r'\1', i).lower() for i in basenames]
        # 如果remaining中的项长度不为1，说明有文件名不符合正则表达式条件（没有发生替换或不带分片信息）
        if (any([len(i) != 1 for i in remaining]) 
            # remaining为初步提取的分片信息，不允许有重复值
            or len(remaining) != len(set(remaining))):
            non_slice_dup[dvdid] = files
            del dic[dvdid]
            continue
        # 影片编号必须从 0/1/a 开始且编号连续
        slices = sorted(remaining)
        first, last = slices[0], slices[-1]
        if (first not in ('0', '1', 'a')) or (ord(last) != (ord(first)+len(slices)-1)):
            non_slice_dup[dvdid] = files
            del dic[dvdid]
            continue
        # 生成最终的分片信息
        mapped_files = [files[remaining.index(i)] for i in slices]
        dic[dvdid] = mapped_files

    # 汇总输出错误提示信息
    msg = ''
    for dvdid, files in non_slice_dup.items():
        msg += f'{dvdid}: \n'
        for f in files:
            msg += ('  ' + os.path.relpath(f, root) + '\n')
    if msg:
        logger.error("下列番号对应多部影片文件且不符合分片规则，已略过整理，请手动处理后重新运行脚本: \n" + msg)
    # 转换数据的组织格式
    movies = []
    for dvdid, files in dic.items():
        mov = Movie(dvdid)
        mov.files = files
        movies.append(mov)
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
    print(scan_movies(select_folder()))
