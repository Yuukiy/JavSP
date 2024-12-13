"""调用抓取器抓取数据"""
import os
import sys


import pretty_errors
from tqdm import tqdm


pretty_errors.configure(display_link=True)


file_dir = os.path.dirname(__file__)
data_dir = os.path.abspath(os.path.join(file_dir, '../unittest/data'))
sys.path.insert(0, os.path.abspath(os.path.join(file_dir, '..')))
from javsp.datatype import MovieInfo


# 搜索抓取器并导入它们
all_crawler = {}
exclude_files = ['fc2fan']
for file in os.listdir('../javsp/web'):
    name, ext = os.path.splitext(file)
    if ext == '.py' and name not in exclude_files:
        modu = 'javsp.web.' + name
        __import__(modu)
        if hasattr(sys.modules[modu], 'parse_data'):
            parser = getattr(sys.modules[modu], 'parse_data')
            all_crawler[name] = parser


# 生成本地的测试数据作为测试数据，以确保未来对抓取器进行修改时，不会影响到现有功能
def call_crawlers(dvdid_list: list, used_crawlers=None):
    """抓取影片数据

    Args:
        dvdid_list (list): 影片番号的列表
        crawlers (list[str], optional): 要使用的抓取器，未指定时将使用全部抓取器
    """
    if used_crawlers:
        crawlers = {i:all_crawler[i] for i in used_crawlers}
    else:
        crawlers = all_crawler
    outer_bar = tqdm(dvdid_list, desc='抓取影片数据', leave=False)
    for avid in outer_bar:
        success, fail = [], []
        outer_bar.set_description(f'抓取影片数据: {avid}')
        inner_bar = tqdm(crawlers.items(), desc='抓取器', leave=False)
        for name, parser in inner_bar:
            inner_bar.set_description(f'正在抓取{name}'.rjust(10+len(avid)))
            # 每次都会创建一个全新的实例，所以不同抓取器的结果之间不会有影响
            if name != 'fanza':
                movie = MovieInfo(avid)
            else:
                movie = MovieInfo(cid=avid)
            try:
                parser(movie)
                path = f"{data_dir}{os.sep}{avid} ({name}).json"
                movie.dump(path)
                success.append(name)
            except:
                fail.append(name)
        out = "{} 抓取完成: 成功{}个 {}; 失败{}个 {}".format(avid, len(success), ' '.join(success), len(fail), ' '.join(fail))
        tqdm.write(out)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 带参数调用时，将参数全部视作番号并调用所有抓取器抓取数据
        call_crawlers(sys.argv[1:])
    else:
        user_in = input('请输入要抓取数据的影片番号: ')
        dvdid_list = user_in.split()
        # 提示选择要使用的抓取器
        names = list(all_crawler.keys())
        for i in range(len(names)):
            print(f"{i+1}. {names[i]}", end='  ')
        user_in2 = input('\n请选择要使用的抓取器（回车表示全部使用）: ')
        if user_in2:
            items = user_in2.split()
            indexes = [int(i)-1 for i in items if i.isdigit()]
            valid_indexes = [i for i in indexes if i < len(names)]
            used = [names[i] for i in valid_indexes]
        else:
            used = names
        # 开始抓取数据
        call_crawlers(dvdid_list, used)
