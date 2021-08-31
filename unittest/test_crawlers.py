import os
import re
import sys
from glob import glob


file_dir = os.path.dirname(__file__)
data_dir = os.path.join(file_dir, 'data')
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



def test_prepare_compare(crawler_params):
    """包装函数，便于通过参数判断测试用例生成，以及负责将参数解包后进行实际调用"""
    compare(*crawler_params)


def compare(avid, scraper, file):
    """从本地的数据文件生成Movie实例，并与在线抓取到的数据进行比较"""
    local = MovieInfo(from_file=file)
    if scraper != 'fanza':
        online = MovieInfo(avid)
    else:
        online = MovieInfo(cid=avid)
    parse_data = getattr(sys.modules[f'web.{scraper}'], 'parse_data')
    parse_data(online)
    ## 取消下面两行注释可以用来更新已有的测试数据
    # online.dump(file)
    # return
    # 解包数据再进行比较，以便测试不通过时快速定位不相等的键值
    local_vars = vars(local)
    online_vars = vars(online)
    for k, v in online_vars.items():
        # 部分字段可能随时间变化，因此只要这些字段不是一方有值一方无值就行
        if k in ['score', 'magnet'] or (scraper in ['airav', 'javdb'] and k == 'preview_video'):
            assert bool(v) == bool(local_vars.get(k, None))
        else:
            assert v == local_vars.get(k, None)
