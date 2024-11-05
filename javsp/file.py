"""与文件相关的各类功能"""
import os
from pathlib import Path
import re
import ctypes
import logging
import itertools
import json
from sys import platform
from typing import List


__all__ = ['scan_movies', 'get_fmt_size', 'get_remaining_path_len', 'replace_illegal_chars', 'get_failed_when_scan', 'find_subtitle_in_dir']


from javsp.avid import *
from javsp.lib import re_escape
from javsp.config import Cfg
from javsp.datatype import Movie

logger = logging.getLogger(__name__)
failed_items = []


def scan_movies(root: str) -> List[Movie]:
    """获取文件夹内的所有影片的列表（自动探测同一文件夹内的分片）"""
    # 由于实现的限制: 
    # 1. 以数字编号最多支持10个分片，字母编号最多支持26个分片
    # 2. 允许分片间的编号有公共的前导符（如编号01, 02, 03），因为求prefix时前导符也会算进去

    # 扫描所有影片文件并获取它们的番号
    dic = {}    # avid: [abspath1, abspath2...]
    small_videos = {}
    ignore_folder_name_pattern = re.compile('|'.join(Cfg().scanner.ignored_folder_name_pattern))
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames.copy():
            if ignore_folder_name_pattern.match(name):
                dirnames.remove(name)
        for file in filenames:
            ext = os.path.splitext(file)[1].lower()
            if ext in Cfg().scanner.filename_extensions:
                fullpath = os.path.join(dirpath, file)
                # 忽略小于指定大小的文件
                filesize = os.path.getsize(fullpath)
                if filesize < Cfg().scanner.minimum_size:
                    small_videos.setdefault(file, []).append(fullpath)
                    continue
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
    # 多分片影片容易有文件大小低于阈值的子片，进行特殊处理
    has_avid = {}
    for name in list(small_videos.keys()):
        dvdid = get_id(name)
        cid = get_cid(name)
        avid = cid if cid else dvdid
        if avid in dic:
            dic[avid].extend(small_videos.pop(name))
        elif avid:
            has_avid[name] = avid
    # 对于前面忽略的视频生成一个简单的提示
    small_videos = {k:sorted(v) for k,v in sorted(small_videos.items())}
    skipped_files = list(itertools.chain(*small_videos.values()))
    skipped_cnt = len(skipped_files)
    if skipped_cnt > 0:
        if len(has_avid) > 0:
            logger.info(f"跳过了 {', '.join(has_avid)} 等{skipped_cnt}个小于指定大小的视频文件")
        else:
            logger.info(f"跳过了{skipped_cnt}个小于指定大小的视频文件")
        logger.debug('跳过的视频文件如下:\n' + '\n'.join(skipped_files))
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
        try:
            pattern_expr = re_escape(prefix) + r'\s*([a-z\d])\s*'
            pattern = re.compile(pattern_expr, flags=re.I)
        except re.error:
            logger.debug(f"正则识别影片分片信息时出错: '{pattern_expr}'")
            del dic[avid]
            continue
        remaining = [pattern.sub(r'\1', i).lower() for i in basenames]
        postfixes = [i[1:] for i in remaining]
        slices = [i[0] for i in remaining]
        # 如果有不同的后缀，说明有文件名不符合正则表达式条件（没有发生替换或不带分片信息）
        if (len(set(postfixes)) != 1
            # remaining为初步提取的分片信息，不允许有重复值
            or len(slices) != len(set(slices))):
            logger.debug(f"无法识别分片信息: {prefix=}, {remaining=}")
            non_slice_dup[avid] = files
            del dic[avid]
            continue
        # 影片编号必须从 0/1/a 开始且编号连续
        sorted_slices = sorted(slices)
        first, last = sorted_slices[0], sorted_slices[-1]
        if (first not in ('0', '1', 'a')) or (ord(last) != (ord(first)+len(sorted_slices)-1)):
            logger.debug(f"无效的分片起始编号或分片编号不连续: {sorted_slices=}")
            non_slice_dup[avid] = files
            del dic[avid]
            continue
        # 生成最终的分片信息
        mapped_files = [files[slices.index(i)] for i in sorted_slices]
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
    movies: List[Movie] = []
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


_PARDIR_REPLACE = re.compile(r'\.{2,}')
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
    # 处理连续多个英文句点.
    if os.pardir in name:
        name = _PARDIR_REPLACE.sub('…', name)
    return name


def is_remote_drive(path: str):
    """判断一个路径是否为远程映射到本地"""
    #TODO: 当前仅支持Windows平台
    if platform != 'win32':
        return False
    DRIVE_REMOTE = 0x4
    drive = os.path.splitdrive(os.path.abspath(path))[0] + os.sep
    result = ctypes.windll.kernel32.GetDriveTypeW(drive)
    return result == DRIVE_REMOTE


def get_remaining_path_len(path):
    """计算当前系统支持的最大路径长度与给定路径长度的差值"""
    #TODO: 支持不同的操作系统
    fullpath = os.path.abspath(path)
    # Windows: If the length exceeds ~256 characters, you will be able to see the path/files via Windows/File Explorer, but may not be able to delete/move/rename these paths/files
    length = len(fullpath.encode('utf-8')) if Cfg().summarizer.path.length_by_byte else len(fullpath)
    remaining = Cfg().summarizer.path.length_maximum - length
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


_sub_files = {}
SUB_EXTENSIONS = ('.srt', '.ass')
def find_subtitle_in_dir(folder: str, dvdid: str):
    """在folder内寻找是否有匹配dvdid的字幕"""
    folder_data = _sub_files.get(folder)
    if folder_data is None:
        # 此文件夹从未检查过时
        folder_data = {}
        for dirpath, dirnames, filenames in os.walk(folder):
            for file in filenames:
                basename, ext = os.path.splitext(file)
                if ext in SUB_EXTENSIONS:
                    match_id = get_id(basename)
                    if match_id:
                        folder_data[match_id.upper()] = os.path.join(dirpath, file)
        _sub_files[folder] = folder_data
    sub_file = folder_data.get(dvdid.upper())
    return sub_file


if __name__ == "__main__":
    p = "C:/Windows\\System32//PerceptionSimulation\\..\\Assets\\/ClosedHand.png"
    print(get_remaining_path_len(p))
