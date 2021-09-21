import os
import sys
from urllib.parse import urlsplit


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



def test_crawler(crawler_params):
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
        if k in ['score', 'magnet']:
            assert bool(v) == bool(local_vars.get(k, None))
        elif k == 'preview_video' and scraper in ['airav', 'javdb']:
            assert bool(v) == bool(local_vars.get(k, None))
        # JavBus采用免代理域名时图片地址也会是免代理域名，因此只比较path部分即可
        elif k == 'cover' and scraper == 'javbus':
            assert urlsplit(v).path == urlsplit(local_vars.get(k, None)).path
        elif k == 'actress_pics' and scraper == 'javbus':
            local_tmp = online_tmp = {}
            local_pics = local_vars.get('actress_pics')
            if local_pics:
                local_tmp = {name: urlsplit(url).path for name, url in local_pics.items()}
            if v:
                online_tmp = {name: urlsplit(url).path for name, url in v.items()}
            assert local_tmp == online_tmp
        else:
            assert v == local_vars.get(k, None)
