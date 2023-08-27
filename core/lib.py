"""用来组织不需要依赖任何自定义类型的功能函数"""
import os
import re
import sys


__all__ = ['re_escape', 'mei_path', 'strftime_to_minutes', 'detect_special_attr']


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


_PATTERN = re.compile(r'(uncensor(ed)?[- _\s]*leak(ed)?|[无無][码碼](流出|破解))', flags=re.I)
def detect_special_attr(filepath: str) -> str:
    """通过文件名检测影片是否有特殊属性（内嵌字幕、无码流出/破解）

    Returns:
        [str]: '', 'U', 'C', 'UC'
    """
    result = ''
    base = os.path.splitext(os.path.basename(filepath))[0].upper()
    # 尝试使用正则匹配
    match = _PATTERN.search(base)
    if match:
        result += 'U'
    # 尝试匹配-C/-U/-UC后缀的影片
    postfix = base.split('-')[-1]
    if postfix in ('U', 'C', 'UC'):
        result += postfix
    # 最终格式化
    result = ''.join(sorted(result, reverse=True))
    return result


if __name__ == "__main__":
    print(detect_special_attr('STARS-225_UNCENSORED_LEAKED.mp4'))
