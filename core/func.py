"""供其他模块使用（但是又不知道放哪里）的功能函数"""
import os
import re
import time
import logging

__all__ = ['remove_trail_actor_in_title', 'shutdown', 'CLEAR_LINE']


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
