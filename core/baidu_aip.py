"""百度AI开放平台的人体分析方案"""
import os
import sys
import json
import random
from hashlib import md5
from datetime import datetime

from aip import AipBodyAnalysis
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config import cfg, rel_path_from_exe


class AipClient():
    def __init__(self) -> None:
        # 保存已经识别过的图片的结果，减少请求次数
        self.file = rel_path_from_exe('data/baidu_aip.cache.json')
        dir_path = os.path.dirname(self.file)
        if not os.path.exists(dir_path):
            os.mkdirs(dir_path)
        if os.path.exists(self.file):
            with open(self.file, 'rt', encoding='utf-8') as f:
                self.cache = json.load(f)
        else:
            self.cache = {}
        piccfg = cfg.Picture
        self.client = AipBodyAnalysis(piccfg.aip_appid, piccfg.aip_api_key, piccfg.aip_secret_key)

    def analysis(self, pic_path):
        with open(pic_path, 'rb') as f:
            pic = f.read()
            hash = md5(pic).hexdigest()
        if hash in self.cache:
            return self.cache[hash]['result']
        else:
            now = datetime.now().isoformat()
            result = self.client.bodyAnalysis(pic)
            record = {'pic': os.path.basename(pic_path), 'time': now, 'result': result}
            self.cache[hash] = record
            with open(self.file, 'wt', encoding='utf-8') as f:
                json.dump(self.cache, f)
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
            return {i:(pair[0][i]+pair[1][i])/2 for i in pair[0].keys()}
    for part in ('top_head', 'neck'):
        if part in body_parts:
            return body_parts[part]
    pair = [body_parts.get(i) for i in ('left_shoulder', 'right_shoulder')]
    if all(pair):
        return {i:(pair[0][i]+pair[1][i])/2 for i in pair[0].keys()}
    return {}


def aip_crop_poster(fanart, poster='', hw_ratio=1.42):
    """将给定的fanart图片文件裁剪为适合poster尺寸的图片"""
    r = ai.analysis(fanart)
    im = Image.open(fanart)
    # 计算识别到的各人体框区域的权重
    for person in r['person_info']:
        # 当关键点得分大于0.2的个数大于3，且人体框的分数大于0.03时，才认为是有效人体
        valid_parts = [k for k, v in person['body_parts'].items() if v['score'] > 0.2]
        if not (len(valid_parts) > 3 and person['location']['score'] > 0.03):
            person['total_score'] = 0
            continue
        score, top, left, width, height = 0, 0, 0, 0, 0
        # extract vars: score, top, left, width, height
        locals().update(person['location'])
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
    # 寻找一个最佳位置的裁剪框，使得尽可能包含最多的人体
    # (left, upper, right, lower)
    prefer_person = sorted(r['person_info'], key=lambda x:x['total_score'])[0]
    body_parts = prefer_person['body_parts']
    valid_parts = {k:v for k,v in body_parts.items() if v['score'] > 0.3}
    center = choose_center(valid_parts)
    if not center:
        # 找不到人体关键部位时，使用人体框中心作为裁剪中心点
        # extract vars: score, top, left, width, height
        locals().update(prefer_person['location'])
        center['x'] = left + width/2
        center['y'] = top + height/2
    # 调整裁剪框的位置，确保裁剪框没有超出图片范围
    left2, upper2 = center['x']-poster_w/2, center['y']-poster_h/2
    right2, lower2 = center['x']+poster_w/2, center['y']+poster_h/2
    if left2 < 0:
        left2, right2 = 0, right2-left2
    if upper2 < 0:
        upper2, lower2 = 0, lower2-upper2
    if right2 > fanart_w:
        left2, right2 = left2-(right2-fanart_w), fanart_w
    if lower2 > fanart_h:
        upper2, lower2 = upper2-(lower2-fanart_h), fanart_h
    # 裁剪图片 (left, upper, right, lower)
    box = (left2, upper2, right2, lower2)
    im_poster = im.crop(box)
    im_poster.save(poster, quality=95)
    # 调试模式下显示图片结果和标注
    if globals().get('baidu_aip_debug'):
        im2 = draw_marks(im, r)
        draw = ImageDraw.Draw(im2)
        draw_labeled_box(draw, box, outline='red', width=2)
        im2.show()


# 下面的函数主要用于调试，正常功能中不会触发

def random_color():
    r = random.randint(0,255)
    g = random.randint(0,255)
    b = random.randint(0,255)
    rgb = [r,g,b]
    return tuple(rgb)


def calc_ellipse(center, r=1.5):
    x, y = center
    return (x-r, y-r, x+r, y+r)


def draw_labeled_box(draw: ImageDraw, xy, fill=None, outline=None, width=1, label=''):
    draw.rectangle(xy, fill, outline, width)
    scale = min(xy[2]-xy[0], xy[3]-xy[1])
    fontsize = max(12, min(40, int(scale/15)))
    fnt = ImageFont.truetype("consola.ttf", fontsize)
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
        score = (loc['width']*loc['height'])/(im.width*im.height)*100 * loc['score']
        if score > 2:
            label = f"{loc['width']:.0f}x{loc['height']:.0f}, {loc['score']:.3}\n{score:.3f}"
            draw_labeled_box(draw, rec, outline=color, width=2, label=label)
    return im


if __name__ == "__main__":
    baidu_aip_debug = True
    files = sys.argv[1:] or ["FC2-1283407-fanart.jpg"]
    for file in files:
        if os.path.exists(file):
            base, ext = os.path.splitext(file)
            poster = base.replace('_fanart', '') + '_poster' + ext
            aip_crop_poster(file, poster)
            print('Crop poster to: ' + poster)
