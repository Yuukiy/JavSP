"""处理本地图片的相关功能"""
from PIL import Image


__all__ = ['crop_poster', 'get_pic_size']


def crop_poster(fanart_file, poster_file):
    """将给定的fanart图片文件裁剪为适合poster尺寸的图片"""
    # Kodi的宽高比为2:3，但是按照这个比例来裁剪会导致poster画面不完整，
    # 因此按照poster画面比例来裁剪，这样的话虽然在显示时可能有轻微变形，但是画面是完整的
    fanart = Image.open(fanart_file)
    fanart_w, fanart_h = fanart.size
    # 1.42 = 2535/1785（高清封面）, 539/379（普通封面）
    poster_w = int(fanart_h / 1.42)
    box = (fanart_w-poster_w, 0, fanart_w, fanart_h)
    poster = fanart.crop(box)
    # quality: from doc, default is 75, values above 95 should be avoided
    poster.save(poster_file, quality=95)


def get_pic_size(pic_file):
    """获取图片文件的分辨率"""
    pic = Image.open(pic_file)
    return pic.size
