"""用来组织不需要依赖任何自定义类型的功能函数"""
import os
import re
import sys


__all__ = ['mei_path']


_special_chars_map = {i: '\\' + chr(i) for i in b'()[]{}?*+|^$\\.'}
def re_escape(s: str) -> str:
    """用来对字符串进行转义，以将转义后的字符串用于构造正则表达式"""
    pattern = s.translate(_special_chars_map)
    return pattern


def mei_path(path):
    """获取一个随代码打包的文件在解压后的路径"""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, path)
    else:
        return path


def strftime_to_minutes(s: str) -> int:
    """将HH:MM:SS或MM:SS的时长转换为分钟数返回

    Args:
        s (str): HH:MM:SS or MM:SS

    Returns:
        [int]: 取整后的分钟数
    """
    items = list(map(int, s.split(':')))
    if len(items) == 2:
        minutes = items[0] + round(items[1]/60)
    elif len(items) == 3:
        minutes = items[0] * 60 + items[1] + round(items[2]/60)
    else:
        logger.error(f"无法将字符串'{s}'转换为分钟")
        return
    return minutes
