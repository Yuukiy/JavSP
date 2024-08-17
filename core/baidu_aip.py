"""百度AI开放平台的人体分析方案"""
import os
import sys
import json
import random
import logging
from hashlib import md5
from datetime import datetime

from aip import AipBodyAnalysis
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config import cfg, rel_path_from_exe

logger = logging.getLogger(__name__)


class AipClient():
    def __init__(self) -> None:
        piccfg = cfg.Picture
        # 保存已经识别过的图片的结果，减少请求次数
        self.file = rel_path_from_exe('data/baidu_aip.cache.json')
        dir_path = os.path.dirname(self.file)
        if (not os.path.exists(dir_path)) and piccfg.ai_engine == 'baidu':
            os.makedirs(dir_path)
        if os.path.exists(self.file):
            with open(self.file, 'rt', encoding='utf-8') as f:
                self.cache = json.load(f)
        else:
            self.cache = {}
        self.client = AipBodyAnalysis(piccfg.aip_appid, piccfg.aip_api_key, piccfg.aip_secret_key)

    def analysis(self, pic_path):
        with open(pic_path, 'rb') as f:
            pic = f.read()
            hash = md5(pic).hexdigest()
        if hash in self.cache:
            return self.cache[hash]['result']
        else:
            now = datetime.now().isoformat()
            try:
                result = self.client.bodyAnalysis(pic)
            except Exception as e:
                logger.debug(e, exc_info=True)
                raise
            if 'error_code' in result:
                raise Exception(f"Baidu AIP error {result['error_code']}: {result['error_msg']}")
            record = {'pic': os.path.basename(pic_path), 'time': now, 'result': result}
            self.cache[hash] = record
            with open(self.file, 'wt', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False)
            return result


ai = AipClient()


def choose_center(body_parts):
    # 寻找关键部位作为图片的中心点，顺序依次为:
    # 鼻子, 左右眼, 左右耳, 左右嘴角, 头顶, 颈部, 左右肩
    if 'nose' in body_parts:
        return body_parts['nose']
    pair_parts = (('left_eye', 'right_eye'),
                  ('left_ear', 'right_ear'),
                  ('left_mouth_corner', 'right_mouth_corner'))
    for parts_name in pair_parts:
        pair = [body_parts.get(i) for i in parts_name]
        if all(pair):
            return {i: (pair[0][i]+pair[1][i])/2 for i in pair[0].keys()}
    for part in ('top_head', 'neck'):
        if part in body_parts:
            return body_parts[part]
    pair = [body_parts.get(i) for i in ('left_shoulder', 'right_shoulder')]
    if all(pair):
        return {i: (pair[0][i]+pair[1][i])/2 for i in pair[0].keys()}
    return {}


def fit_crop_box(box, persons):
    """根据人体框信息调整裁剪框，以包含更完整的人体区域"""
    if len(persons) == 0:
        return box
    elif len(persons) == 1:
        loc = persons[0]['location']
        left0, right0 = loc['left'], loc['left']+loc['width']
        top0, bottom0 = loc['top'], loc['top']+loc['height']
    else:
        allow_score = persons[0]['total_score'] * 0.7
        allow_persons = [i for i in persons if i['total_score'] >= allow_score]
        locs = []
        # 求取一个包含重叠的几个人体框区域的矩形
        for i in allow_persons:
            loc = i['location']
            le, ri = loc['left'], loc['left']+loc['width']
            to, bo = loc['top'], loc['top']+loc['height']
            locs.append((le, to, ri, bo))
        locs.sort(key=lambda x: x[0])   # sort by postion left
        le0, to0, ri0, bo0 = locs[0]
        for (le, to, ri, bo) in locs[1:]:
            if le0 <= le < ri0 and (to0 <= to < bo0 or to0 <= bo < bo0):
                to0 = max(to, to0)
                ri0 = max(ri, ri0)
                bo0 = max(bo, bo0)
        left0, top0, right0, bottom0 = le0, to0, ri0, bo0
    # 调整裁剪框位置
    (left, top, right, bottom) = box
    if left < left0 < right < right0:
        move = min(left0-left, right0-right)
        left, right = left+move, right+move
    if left0 < left < right0 < right:
        move = min(left-left0, right-right0)
        left, right = left-move, right-move
    if top < top0 < bottom < bottom0:
        move = min(top0-top, bottom0-bottom)
        top, bottom = top+move, bottom+move
    if top0 < top < bottom0 < bottom:
        move = min(top-top0, bottom-bottom0)
        top, bottom = top-move, bottom-move
    return (left, top, right, bottom)


def aip_crop_poster(fanart, poster='', hw_ratio=1.42):
    """将给定的fanart图片文件裁剪为适合poster尺寸的图片"""
    r = ai.analysis(fanart)
    im = ImageOps.exif_transpose(Image.open(fanart))
    # 计算识别到的各人体框区域的权重
    for person in r['person_info']:
        # 当关键点得分大于0.2的个数大于3，且人体框的分数大于0.03时，才认为是有效人体
        valid_parts = [k for k, v in person['body_parts'].items() if v['score'] > 0.2]
        if not (len(valid_parts) > 3 and person['location']['score'] > 0.03):
            person['total_score'] = 0
            continue
        loc = person['location']
        score, width, height = loc['score'], loc['width'], loc['height']
        # 为每个识别到的区域计算权重，综合考虑区域相对于图片大小的占比和人体识别置信度
        nose_weight = 100 if 'nose' in person['body_parts'] else 30
        total_score = (width*height)/(im.width*im.height) * score * nose_weight
        person['total_score'] = total_score
    # 计算裁剪框大小（方法同image.py）
    fanart_w, fanart_h = im.size
    poster_w = int(fanart_h / hw_ratio)
    if poster_w <= fanart_w:
        poster_h = fanart_h
    else:
        poster_w, poster_h = fanart_w, int(fanart_w * hw_ratio)
    # 采信得分最高的一个人体框
    persons = sorted(r['person_info'], key=lambda x: x['total_score'], reverse=True)
    body_parts = persons[0]['body_parts']
    valid_parts = {k: v for k, v in body_parts.items() if v['score'] > 0.3}
    if not valid_parts:
        raise Exception('Baidu AIP error: 人体识别未获得有效结果')
    center = choose_center(valid_parts)
    loc = persons[0]['location']
    top0, left0, width0, height0 = loc['top'], loc['left'], loc['width'], loc['height']
    if not center:
        # 找不到人体关键部位时，使用人体框中心作为裁剪中心点
        center['x'] = left0 + width0/2
        center['y'] = top0 + height0/2
    left2, top2 = center['x']-poster_w/2, center['y']-poster_h/2
    right2, bottom2 = center['x']+poster_w/2, center['y']+poster_h/2
    # 调整裁剪框的位置，确保裁剪框没有超出图片范围
    if left2 < 0:
        left2, right2 = 0, right2-left2
    if top2 < 0:
        top2, bottom2 = 0, bottom2-top2
    if right2 > fanart_w:
        left2, right2 = left2-(right2-fanart_w), fanart_w
    if bottom2 > fanart_h:
        top2, bottom2 = top2-(bottom2-fanart_h), fanart_h
    # 当裁剪框的一边超出人体框且另一边有移动余量时，移动裁剪框使其对齐人体框
    box = fit_crop_box((left2, top2, right2, bottom2), persons)
    # 裁剪图片
    im_poster = im.crop(box)
    if im_poster.mode != 'RGB':
        im_poster = im_poster.convert('RGB')
    im_poster.save(poster, quality=95)
    # 调试模式下显示图片结果和标注
    if globals().get('baidu_aip_debug'):
        im2 = draw_marks(im, r)
        draw = ImageDraw.Draw(im2)
        draw_labeled_box(draw, box, outline='red', width=2, label='CROP')
        im2.show()


# 下面的函数主要用于调试，正常功能中不会触发

def random_color():
    # 降低红色取值范围，以便与红色的裁剪框区分开来
    r = random.randint(0, 180)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    rgb = [r, g, b]
    return tuple(rgb)


def calc_ellipse(center, r=1.5):
    x, y = center
    return (x-r, y-r, x+r, y+r)


def draw_labeled_box(draw: ImageDraw, xy, fill=None, outline=None, width=1, label=''):
    draw.rectangle(xy, fill, outline, width)
    scale = min(xy[2]-xy[0], xy[3]-xy[1])
    fontsize = max(12, min(40, int(scale/15)))
    try:
        fnt = ImageFont.truetype("consola.ttf", fontsize)
    except:
        fnt = ImageFont.load_default()
    if label:
        tw, th = draw.textsize(label, font=fnt)
        textbox = (xy[0], xy[1], xy[0]+tw, xy[1]+th)
        draw.rectangle(textbox, outline)
    draw.text((xy[0], xy[1]), label, font=fnt)


def draw_marks(im0, data):
    """在图片上画出人脸识别到的关键点信息"""
    im = im0.copy()
    draw = ImageDraw.Draw(im)
    for person in data['person_info']:
        color = random_color()
        for part, info in person['body_parts'].items():
            point = (info['x'], info['y'])
            if part == 'nose':
                draw.ellipse(calc_ellipse(point, r=2), fill=color, outline=color)
            else:
                draw.ellipse(calc_ellipse(point), fill=color)
        loc = person['location']
        rec = (loc['left'], loc['top'], loc['left']+loc['width'], loc['top']+loc['height'])
        label = f"{loc['width']:.0f}x{loc['height']:.0f}, {loc['score']:.3}\n" + \
                f"score: {person['total_score']:.3f}"
        draw_labeled_box(draw, rec, outline=color, width=2, label=label)
    return im


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)
    baidu_aip_debug = True
    files = sys.argv[1:] or ["FC2-1283407-fanart.jpg"]
    for file in files:
        if os.path.exists(file):
            base, ext = os.path.splitext(file)
            poster = base.replace('_fanart', '') + '_poster' + ext
            aip_crop_poster(file, poster)
            print('Crop poster to: ' + poster)
