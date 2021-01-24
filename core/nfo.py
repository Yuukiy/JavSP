"""与操作nfo文件相关的功能"""
import os
import sys
from lxml.etree import tostring
from lxml.builder import E


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.datatype import MovieInfo


def write_nfo(info: MovieInfo):
    """将存储了影片信息的'info'写入到nfo文件中"""
    # NFO spec: https://kodi.wiki/view/NFO_files/Movies
    nfo = E.movie()
    nfo.append(E.title(info.title))

    # TODO: 只有去除了标题中的重复女优名或者进行了翻译时需要使用原始标题
    # nfo.append(E.originaltitle('原始标题'))

    # Kodi的文档中评分支持多个来源，但经测试，添加了多个评分时Kodi也只显示了第一个评分
    # 由于目前也只有一个评分来源（JavLibrary），因此只使用单个评分
    if info.score:
        nfo.append(E.rating(info.score))

    # 目前没有合适的字段用于outline（一行简短的介绍），力求不在nfo中写入冗余的信息，因此不添加outline标签
    # 而且无论是Kodi还是Jellyfin中都没有找到实际显示outline的位置；tagline倒是都有发现

    # TODO: plot：可以有多行的详细介绍，待完成arzon抓取功能以后再添加

    # 目前没有合适的字段用于tagline（一行简短的介绍）

    nfo.append(E.runtime(info.duration))

    # thumb字段可以用来为不同的aspect强制指定图片文件名
    # 例如可以将'NoPoster.jpg'指定给'ABC-123.mp4'，而不必按照poster文件名的常规命名规则来

    # fanart通常也是通过给fanart图片命名来匹配
    nfo.append(E.mpaa('NC-17'))     # 分级

    # 将DVD ID和CID写入到uniqueid字段
    if info.dvdid:
        nfo.append(E.uniqueid(info.dvdid, type='num', defult='true'))
    if info.cid:
        nfo.append(E.uniqueid(info.cid, type='cid'))

    # 写入genre分类。在Jellyfin上，只有genre可以直接跳转，tag不可以
    # 也同时写入tag。TODO: 还没有研究tag和genre在Kodi上的区别
    for i in info.genre:
        nfo.append(E.genre(i))
    for i in info.genre:
        nfo.append(E.tag(i))

    # Kodi上的country字段没说必须使用国家的代码（比如JP），所以目前暂定直接使用国家名
    nfo.append(E.country('日本'))

    if info.serial:
        # 部分影片有系列。set字段支持overview作为介绍，但是目前没发现有地方可以获取到系列的介绍
        nfo.append(E.set(E.name(info.serial)))

    if info.director:
        nfo.append(E.directr(info.director))

    # 发行日期。文档中关于'year'字段的说明: Do not use. Use <premiered> instead
    nfo.append(E.premiered('2021-01-24'))

    # 原文是 Production studio: 因此这里写入的是影片制作商
    nfo.append(E.studio(info.producer))

    # trailer 预告片
    if info.preview_video:
        nfo.append(E.trailer(info.preview_video))

    # TODO: fileinfo 字段，看起来可以给定字幕语言和类型，留待开发

    # 写入演员名。 TODO: Kodi支持用thumb显示演员头像，但是需要爬取数据时把演员头像地址也爬一下
    for i in info.actress:
        nfo.append(E.actor(E.name(i)))

    with open(f'{info.dvdid}.nfo', 'wt', encoding='utf-8') as f:
        f.write(tostring(nfo, encoding='unicode', pretty_print=True,
                         doctype='<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'))


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    info = MovieInfo(from_file=R'unittest\data\IPX-177 (javbus).json')
    write_nfo(info)
