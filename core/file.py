"""与文件相关的各类功能"""
import os
import re
import sys
import ctypes
import logging
from sys import platform
from typing import List

__all__ = ['scan_movies', 'get_fmt_size', 'get_remaining_path_len', 'replace_illegal_chars', 'get_failed_when_scan', 'find_subtitle_in_dir']


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.avid import *
from core.lib import re_escape
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
    failed_path_ls = []
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames.copy():
            if name.startswith('.') or name in cfg.File.ignore_folder:
                dirnames.remove(name)
        match_videos, unmatch_videos = {}, {}
        for file in filenames:
            ext = os.path.splitext(file)[1].lower()
            if ext in cfg.File.media_ext:
                fullpath = os.path.join(dirpath, file)
                dvdid = get_id(file)
                cid = get_cid(fullpath)
                # 如果文件名能匹配到cid，那么将cid视为有效id，因为此时dvdid多半是错的
                avid = cid if cid else dvdid
                if avid:
                    match_videos[fullpath] = avid
                    dic.setdefault(avid, []).append(fullpath)
                else:
                    unmatch_videos[fullpath] = None
        # 如果一个文件夹内有视频能匹配到番号，同时也有视频无法匹配到番号，则后者很可能是广告
        match_cnt, unmatch_cnt = len(match_videos), len(unmatch_videos)
        if match_cnt == 0:
            # 所有视频都没有匹配到番号，则尝试从文件夹寻找番号并作为所有视频的结果
            dvdid = get_id(dirpath)
            if dvdid:
                for fullpath in unmatch_videos.keys():
                    dic.setdefault(dvdid, []).append(fullpath)
            else:
                for fullpath in unmatch_videos.keys():
                    failed_path_ls.append(fullpath)
                    logger.error(f"无法提取影片番号: '{fullpath}'")
        else:
            if unmatch_cnt > 0:
                for fullpath in unmatch_videos.keys():
                    filesize = os.path.getsize(fullpath)
                    if filesize < cfg.File.ignore_video_file_less_than:
                        logger.debug(f"忽略匹配不到番号的小文件: '{fullpath}'")
                    else:
                        failed_path_ls.append(fullpath)
                        logger.error(f"无法提取影片番号: '{fullpath}'")
    for fullpath in failed_path_ls:
        fail = Movie('无法识别番号')
        fail.files = [fullpath]
        failed_items.append(fail)
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


def is_remote_drive(path: str):
    """判断一个路径是否为远程映射到本地"""
    #TODO: 当前仅支持Windows平台
    DRIVE_REMOTE = 0x4
    drive = os.path.splitdrive(os.path.abspath(path))[0] + os.sep
    result = ctypes.windll.kernel32.GetDriveTypeW(drive)
    return result == DRIVE_REMOTE


def get_remaining_path_len(path):
    """计算当前系统支持的最大路径长度与给定路径长度的差值"""
    #TODO: 支持不同的操作系统
    fullpath = os.path.abspath(path)
    # Windows: If the length exceeds ~256 characters, you will be able to see the path/files via Windows/File Explorer, but may not be able to delete/move/rename these paths/files
    if cfg.NamingRule.calc_path_len_by_byte == 'auto':
        is_remote = is_remote_drive(path)
        logger.debug(f"目标路径{['不是', '是'][is_remote]}远程文件系统")
        cfg.NamingRule.calc_path_len_by_byte = is_remote
    length = len(fullpath.encode('utf-8')) if cfg.NamingRule.calc_path_len_by_byte else len(fullpath)
    remaining = cfg.NamingRule.max_path_len - length
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
