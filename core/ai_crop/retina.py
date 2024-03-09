from retinaface import RetinaFace

from PIL import Image, ImageOps
def ai_crop_poster(fanart, poster='', hw_ratio=1.42):
    im = ImageOps.exif_transpose(Image.open(fanart))
    fanart_w, fanart_h = im.size
    poster_h = fanart_h
    poster_w = fanart_h / hw_ratio 

    resp = RetinaFace.detect_faces(fanart)

    if not 'face_1' in resp:
        raise Exception("Retina can't detect face")

    [x1, y1, x2, y2] = resp['face_1']['facial_area']
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    poster_left = max(center_x - poster_w / 2, 0)
    poster_left = min(poster_left, fanart_w - poster_w)
    poster_left = int(poster_left)
    im_poster = im.crop((poster_left, 0, int(poster_left + poster_w), poster_h))
    if im_poster.mode != 'RGB':
        im_poster = im_poster.convert('RGB')
    im_poster.save(poster, quality=95)

