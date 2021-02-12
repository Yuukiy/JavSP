"""调用抓取器抓取数据"""
import os
import sys


import pretty_errors
from tqdm import tqdm


pretty_errors.configure(display_link=True)


file_dir = os.path.dirname(__file__)
data_dir = os.path.abspath(os.path.join(file_dir, '../unittest/data'))
sys.path.insert(0, os.path.abspath(os.path.join(file_dir, '..')))
from core.datatype import MovieInfo


# 搜索抓取器并导入它们
all_crawler = []
exclude_files = ('base', 'proxyfree', 'fc2fan')
for file in os.listdir('web'):
    name, ext = os.path.splitext(file)
    if ext == '.py' and name not in exclude_files:
        all_crawler.append('web.' + name)
for i in all_crawler:
    __import__(i)


# 生成本地的测试数据作为测试数据，以确保未来对抓取器进行修改时，不会影响到现有功能
def call_crawlers(dvdid_list: list, crawlers=None):
    """抓取影片数据

    Args:
        dvdid_list (list): 影片番号的列表
        crawlers (list[str], optional): 要使用的抓取器，未指定时将使用全部抓取器
    """
    if crawlers:
        crawlers = [i for i in crawlers if i in all_crawler]
    else:
        crawlers = all_crawler
    outer_bar = tqdm(dvdid_list, desc='抓取影片数据', leave=False)
    for avid in outer_bar:
        success, fail = [], []
        outer_bar.set_description(f'抓取影片数据: {avid}')
        inner_bar = tqdm(crawlers, desc='抓取器', leave=False)
        for scrp in inner_bar:
            scrp_name = scrp.split('.')[1]
            inner_bar.set_description(f'正在抓取{scrp_name}'.rjust(10+len(avid)))
            # 每次都会创建一个全新的实例，所以不同抓取器的结果之间不会有影响
            if scrp_name != 'fanza':
                movie = MovieInfo(avid)
            else:
                movie = MovieInfo(cid=avid)
            parse_data = getattr(sys.modules[scrp], 'parse_data')
            try:
                parse_data(movie)
                path = f"{data_dir}{os.sep}{avid} ({scrp_name}).json"
                movie.dump(path)
                success.append(scrp_name)
            except:
                fail.append(scrp_name)
        out = "{} 抓取完成: 成功{}个 {}; 失败{}个 {}".format(avid, len(success), ' '.join(success), len(fail), ' '.join(fail))
        tqdm.write(out)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        call_crawlers(sys.argv[1:])
    else:
        user_in = input('请输入要抓取数据的影片番号: ')
        dvdid_list = user_in.split()
        # 提示选择要使用的抓取器
        for i in range(len(all_crawler)):
            print(f"{i+1}. {all_crawler[i].split('.')[1]}", end='  ')
        user_in2 = input('\n请选择要使用的抓取器（回车表示全部使用）: ')
        if user_in2:
            used = []
            items = user_in2.split()
            for i in items:
                try:
                    index = int(i)-1
                    used.append(all_crawler[index])
                except:
                    pass
        else:
            used = all_crawler
        # 开始抓取数据
        call_crawlers(dvdid_list, used)
