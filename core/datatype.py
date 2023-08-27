"""定义数据类型和一些通用性的对数据类型的操作"""
import os
import csv
import sys
import json
import logging
from functools import cached_property

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.lib import mei_path, detect_special_attr


logger = logging.getLogger(__name__)
filemove_logger = logging.getLogger('filemove')


class MovieInfo:
    def __init__(self, dvdid=None, /, *, cid=None, from_file=None):
        """
        Args:
            dvdid ([str], optional): 番号，要通过其他方式创建实例时此参数应留空
            from_file: 从指定的文件(json格式)中加载数据来创建实例
        """
        arg_count = len([i for i in [dvdid, cid, from_file] if i])
        if arg_count != 1:
            raise TypeError(f'Require 1 parameter but {arg_count} given')
        if isinstance(dvdid, Movie):
            self.dvdid = dvdid.dvdid
            self.cid = dvdid.cid
        else:
            self.dvdid = dvdid      # DVD ID，即通常的番号
            self.cid = cid          # DMM Content ID
        # 创建类的默认属性
        self.url = None             # 影片页面的URL
        self.plot = None            # 故事情节
        self.cover = None           # 封面图片（URL）
        self.big_cover = None       # 高清封面图片（URL）
        self.genre = None           # 影片分类的标签
        self.genre_id = None        # 影片分类的标签的ID，用于解决部分站点多个genre同名的问题，也便于管理多语言的genre
        self.genre_norm = None      # 统一后的影片分类的标签
        self.score = None           # 评分（10分制，为方便提取写入和保持统一，应以字符串类型表示）
        self.title = None           # 影片标题（不含番号）
        self.ori_title = None       # 原始影片标题，仅在标题被处理过时才对此字段赋值
        self.magnet = None          # 磁力链接
        self.serial = None          # 系列
        self.actress = None         # 出演女优
        self.actress_pics = None    # 出演女优的头像。单列一个字段，便于满足不同的使用需要
        self.director = None        # 导演
        self.duration = None        # 影片时长
        self.producer = None        # 制作商
        self.publisher = None       # 发行商
        self.uncensored = None      # 是否为无码影片
        self.publish_date = None    # 发布日期
        self.preview_pics = None    # 预览图片（URL）
        self.preview_video = None   # 预览视频（URL）

        if from_file:
            if os.path.isfile(from_file):
                self.load(from_file)
            else:
                raise TypeError(f"Invalid file path: '{from_file}'")

    def __str__(self) -> str:
        d = vars(self)
        return json.dumps(d, indent=2, ensure_ascii=False)

    def __repr__(self) -> str:
        if self.dvdid:
            expression = f"('{self.dvdid}')"
        else:
            expression = f"('cid={self.cid}')"
        return __class__.__name__ + expression

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def dump(self, filepath=None, crawler=None) -> None:
        if not filepath:
            id = self.dvdid if self.dvdid else self.cid
            if crawler:
                filepath = f'../unittest/data/{id} ({crawler}).json'
                filepath = os.path.join(os.path.dirname(__file__), filepath)
            else:
                filepath = id + '.json'
        with open(filepath, 'wt', encoding='utf-8') as f:
            f.write(str(self))

    def load(self, filepath) -> None:
        with open(filepath, 'rt', encoding='utf-8') as f:
            d = json.load(f)
        # 更新对象属性
        attrs = vars(self).keys()
        for k, v in d.items():
            if k in attrs:
                self.__setattr__(k, v)


class Movie:
    """用于关联影片文件的类"""
    def __init__(self, dvdid=None, /, *, cid=None) -> None:
        arg_count = len([i for i in (dvdid, cid) if i])
        if arg_count != 1:
            raise TypeError(f'Require 1 parameter but {arg_count} given')
        # 创建类的默认属性
        self.dvdid = dvdid              # DVD ID，即通常的番号
        self.cid = cid                  # DMM Content ID
        self.files = []                 # 关联到此番号的所有影片文件的列表（用于管理带有多个分片的影片）
        self.data_src = 'normal'        # 数据源：不同的数据源将使用不同的爬虫
        self.info = None                # 抓取到的影片信息
        self.save_dir = None            # 存放影片、封面、NFO的文件夹路径
        self.basename = None            # 按照命名模板生成的不包含路径和扩展名的basename
        self.nfo_file = None            # nfo文件的路径
        self.fanart_file = None         # fanart文件的路径
        self.poster_file = None         # poster文件的路径

    @cached_property
    def hard_sub(self) -> bool:
        """影片文件带有内嵌字幕"""
        return 'C' in self.attr_str

    @cached_property
    def uncensored(self) -> bool:
        """影片文件是无码流出/无码破解版本（很多种子并不严格区分这两种，故这里也不进一步细分）"""
        return 'U' in self.attr_str

    @cached_property
    def attr_str(self) -> str:
        """用来标示影片文件的额外属性的字符串(空字符串/-U/-C/-UC)"""
        # 暂不支持多分片的影片
        if len(self.files) != 1:
            return ''
        r = detect_special_attr(self.files[0])
        if r:
            r = '-' + r
        return r

    def __repr__(self) -> str:
        if self.cid and self.data_src == 'cid':
            expression = f"('cid={self.cid}')"
        else:
            expression = f"('{self.dvdid}')"
        return __class__.__name__ + expression

    def rename_files(self):
        """根据命名规则移动（重命名）影片文件"""
        def move_file(src:str, dst:str):
            """移动（重命名）文件并记录信息到日志"""
            abs_dst = os.path.abspath(dst)
            os.rename(src, abs_dst)
            src_rel = os.path.relpath(src)
            dst_name = os.path.basename(dst)
            logger.info(f"重命名文件: '{src_rel}' -> '...{os.sep}{dst_name}'")
            # 目前StreamHandler并未设置filter，为了避免显示中出现重复的日志，这里暂时只能用debug级别
            filemove_logger.debug(f'移动（重命名）文件: \n  原路径: "{src}"\n  新路径: "{abs_dst}"')

        new_paths = []
        if len(self.files) == 1:
            fullpath = self.files[0]
            ext = os.path.splitext(fullpath)[1]
            newpath = os.path.join(self.save_dir, self.basename + ext)
            move_file(fullpath, newpath)
            new_paths.append(newpath)
        else:
            for i, fullpath in enumerate(self.files, start=1):
                ext = os.path.splitext(fullpath)[1]
                newpath = os.path.join(self.save_dir, self.basename + f'-CD{i}' + ext)
                move_file(fullpath, newpath)
                new_paths.append(newpath)
        self.new_paths = new_paths


class GenreMap(dict):
    """genre的映射表"""
    def __init__(self, file):
        genres = {}
        with open(mei_path(file), newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            try:
                for row in reader:
                    genres[row['id']] = row['translate']
            except UnicodeDecodeError:
                logger.error('CSV file must be saved as UTF-8-BOM to edit is in Excel')
            except KeyError:
                logger.error("The columns 'id' and 'translate' must exist in the csv file")
        self.update(genres)

    def map(self, ls):
        """将列表ls按照内置的映射进行替换：保留映射表中不存在的键，删除值为空的键"""
        mapped = [self.get(i, i) for i in ls]
        cleaned = [i for i in mapped if i]  # 译文为空表示此genre应当被删除
        return cleaned
