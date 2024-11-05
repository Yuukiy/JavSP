"""获取和转换影片的各类番号（DVD ID, DMM cid, DMM pid）"""
import os
import re
from pathlib import Path


__all__ = ['get_id', 'get_cid', 'guess_av_type']


from javsp.config import Cfg

def get_id(filepath_str: str) -> str:
    """从给定的文件路径中提取番号（DVD ID）"""
    filepath = Path(filepath_str)
    # 通常是接收文件的路径，当然如果是普通字符串也可以
    ignore_pattern = re.compile('|'.join(Cfg().scanner.ignored_id_pattern))
    norm = ignore_pattern.sub('', filepath.stem).upper()
    if 'FC2' in norm:
        # 根据FC2 Club的影片数据，FC2编号为5-7个数字
        match = re.search(r'FC2[^A-Z\d]{0,5}(PPV[^A-Z\d]{0,5})?(\d{5,7})', norm, re.I)
        if match:
            return 'FC2-' + match.group(2)
    elif 'HEYDOUGA' in norm:
        match = re.search(r'(HEYDOUGA)[-_]*(\d{4})[-_]0?(\d{3,5})', norm, re.I)
        if match:
            return '-'.join(match.groups())
    elif 'GETCHU' in norm:
        match = re.search(r'GETCHU[-_]*(\d+)', norm, re.I)
        if match:
            return 'GETCHU-' + match.group(1)
    elif 'GYUTTO' in norm:
        match = re.search(r'GYUTTO-(\d+)', norm, re.I)
        if match:
            return 'GYUTTO-' + match.group(1)
    elif '259LUXU' in norm: # special case having form of '259luxu'
        match = re.search(r'259LUXU-(\d+)', norm, re.I)
        if match:
            return '259LUXU-' + match.group(1)

    else:
        # 先尝试移除可疑域名进行匹配，如果匹配不到再使用原始文件名进行匹配
        no_domain = re.sub(r'\w{3,10}\.(COM|NET|APP|XYZ)', '', norm, flags=re.I)
        if no_domain != norm:
            avid = get_id(no_domain)
            if avid:
                return avid
        # 匹配缩写成hey的heydouga影片。由于番号分三部分，要先于后面分两部分的进行匹配
        match = re.search(r'(?:HEY)[-_]*(\d{4})[-_]0?(\d{3,5})', norm, re.I)
        if match:
            return 'heydouga-' + '-'.join(match.groups())
        # 匹配片商 MUGEN 的奇怪番号。由于MK3D2DBD的模式，要放在普通番号模式之前进行匹配
        match = re.search(r'(MKB?D)[-_]*(S\d{2,3})|(MK3D2DBD|S2M|S2MBD)[-_]*(\d{2,3})', norm, re.I)
        if match:
            if match.group(1) is not None:
                avid = match.group(1) + '-' + match.group(2)
            else:
                avid = match.group(3) + '-' + match.group(4)
            return avid
        # 匹配IBW这样带有后缀z的番号
        match = re.search(r'(IBW)[-_](\d{2,5}z)', norm, re.I)
        if match:
            return match.group(1) + '-' + match.group(2)
        # 普通番号，优先尝试匹配带分隔符的（如ABC-123）
        match = re.search(r'([A-Z]{2,10})[-_](\d{2,5})', norm, re.I)
        if match:
            return match.group(1) + '-' + match.group(2)
        # 普通番号，运行到这里时表明无法匹配到带分隔符的番号
        # 先尝试匹配东热的red, sky, ex三个不带-分隔符的系列
        # （这三个系列已停止更新，因此根据其作品编号将数字范围限制得小一些以降低误匹配概率）
        match = re.search(r'(RED[01]\d\d|SKY[0-3]\d\d|EX00[01]\d)', norm, re.I)
        if match:
            return match.group(1)
        # 然后再将影片视作缺失了-分隔符来匹配
        match = re.search(r'([A-Z]{2,})(\d{2,5})', norm, re.I)
        if match:
            return match.group(1) + '-' + match.group(2)
    # 尝试匹配TMA制作的影片（如'T28-557'，他家的番号很乱）
    match = re.search(r'(T[23]8[-_]\d{3})', norm)
    if match:
        return match.group(1)
    # 尝试匹配东热n, k系列
    match = re.search(r'(N\d{4}|K\d{4})', norm, re.I)
    if match:
        return match.group(1)
    # 尝试匹配纯数字番号（无码影片）
    match = re.search(r'(\d{6}[-_]\d{2,3})', norm)
    if match:
        return match.group(1)
    # 如果还是匹配不了，尝试将')('替换为'-'后再试，少部分影片的番号是由')('分隔的
    if ')(' in norm:
        avid = get_id(norm.replace(')(', '-'))
        if avid:
            return avid
    # 如果最后仍然匹配不了番号，则尝试使用文件所在文件夹的名字去匹配
    
    if filepath.parent.name != '': # haven't reach '.' or '/'
        return get_id(filepath.parent.name)
    else:
        return ''


CD_POSTFIX = re.compile(r'([-_]\w|cd\d)$')
def get_cid(filepath: str) -> str:
    """尝试将给定的文件名匹配为CID（Content ID）"""
    basename = os.path.splitext(os.path.basename(filepath))[0]
    # 移除末尾可能带有的分段影片序号
    possible = CD_POSTFIX.sub('', basename)
    # cid只由数字、小写字母和下划线组成
    match = re.match(r'^([a-z\d_]+)$', possible, re.A)
    if match:
        possible = match.group(1)
        if '_' not in possible:
            # 长度为7-14的cid就占了约99.01%. 最长的cid为24，但是长为20-24的比例不到十万分之五
            match = re.match(r'^[a-z\d]{7,19}$', possible)
            if match:
                return possible
        else:
            # 绝大多数都只有一个下划线（只有约万分之一带有两个下划线）
            match2 = re.match(r'''^h_\d{3,4}[a-z]{1,10}\d{2,5}[a-z\d]{0,8}$  # 约 99.17%
                                |^\d{3}_\d{4,5}$                            # 约 0.57%
                                |^402[a-z]{3,6}\d*_[a-z]{3,8}\d{5,6}$       # 约 0.09%
                                |^h_\d{3,4}wvr\d\w\d{4,5}[a-z\d]{0,8}$      # 约 0.06%
                                 $''', possible, re.VERBOSE)
            if match2:
                return possible
    return ''


def guess_av_type(avid: str) -> str:
    """识别给定的番号所属的分类: normal, fc2, cid"""
    match = re.match(r'^FC2-\d{5,7}$', avid, re.I)
    if match:
        return 'fc2'
    match = re.match(r'^GETCHU-(\d+)',avid,re.I)
    if match:
        return 'getchu'
    match = re.match(r'^GYUTTO-(\d+)',avid,re.I)
    if match:
        return 'gyutto'
    # 如果传入的avid完全匹配cid的模式，则将影片归类为cid
    cid = get_cid(avid)
    if cid == avid:
        return 'cid'
    # 以上都不是: 默认归类为normal
    return 'normal'


if __name__ == "__main__":
    print(get_id('FC2-123456/Unknown.mp4'))
