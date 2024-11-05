def get_poster_size(image_shape: tuple[int, int], ratio: float) -> tuple[int, int]:
        (fanart_w, fanart_h) = image_shape
        (poster_w, poster_h) = \
            (int(fanart_h / ratio), fanart_h) \
            if fanart_h / fanart_w < ratio \
            else (fanart_w, int(fanart_w * ratio)) # 图片太“瘦”时以宽度来定裁剪高度
        return (poster_w, poster_h)

def get_bound_box_by_face(face: tuple[int, int, int, int], image_shape: tuple[int, int], ratio: float) -> tuple[int, int, int, int]:
    """
    returns (left, upper, right, lower)
    """

    (fanart_w, fanart_h) = image_shape
    (poster_w, poster_h) = get_poster_size(image_shape, ratio)

    # face coordinates
    fx, fy, fw, fh = face

    # face center
    cx, cy = fx + fw / 2, fy + fh / 2

    poster_left = max(cx - poster_w / 2, 0)
    poster_left = min(poster_left, fanart_w - poster_w)
    poster_left = int(poster_left)
    return (poster_left, 0, poster_left + poster_w, poster_h)

