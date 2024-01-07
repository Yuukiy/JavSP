import os
import sys
import logging
import requests
from urllib.parse import urlsplit


file_dir = os.path.dirname(__file__)
data_dir = os.path.join(file_dir, 'data')
sys.path.insert(0, os.path.abspath(os.path.join(file_dir, '..')))

from core.datatype import MovieInfo
from web.exceptions import CrawlerError, SiteBlocked


logger = logging.getLogger(__name__)


def test_crawler(crawler_params):
    """包装函数，便于通过参数判断测试用例生成，以及负责将参数解包后进行实际调用"""
    # crawler_params: ('ABC-123', 'javlib', 'path_to_local_json')
    # TODO: 在Github actions环境中总是无法通过Cloudflare的检测，因此暂时忽略需要过验证站点的失败项
    try:
        site, params = crawler_params[1], crawler_params[:2]
        compare(*crawler_params)
    except requests.exceptions.ReadTimeout:
        logger.warning(f"{site} 连接超时: {params}")
    except Exception as e:
        if os.getenv('GITHUB_ACTIONS') and (site in ['javdb', 'javlib', 'airav']):
            logger.debug(f'检测到Github actions环境，已忽略测试失败项: {params}')
            logger.exception(e)
        else:
            raise

def compare(avid, scraper, file):
    """从本地的数据文件生成Movie实例，并与在线抓取到的数据进行比较"""
    local = MovieInfo(from_file=file)
    if scraper != 'fanza':
        online = MovieInfo(avid)
    else:
        online = MovieInfo(cid=avid)
    # 导入抓取器模块
    scraper_mod = 'web.' + scraper
    __import__(scraper_mod)
    mod = sys.modules[scraper_mod]
    if hasattr(mod, 'parse_clean_data'):
        parse_data = getattr(mod, 'parse_clean_data')
    else:
        parse_data = getattr(mod, 'parse_data')

    try:
        parse_data(online)
    except SiteBlocked as e:
        logger.warning(e)
        return
    except (CrawlerError, requests.exceptions.ReadTimeout) as e:
        logger.info(e)

    try:
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
                local_pics = local_vars.get(k)
                if local_pics:
                    local_tmp = {name: urlsplit(url).path for name, url in local_pics.items()}
                if v:
                    online_tmp = {name: urlsplit(url).path for name, url in v.items()}
                assert local_tmp == online_tmp
            elif k == 'preview_pics' and scraper == 'javbus':
                local_pics = local_vars.get(k)
                if local_pics:
                    local_tmp = [urlsplit(i).path for i in local_pics]
                if v:
                    online_tmp = [urlsplit(i).path for i in v]
                assert local_tmp == online_tmp
            # 对顺序没有要求的list型字段，比较时也应该忽略顺序信息
            elif k in ['genre', 'genre_id', 'genre_norm', 'actress']:
                if isinstance(v, list):
                    loc_v = local_vars.get(k)
                    if loc_v is None:
                        loc_v = []
                    assert sorted(v) == sorted(loc_v)
                else:
                    assert v == local_vars.get(k, None)
            else:
                assert v == local_vars.get(k, None)
    except AssertionError:
        # 本地运行时更新已有的测试数据，方便利用版本控制系统检查差异项
        if not os.getenv('GITHUB_ACTIONS'):
            online.dump(file)
        raise
    except Exception as e:
        logger.error(e)
        raise
