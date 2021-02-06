"""用于辅助翻译genre列表、检查是否有更新的脚本"""
# - 为了使生成的NFO信息在最终呈现时便于理解、保持多个站点具有一致的分类规则，对各个网站的影片分类（genre）进行翻译
# - 本项目计划对所有提供影片分类信息的的站点，都维护一份对应的genre的翻译列表
# - 本脚本用来抓取各个网站的genre并生成csv数据，经人工校对后作为最终的翻译数据（必要时结合一些搜索的信息）
#   如果你觉得某些词汇有更好的翻译，欢迎发issue或者PR一起讨论和改进

# 为了便于对比和维护，以及尽可能保持各个站点间相同含义的genre具有一致的翻译，作以下约定：
# 1. 数据文件按照原genre作字符串升序排序
# 2. 在准确的前提下尽可能保持译文的简短
# 3. 网站上的部分genre标签并不适合写入nfo（如'高清'），这些标签的译文留空
#    程序会自动从抓取的标签中删除它们，不再写入nfo
# 4. 对于部分不直观的翻译或者被设置为删除的标签，应当在csv的note列中说明这样做的原因

import os
import sys
import csv


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import *
from core.config import cfg


def retrive_tag_data(genre_tags, record):
    """从各个a标签中获取genre id, url, 文本"""
    for tag in genre_tags:
        url = tag.get('href')
        id = url.split('/')[-1]
        name = tag.text.strip()
        if id in record:
            record[id].append(name)
        else:
            record[id] = [url, name]


def get_javbus_genre():
    """获取JavBus的genre各语言对照列表"""
    record = {}   # {id: [cn_url, zh_tw, ja, en]}
    base_url = cfg.ProxyFree.javbus
    zh_tw = get_html(f'{base_url}/genre')
    ja = get_html(f'{base_url}/ja/genre')
    en = get_html(f'{base_url}/en/genre')
    for html in [zh_tw, ja, en]:
        genre_tags = html.xpath("//a[@class='col-lg-2 col-md-2 col-sm-3 col-xs-6 text-center']")
        retrive_tag_data(genre_tags, record)
    # 将相关数据进行结构化后返回
    data = {
        'site_name': 'javbus',
        'header': ['id', 'url', 'zh_tw', 'ja', 'en'],
        'record': record
    }
    return data


def get_javbus_genre_uncensored():
    """获取JavBus无码影片的genre各语言对照列表"""
    # 由于JavBus有码和无码的genre id有重复（但是代表的分类不同），所以二者无法组合成一个数据文件
    record = {}   # {id: [cn_url, zh_tw, ja, en]}
    base_url = cfg.ProxyFree.javbus
    zh_tw = get_html(f'{base_url}/uncensored/genre')
    ja = get_html(f'{base_url}/ja/uncensored/genre')
    en = get_html(f'{base_url}/en/uncensored/genre')
    for html in [zh_tw, ja, en]:
        genre_tags = html.xpath("//a[@class='col-lg-2 col-md-2 col-sm-3 col-xs-6 text-center']")
        retrive_tag_data(genre_tags, record)
    # 将相关数据进行结构化后返回
    data = {
        'site_name': 'javbus_uncensored',
        'header': ['id', 'url', 'zh_tw', 'ja', 'en'],
        'record': record
    }
    return data


def get_javdb_genre():
    """获取JavDB的genre各语言对照列表"""
    # JavDB的genre id有重复且各子站内的含义不同，但是'tags?c2=1'的形式不重复，所以可以合并成一个数据文件
    # FC2 部分的数据需要登录，待实现FC2的解析功能时一并添加
    record = {}
    base_url = cfg.ProxyFree.javdb
    subsite_urls = {
        'normal':     ['/tags?locale=zh', '/tags?locale=en'],
        'uncensored': ['/tags/uncensored?locale=zh', '/tags/uncensored?locale=en'],
        'western':    ['/tags/western?locale=zh', '/tags/western?locale=en']
    }
    for subsite, urls in subsite_urls.items():
        zh_tw = get_html(base_url + urls[0])
        en = get_html(base_url + urls[1])
        for html in [zh_tw, en]:
            genre_tags = html.xpath("//span[@class='tag_labels']/a")
            retrive_tag_data(genre_tags, record)
    # 移除分类中的c9:'筛选', c10:'年份', c11:'时长'
    for id, _ in record.copy().items():
        catelog = id.split('?')[1].split('=')[0]   # e.g. tags?c11=2021
        if catelog in ['c9', 'c10', 'c11']:
            del record[id]
    # 将相关数据进行结构化后返回
    data = {
        'site_name': 'javdb',
        'header': ['id', 'url', 'zh_tw', 'en'],
        'record': record
    }
    return data


def write_csv(data):
    """将genre按照中文翻译排序后写入csv文件"""
    # data格式: {'site_name': name, 'header': ['id', 'url', 'zh_tw'...], 'record': {id1: [ls1], id2: [ls2]...}}
    record = data['record']
    csv_name = f"data/genre_{data['site_name']}.csv"
    csv_header = data['header'] + ['translate', 'note']
    # p[1][1] 必须是最接近最终翻译文本的那一列（如繁体中文）
    sort_record = {k: v for k, v in sorted(record.items(), key=lambda p: p[1][1])}
    with open(csv_name, 'wt', encoding='utf-8-sig', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(csv_header)
        for id, genres in sort_record.items():
            writer.writerow([id] + genres)


if __name__ == "__main__":
    write_csv(get_javdb_genre())
