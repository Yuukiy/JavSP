"""供其他模块使用（但是又不知道放哪里）的功能函数"""
import os
import re
import sys
import time
import logging
from packaging import version
from colorama import Fore, Style

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import *


__all__ = ['remove_trail_actor_in_title', 'shutdown', 'CLEAR_LINE', 'check_update']


CLEAR_LINE = '\r\x1b[K'
logger = logging.getLogger(__name__)


def remove_trail_actor_in_title(title:str, actors:list) -> str:
    """寻找并移除标题尾部的女优名"""
    # 目前使用分隔符白名单来做检测（担心按Unicode范围匹配误伤太多），考虑尽可能多的分隔符
    delimiters = '-xX &·,;　＆・，；'
    pattern = f"^(.*?)([{delimiters}]{{1,3}}({'|'.join(actors)}))+$"
    # 使用match而不是sub是为了将替换掉的部分写入日志
    match = re.match(pattern, title)
    if match:
        logger.debug(f"移除标题尾部的女优名: '{match.group(1)}'[{match.group(2)}]")
        return match.group(1)
    else:
        return title


def shutdown(timeout=120):
    """关闭计算机"""
    try:
        for i in reversed(range(timeout)):
            print(CLEAR_LINE + f"JavSP整理完成，将在 {i} 秒后关机。按'Ctrl+C'取消", end='')
            time.sleep(1)
        logger.info('整理完成，自动关机')
        #TODO: 当前仅支持Windows平台
        os.system('shutdown -s')
    except KeyboardInterrupt:
        return


def get_actual_width(mix_str: str) -> int:
    """给定一个中英混合的字符串，返回实际的显示宽度"""
    width = len(mix_str)
    for c in mix_str:
        if u'\u4e00' <= c <= u'\u9fa5':
            width += 1
    return width


def align_to_width(mix_str: str, width: int) -> str:
    """给定一个中英混合的字符串，将其实际显示宽度对齐到指定的值"""
    actual_width = get_actual_width(mix_str)
    aligned_str = mix_str + ' ' * (width-actual_width)
    return aligned_str


def check_update(local_version='v0.0', print=print):
    """检查是否有新版本"""
    api_url = 'https://api.github.com/repos/Yuukiy/JavSP/releases/latest'
    release_url = 'https://github.com/Yuukiy/JavSP/releases/latest'
    print('正在检查更新...', end='')
    try:
        data = request_get(api_url, timeout=3).json()
        print(CLEAR_LINE, end='')
    except:
        print(CLEAR_LINE + '检查更新失败，请前往以下地址查看是否有新版本: ')
        print('  ' + release_url + '\n')
        return
    latest_version = data['tag_name']
    if version.parse(local_version) < version.parse(latest_version):
        # 提取changelog消息
        lines = data['body'].split('\r\n')
        changelog = []
        for line in lines:
            if line.startswith('## '):
                changelog.append(Style.BRIGHT + line[3:] + Style.RESET_ALL)
            elif line.startswith('- '):
                changelog.append(line)
        display_width = max([get_actual_width(i) for i in lines]) + 5
        display_width = max(display_width, len(release_url))
        # 输出更新信息
        print('=' * display_width)
        title = '↓ Jav Scraper Package 新版本: ' + latest_version + ' ↓'
        print(Fore.LIGHTCYAN_EX + title.center(display_width) + Style.RESET_ALL)
        print(release_url.center(display_width))
        print('-' * display_width)
        print('\n'.join(changelog))
        print('=' * display_width)
        print('')


if __name__ == "__main__":
    check_update()
