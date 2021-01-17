"""定义数据类型"""
import os
import json
from datetime import date


class MovieInfo:
    def __init__(self, dvdid=None, /, *, cid=None, pid=None, from_file=None):
        """
        Args:
            dvdid ([str], optional): 番号，要通过其他方式创建实例时此参数应留空
            from_file: 从指定的文件(json格式)中加载数据来创建实例
        """
        # 创建类的默认属性
        self.dvdid = dvdid          # DVD ID，即通常的番号
        self.cid = cid              # DMM Content ID
        self.pid = pid              # DMM Product ID
        self.cover = None           # 封面图片
        self.genre = None           # 影片分类的标签
        self.score = None           # 评分（10分制）
        self.title = None           # 影片标题（不含番号）
        self.magnet = None          # 磁力链接
        self.serial = None          # 系列
        self.actress = None         # 出演女优
        self.director = None        # 导演
        self.duration = None        # 影片时长
        self.producer = None        # 制作商
        self.publisher = None       # 发行商
        self.publish_date = None    # 发布日期
        self.preview_pics = None    # 预览图片
        self.preview_video = None   # 预览视频

        if not dvdid:
            if from_file:
                if os.path.isfile(from_file):
                    self.load(from_file)
                else:
                    raise TypeError('A valid file path is required')
            else:
                raise TypeError("Require additional keyword parameter when 'dvdid' is left blank")

    def __str__(self) -> str:
        d = vars(self)
        if type(d['publish_date']) is date:
            d['publish_date'] = d['publish_date'].isoformat()
        return json.dumps(d, indent=2, ensure_ascii=False)

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
        try:
            d['publish_date'] = date.fromisoformat(d['publish_date'])
        except:
            d['publish_date'] = None
        # 更新对象属性
        attrs = vars(self).keys()
        for k, v in d.items():
            if k in attrs:
                self.__setattr__(k, v)
