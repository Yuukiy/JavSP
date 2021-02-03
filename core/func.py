"""供其他模块使用（但是又不知道放哪里）的功能函数"""
import re
import logging


logger = logging.getLogger(__name__)


__all__ = ['remove_trail_actor_in_title']


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
