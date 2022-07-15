"""与文件相关的各类功能"""
import os
import re
import sys
import logging
from sys import platform
from typing import List

__all__ = ['scan_movies', 'get_fmt_size', 'get_remaining_path_len', 'replace_illegal_chars', 'get_failed_when_scan']


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.avid import *
from core.config import cfg
from core.datatype import Movie

logger = logging.getLogger(__name__)
failed_items = []


def scan_movies(root: str) -> List[Movie]:
    """获取文件夹内的所有影片的列表（自动探测同一文件夹内的分片）"""
    # 由于实现的限制: 
    # 1. 以数字编号最多支持10个分片，字母编号最多支持26个分片
    # 2. 允许分片间的编号有公共的前导符（如编号01, 02, 03），因为求prefix时前导符也会算进去

    # 扫描所有影片文件并获取它们的番号
    dic = {}    # avid: [abspath1, abspath2...]
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath.startswith('.'):
            # 特殊文件夹排除
            logger.debug(f"文件夹[{dirpath}]已被忽略11111。")
            continue
        dir_is_ignore = False
        for cif in cfg.File.ignore_folder:
            # 根目录被忽略或者是被忽略目录的子目录都排除
            if dirpath == cif or dirpath.find(cif) >= 0:
                dir_is_ignore = True
                break
        if dir_is_ignore is True:
            logger.debug(f"文件夹[{dirpath}]已被忽略222222。")
            continue
        logger.debug(f"文件夹[{dirpath}]没有被忽略。")
        for file in filenames:
            logger.debug(f"文件[{file}]开始处理")
            ext = os.path.splitext(file)[1].lower()
            if ext in cfg.File.media_ext:
                fullpath = os.path.join(dirpath, file)
                dvdid = get_id(fullpath)
                cid = get_cid(fullpath)
                # 如果文件名能匹配到cid，那么将cid视为有效id，因为此时dvdid多半是错的
                avid = cid if cid else dvdid
                if avid:
                    if avid in dic:
                        dic[avid].append(fullpath)
                    else:
                        dic[avid] = [fullpath]
                else:
                    fail = Movie('无法识别番号')
                    fail.files = [fullpath]
                    failed_items.append(fail)
                    logger.error(f"无法提取影片番号: '{fullpath}'")
    # 检查是否有多部影片对应同一个番号
    non_slice_dup = {}  # avid: [abspath1, abspath2...]
    for avid, files in dic.copy().items():
        # 一一对应的直接略过
        if len(files) == 1:
            continue
        dirs = set([os.path.split(i)[0] for i in files])
        # 不同位置的多部影片有相同番号时，略过并报错
        if len(dirs) > 1:
            non_slice_dup[avid] = files
            del dic[avid]
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
            non_slice_dup[avid] = files
            del dic[avid]
            continue
        # 影片编号必须从 0/1/a 开始且编号连续
        slices = sorted(remaining)
        first, last = slices[0], slices[-1]
        if (first not in ('0', '1', 'a')) or (ord(last) != (ord(first)+len(slices)-1)):
            non_slice_dup[avid] = files
            del dic[avid]
            continue
        # 生成最终的分片信息
        mapped_files = [files[remaining.index(i)] for i in slices]
        dic[avid] = mapped_files

    # 汇总输出错误提示信息
    msg = ''
    for avid, files in non_slice_dup.items():
        msg += f'{avid}: \n'
        for f in files:
            msg += ('  ' + os.path.relpath(f, root) + '\n')
    if msg:
        logger.error("下列番号对应多部影片文件且不符合分片规则，已略过整理，请手动处理后重新运行脚本: \n" + msg)
    # 转换数据的组织格式
    movies = []
    for avid, files in dic.items():
        src = guess_av_type(avid)
        if src != 'cid':
            mov = Movie(avid)
        else:
            mov = Movie(cid=avid)
            # 即使初步识别为cid，也存储dvdid以供误识别时退回到dvdid模式进行抓取
            mov.dvdid = get_id(files[0])
        mov.files = files
        mov.data_src = src
        logger.debug(f'影片数据源类型: {avid}: {src}')
        movies.append(mov)
    return movies


def get_failed_when_scan():
    """获取扫描影片过程中无法自动识别番号的条目"""
    return failed_items


def replace_illegal_chars(name):
    """将不能用于文件名的字符替换为形近的字符"""
    # 非法字符列表 https://stackoverflow.com/a/31976060/6415337
    if platform == 'win32': 
        # http://www.unicode.org/Public/security/latest/confusables.txt
        charmap = {'<': '❮',
                   '>': '❯',
                   ':': '：',
                   '"': '″',
                   '/': '／',
                   '\\': '＼',
                   '|': '｜',
                   '?': '？',
                   '*': '꘎'}
        for c, rep in charmap.items():
            name = name.replace(c, rep)
    elif platform == "darwin":  # MAC OS X
        name = name.replace(':', '：')
    else:   # 其余都当做Linux处理
        name = name.replace('/', '／')
    return name


def get_remaining_path_len(path):
    """计算当前系统支持的最大路径长度与给定路径长度的差值"""
    #TODO: 支持不同的操作系统
    fullpath = os.path.abspath(path)
    remaining = cfg.NamingRule.max_path_len - len(fullpath)
    return remaining


def get_fmt_size(file_or_size) -> str:
    """获取格式化后的文件大小

    Args:
        file_or_size (str or int): 文件路径或者文件大小

    Returns:
        str: e.g. 20.21 MiB
    """
    if isinstance(file_or_size, (int, float)):
        size = file_or_size
    else:
        size = os.path.getsize(file_or_size)
    for unit in ['','Ki','Mi','Gi','Ti']:
        # 1023.995: to avoid rounding bug when format str, e.g. 1048571 -> 1024.0 KiB
        if abs(size) < 1023.995:
            return f"{size:3.2f} {unit}B"
        size /= 1024.0


if __name__ == "__main__":
    p = "C:/Windows\\System32//PerceptionSimulation\\..\\Assets\\/ClosedHand.png"
    print(get_remaining_path_len(p))
