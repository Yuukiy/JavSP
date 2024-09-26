"""处理本地图片的相关功能"""
from enum import Enum
import os
import logging
from PIL import Image, ImageOps


__all__ = ['valid_pic', 'get_pic_size', 'add_label_to_poster', 'LabelPostion']

logger = logging.getLogger(__name__)


def valid_pic(pic_path):
    """检查图片文件是否完整"""
    try:
        img = ImageOps.exif_transpose(Image.open(pic_path))
        img.load()
        return True
    except Exception as e:
        logger.debug(e, exc_info=True)
        return False


# 位置枚举
class LabelPostion(Enum):
    """水印位置枚举"""
    TOP_LEFT = 1
    TOP_RIGHT = 2
    BOTTOM_LEFT = 3
    BOTTOM_RIGHT = 4

def add_label_to_poster(poster: Image.Image, mark_pic_file: Image.Image, pos: LabelPostion) -> Image.Image:
    """向poster中添加标签(水印)"""
    mark_img = mark_pic_file.convert('RGBA')
    r,g,b,a = mark_img.split()
    # 计算水印位置
    if pos == LabelPostion.TOP_LEFT:
        box = (0, 0)
    elif pos == LabelPostion.TOP_RIGHT:
        box = (poster.size[0] - mark_img.size[0], 0)
    elif pos == LabelPostion.BOTTOM_LEFT:
        box = (0, poster.size[1] - mark_img.size[1])
    elif pos == LabelPostion.BOTTOM_RIGHT:
        box = (poster.size[0] - mark_img.size[0], poster.size[1] - mark_img.size[1])
    poster.paste(mark_img, box=box, mask=a)
    return poster


def get_pic_size(pic_path):
    """获取图片文件的分辨率"""
    pic = ImageOps.exif_transpose(Image.open(pic_path))
    return pic.size


if __name__ == "__main__":
    import os, sys
    import pretty_errors
    pretty_errors.configure(display_link=True)
    for file in sys.argv[1:]:
        if os.path.exists(file):
            base, ext = os.path.splitext(file)
            poster = base.replace('_fanart', '') + '_poster' + ext
            crop_poster(file, poster)
