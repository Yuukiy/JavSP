import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.javbus import *


data_dir = os.path.split(__file__)[0] + os.sep + 'data'


def compare(dvdid):
    """从本地的数据文件生成Movie实例，并与在线抓取到的数据进行比较"""
    path = data_dir + os.sep + f'{dvdid} (javbus).json'
    local = Movie(from_file=path)
    online = Movie(dvdid)
    parse_data(online)
    # 解包数据再进行比较，以便测试不通过时快速定位不相等的键值
    local_vars = vars(local)
    online_vars = vars(online)
    for k, v in online_vars.items():
        assert v == local_vars.get(k, None)


def test_case1():
    compare('IPX-177')
