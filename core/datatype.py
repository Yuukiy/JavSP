"""定义数据类型和一些通用性的对数据类型的操作"""
import os
import csv
import json
import logging


logger = logging.getLogger(__name__)


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
        # 创建类的默认属性
        self.dvdid = dvdid          # DVD ID，即通常的番号
        self.cid = cid              # DMM Content ID
        self.plot = None            # 故事情节
        self.cover = None           # 封面图片（URL）
        self.big_cover = None       # 高清封面图片（URL）
        self.genre = None           # 影片分类的标签
        self.genre_id = None        # 影片分类的标签的ID，用于解决部分站点多个genre同名的问题，也便于管理多语言的genre
        self.genre_norm = None      # 统一后的影片分类的标签
        self.score = None           # 评分（10分制）
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
        return __class__.__name__ + f"('{self.dvdid}')"

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def dump(self, filepath) -> None:
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

    def __repr__(self) -> str:
        return __class__.__name__ + f"('{self.dvdid}')"

    def rename_files(self):
        """根据命名规则移动（重命名）影片文件"""
        def move_file(src:str, dst:str):
            """移动（重命名）文件并记录信息到日志"""
            os.rename(src, dst)
            src_rel = os.path.relpath(src)
            dst_name = os.path.basename(dst)
            logger.info(f"重命名文件: '{src_rel}' -> '...{os.sep}{dst_name}'")

        if len(self.files) == 1:
            fullpath = self.files[0]
            ext = os.path.splitext(fullpath)[1]
            newpath = os.path.join(self.save_dir, self.basename + ext)
            move_file(fullpath, newpath)
        else:
            for i in range(len(self.files)):
                fullpath = self.files[i]
                ext = os.path.splitext(fullpath)[1]
                cdx = f'-CD{i+1}'
                newpath = os.path.join(self.save_dir, self.basename + cdx + ext)
                move_file(fullpath, newpath)


class ColoredFormatter(logging.Formatter):
    """为不同level的日志着色"""
    NO_STYLE = '\033[0m'
    COLOR_MAP = {
        logging.DEBUG:    '\033[1;30m', # grey
        logging.WARNING:  '\033[1;33m', # light yellow
        logging.ERROR:    '\033[1;31m', # light red
        logging.CRITICAL: '\033[0;31m', # red
    }

    def __init__(self, fmt='%(levelname)-8s:%(message)s', datefmt='%Y-%m-%d %H:%M:%S', style='%', validate=True) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)

    def format(self, record):
        raw = super().format(record)
        color = self.COLOR_MAP.get(record.levelno, self.NO_STYLE)
        return color + raw + self.NO_STYLE


class GenreMap(dict):
    """genre的映射表"""
    def __init__(self, file):
        genres = {}
        with open(file, newline='', encoding='utf-8-sig') as csvfile:
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
