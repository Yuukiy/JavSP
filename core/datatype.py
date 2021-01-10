"""定义数据类型"""


class Movie:
    def __init__(self, dvdid, cid=None, pid=None):
        self.dvdid = dvdid          # DVD ID，即通常的番号
        self.cid = cid              # DMM Content ID
        self.pid = pid              # DMM Product ID
        self.cover = None           # 封面图片
        self.genre = None           # 影片分类的标签
        self.score = None           # 评分（目前为5分制）
        self.title = None           # 影片标题（不含番号）
        self.magnet = None          # 磁力链接
        self.actress = None         # 出演女优
        self.director = None        # 导演
        self.duration = None        # 影片时长
        self.producer = None        # 制作商
        self.publisher = None       # 发行商
        self.preview_pics = None    # 预览图片
        self.preview_video = None   # 预览视频
        self.publish_date = None    # 发布日期

