import os
import re
import sys
from glob import glob

import pretty_errors
from tqdm import tqdm

file_dir = os.path.dirname(__file__)
data_dir = os.path.join(file_dir, 'data')
sys.path.insert(0, os.path.abspath(os.path.join(file_dir, '..')))

from core.datatype import MovieInfo


scrapers = ('javdb', 'javbus', 'javlib', 'avsox')
pretty_errors.configure(display_link=True)


def create_local_data(dvdid_list: list):
    """生成本地的测试数据作为测试数据，以确保未来对抓取器进行修改时，不会影响到现有功能"""
    mods = [f'web.{name}' for name in scrapers]
    for i in mods:
        __import__(i)
    outer_bar = tqdm(dvdid_list, desc='抓取影片数据', leave=False)
    for dvdid in outer_bar:
        success, fail = [], []
        outer_bar.set_description(f'抓取影片数据: {dvdid}')
        inner_bar = tqdm(mods, desc='抓取器', leave=False)
        for mod in inner_bar:
            mod_name = scrapers[mods.index(mod)]
            inner_bar.set_description(f'正在抓取{mod_name}'.rjust(10+len(dvdid)))
            # 每次都会创建一个全新的实例，所以不同抓取器的结果之间不会有影响
            movie = MovieInfo(dvdid)
            parse_data = getattr(sys.modules[mod], 'parse_data')
            try:
                parse_data(movie)
                path = f"{data_dir}{os.sep}{dvdid} ({mod_name}).json"
                movie.dump(path)
                success.append(mod_name)
            except Exception as e:
                fail.append(mod_name)
        out = "{} 抓取完成: 成功{}个 {}; 失败{}个 {}".format(dvdid, len(success), ' '.join(success), len(fail), ' '.join(fail))
        tqdm.write(out)
    return


def compare(dvdid, scraper, file):
    """从本地的数据文件生成Movie实例，并与在线抓取到的数据进行比较"""
    local = MovieInfo(from_file=file)
    online = MovieInfo(dvdid)
    parse_data = getattr(sys.modules[f'web.{scraper}'], 'parse_data')
    parse_data(online)
    # 解包数据再进行比较，以便测试不通过时快速定位不相等的键值
    local_vars = vars(local)
    online_vars = vars(online)
    for k, v in online_vars.items():
        assert v == local_vars.get(k, None)


def test_auto_compare():
    """根据测试数据文件夹中的文件，爬取对应的在线数据进行比较"""
    mods = [f'web.{name}' for name in scrapers]
    for i in mods:
        __import__(i)
    data_files = glob(data_dir + os.sep + '*.json')
    print('')   # 打印空行，避免与pytest的输出同行显示
    for file in data_files:
        basename = os.path.basename(file)
        match = re.match(r"([-\w]+) \((\w+)\)", basename, re.I)
        if match:
            avid, scraper = match.groups()
            print(f'Comparing {avid} with {scraper} scraper...')
            compare(avid, scraper, file)


if __name__ == "__main__":
    create_local_data(['IPX-177'])
