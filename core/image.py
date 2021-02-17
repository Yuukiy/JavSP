"""处理本地图片的相关功能"""
from PIL import Image


__all__ = ['crop_poster', 'get_pic_size']


def crop_poster(fanart_file, poster_file):
    """将给定的fanart图片文件裁剪为适合poster尺寸的图片"""
    # 本项目根据KODI的文档来裁剪poster。对于其他的媒体服务器（如Jellyfin），
    # 由于未在其文档中找到对此的说明，因此假定它们的相关spec均符合先行者KODI的规范:
    # https://kodi.wiki/view/Artwork_types#poster
    fanart = Image.open(fanart_file)
    fanart_w, fanart_h = fanart.size
    poster_w = int(fanart_h / 3 * 2)
    box = (fanart_w-poster_w, 0, fanart_w, fanart_h)
    poster = fanart.crop(box)
    # quality: from doc, default is 75, values above 95 should be avoided
    poster.save(poster_file, quality=95)


def get_pic_size(pic_file):
    """获取图片文件的分辨率"""
    pic = Image.open(pic_file)
    return pic.size
