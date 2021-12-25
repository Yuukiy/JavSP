"""使用Open CV识别图像"""
import os
import cv2 as cv
import sys
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.datatype import mei_path

__all__ = ['crop_by_face']

face_cascade = cv.CascadeClassifier(mei_path('data/haarcascade_frontalface_default.xml'))


# https://github.com/PyImageSearch/imutils/blob/master/imutils/convenience.py#L41
def rotate_bound(image, angle):
    # grab the dimensions of the image and then determine the center
    (h, w) = image.shape[:2]
    (cX, cY) = (w / 2, h / 2)

    # grab the rotation matrix (applying the negative of the angle to rotate clockwise),
    # then grab the sine and cosine (i.e., the rotation components of the matrix)
    M = cv.getRotationMatrix2D((cX, cY), -angle, 1.0)
    cosine = abs(M[0, 0])
    sine = abs(M[0, 1])

    # compute the new bounding dimensions of the image
    nW = int((h * sine) + (w * cosine))
    nH = int((h * cosine) + (w * sine))

    # adjust the rotation matrix to take into account translation
    M[0, 2] += (nW / 2) - cX
    M[1, 2] += (nH / 2) - cY

    # perform the actual rotation and return the image
    return cv.warpAffine(image, M, (nW, nH))


def isValidArea(area):
    """通过识别出的人脸区域大小判断识别结果是否有效"""
    (x, y, w, h) = area
    # 目前的参数是根据840x450左右大小的图片设置的
    if (100 <= w <= 200) and (100 <= h <= 200):
        return True
    else:
        return False


def calc_origin_area(img, area, rotate, ori_size):
    """计算图片中指定区域的中心点在旋转前的位置"""
    # 计算area的中心点以图片中心点为坐标原点的新坐标
    (h, w) = img.shape[:2]
    Ox, Oy = (h//2, w//2)
    new_x = area[0] + area[2]//2 - Ox
    new_y = area[1] + area[3]//2 - Oy
    # 计算area的中心点做反向旋转后的坐标
    anti_rotate = math.radians(-rotate)
    anti_x = new_x * math.cos(anti_rotate) - new_y * math.sin(anti_rotate)
    anti_y = new_x * math.sin(anti_rotate) + new_y * math.cos(anti_rotate)
    # 计算area的中心点在原图坐标系中的坐标
    (ori_h, ori_w) = ori_size
    origin_x = int(ori_w // 2 + anti_x)
    origin_y = int(ori_h // 2 + anti_y)
    # 倾斜度数大的图片，保持人脸居中会使得裁剪范围内的图像内容不平衡（如siro-4727）
    # 因此，计算裁剪框时适当进行居中
    crop_x = int(((ori_w // 2 + new_x) + origin_x) / 2)
    crop_y = int(((ori_h // 2 + new_y) + origin_y) / 2)
    return (origin_x, origin_y), (crop_x, crop_y)


def detect_faces(img_path, debug=False):
    """检测图片中的人脸并返回第一个有效的人脸区域"""
    img = cv.imread(img_path)
    # OpenCV的检测效果似乎受图像角度影响很大，因此要尝试旋转图片（顺时针为正）
    rotate_angles = (0, 10, -10, 20, -20, 30, -30, 40, -40, 50, -50, 60, -60)
    for angle in rotate_angles:
        rotated = rotate_bound(img, angle)
        grey = cv.cvtColor(rotated, cv.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(grey, 1.1, 4)
        for area in faces:
            if isValidArea(area):
                face_pos, crop_pos = calc_origin_area(rotated, area, angle, img.shape[:2])
                return face_pos, crop_pos, angle
            # 有效区域用绿框标记，无效区域用红框标记
            color = (0, 255, 0) if isValidArea(area) else (0, 0, 255)
            (x, y, w, h) = area
            cv.rectangle(rotated, (x, y), (x+w, y+h), color, 2)
            recog_info = f'({x},{y}), {w}x{h}'
            (h2, w2) = rotated.shape[:2]
            pos = (min(w2-170, x), max(y-10, 12))    # 避免信息显示到绘图区外
            cv.putText(rotated, recog_info, pos, cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        if debug:
            win_name = "Actress detection"
            cv.imshow(win_name, rotated)
            cv.setWindowTitle(win_name, win_name + f" with ratotion {angle} degrees")
            cv.waitKey(0)


def crop_by_face(img_path, out_path, debug=False):
    """根据指定的人脸区域裁剪图片"""
    (face_cx, face_cy), (crop_cx, crop_cy), angle = detect_faces(img_path)
    img = cv.imread(img_path)
    (h, w) = img.shape[:2]
    # 按照Kodi的poster宽高比2:3来裁剪，计算裁剪位置
    pw = int(h * 2 / 3)
    if pw <= w:     # poster_size = (pw, h)
        ph = h
    else:           # 图片太“瘦”，以宽度来定裁剪高度
        (pw, ph) = (w, int(w * 3 / 2))
    x1 = max(0, crop_cx - pw//2)
    y1 = max(0, crop_cy - ph//2)
    x2 = x1 + pw
    y2 = y1 + ph
    # 裁剪图片
    crop = img[y1:y2, x1:x2]
    cv.imwrite(out_path, crop)
    if debug:
        # 绿线标注检测到的人脸位置，红框标注裁剪区域
        if not os.path.exists('debug'):
            os.mkdir('debug')
        cv.circle(img, (face_cx, face_cy), 100, (0,255,0), 1)
        cv.rectangle(img, (x1, y1), (x2, y2-1), (0, 0, 255), 1)
        filepath, ext = os.path.splitext(img_path)
        output = 'debug/' + filepath + '_opencv' + ext
        cv.imwrite(output, img)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        for dirpath, dirnames, filenames in os.walk('.'):
            for file in filenames:
                if file.endswith('.jpg'):
                    crop_by_face(file, 'debug/output.jpg', True)
            break
    else:
        for img_path in sys.argv[1:]:
            crop_by_face(img_path, 'debug/output.jpg', True)
