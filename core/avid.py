"""获取和转换影片的各类番号（DVD ID, DMM cid, DMM pid）"""
import os
import re


def get_id(filepath: str) -> str:
    """从给定的文件路径中提取番号（DVD ID）"""
    # 通常是接收文件的路径，当然如果是普通字符串也可以
    filepath_lc = filepath.lower()
    if 'fc2' in filepath_lc:
        # 根据FC2 Club的影片数据，FC2编号为5-7个数字
        match = re.search(r'fc2[^a-z\d]{0,5}(ppv[^a-z\d]{0,5})?(\d{5,7})', filepath, re.I)
        if match:
            return 'FC2-' + match.group(2)
    # 如果最后仍然匹配不了番号，则尝试使用文件所在文件夹的名字去匹配
    if os.path.isfile(filepath):
        norm = os.path.normpath(filepath)
        folder = norm.split(os.sep)[-2]
        return get_id(folder)
    return ''


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    avid = get_id('FC2-123456')
    print(avid)
