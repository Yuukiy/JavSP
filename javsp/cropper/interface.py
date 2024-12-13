from PIL.Image import Image
from abc import ABC, abstractmethod
class Cropper(ABC):
    @abstractmethod
    def crop_specific(self, fanart: Image, ratio: float) -> Image:
        pass

    def crop(self, fanart: Image, ratio: float | None = None) -> Image:
        if ratio is None: 
            ratio = 1.42
        return self.crop_specific(fanart, ratio)

class DefaultCropper(Cropper):
    def crop_specific(self, fanart: Image, ratio: float) -> Image:
        """将给定的fanart图片文件裁剪为适合poster尺寸的图片"""
        (fanart_w, fanart_h) = fanart.size
        (poster_w, poster_h) = \
            (int(fanart_h / ratio), fanart_h) \
            if fanart_h / fanart_w < ratio \
            else (fanart_w, int(fanart_w * ratio)) # 图片太“瘦”时以宽度来定裁剪高度

        dh = int((fanart_h - poster_h) / 2)
        box = (fanart_w - poster_w, dh, fanart_w, poster_h + dh)
        return fanart.crop(box)
