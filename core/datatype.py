"""定义数据类型"""
import json
from datetime import date


class Movie:
    def __init__(self, dvdid: str, *, cid=None, pid=None):
        self.dvdid = dvdid          # DVD ID，即通常的番号
        self.cid = cid              # DMM Content ID
        self.pid = pid              # DMM Product ID
        self.cover = None           # 封面图片
        self.genre = None           # 影片分类的标签
        self.score = None           # 评分（10分制）
        self.title = None           # 影片标题（不含番号）
        self.magnet = None          # 磁力链接
        self.serial = None          # 系列（目前仅avsox使用了该字段）
        self.actress = None         # 出演女优
        self.director = None        # 导演
        self.duration = None        # 影片时长
        self.producer = None        # 制作商
        self.publisher = None       # 发行商
        self.publish_date = None    # 发布日期
        self.preview_pics = None    # 预览图片
        self.preview_video = None   # 预览视频

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
