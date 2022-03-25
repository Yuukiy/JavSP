"""处理本地图片的相关功能"""
import os
import logging
from PIL import Image, ImageOps


__all__ = ['valid_pic', 'crop_poster', 'get_pic_size']

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


def crop_poster(fanart_file, poster_file):
    """将给定的fanart图片文件裁剪为适合poster尺寸的图片"""
    # Kodi的宽高比为2:3，但是按照这个比例来裁剪会导致poster画面不完整，
    # 因此按照poster画面比例来裁剪，这样的话虽然在显示时可能有轻微变形，但是画面是完整的
    fanart = Image.open(fanart_file)
    fanart_w, fanart_h = fanart.size
    # 1.42 = 2535/1785（高清封面）, 539/379（普通封面）
    poster_w = int(fanart_h / 1.42)
    if poster_w <= fanart_w:
        poster_h = fanart_h
    else:
        # 图片太“瘦”时以宽度来定裁剪高度
        poster_w, poster_h = fanart_w, int(fanart_w * 1.42)
    # (left, upper, right, lower)
    box = (fanart_w-poster_w, 0, fanart_w, poster_h)
    poster = fanart.crop(box)
    # quality: from doc, default is 75, values above 95 should be avoided
    poster.save(poster_file, quality=95)


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
