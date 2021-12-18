"""使用Open CV识别图像"""
import os
import cv2
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.datatype import mei_path

face_cascade = cv2.CascadeClassifier(mei_path('data/haarcascade_frontalface_default.xml'))


# https://github.com/PyImageSearch/imutils/blob/master/imutils/convenience.py#L41
def rotate_bound(image, angle):
    # grab the dimensions of the image and then determine the center
    (h, w) = image.shape[:2]
    (cX, cY) = (w / 2, h / 2)

    # grab the rotation matrix (applying the negative of the angle to rotate clockwise),
    # then grab the sine and cosine (i.e., the rotation components of the matrix)
    M = cv2.getRotationMatrix2D((cX, cY), -angle, 1.0)
    cosine = abs(M[0, 0])
    sine = abs(M[0, 1])

    # compute the new bounding dimensions of the image
    nW = int((h * sine) + (w * cosine))
    nH = int((h * cosine) + (w * sine))

    # adjust the rotation matrix to take into account translation
    M[0, 2] += (nW / 2) - cX
    M[1, 2] += (nH / 2) - cY

    # perform the actual rotation and return the image
    return cv2.warpAffine(image, M, (nW, nH))


def isValidArea(area):
    """通过识别出的人脸区域大小判断识别结果是否有效"""
    (x, y, w, h) = area
    # 目前的参数是根据840x450左右大小的图片设置的
    if (100 <= w <= 200) and (100 <= h <= 200):
        return True
    else:
        return False


def detect_faces(img_path, debug=False):
    img = cv2.imread(img_path)
    faces = []
    # OpenCV的检测效果似乎受图像角度影响很大，因此要尝试旋转图片
    rotate_angles = (0, 10, -10, 20, -20, 30, -30, 40, -40, 50, -50, 60, -60)
    for angle in rotate_angles:
        rotated = rotate_bound(img, angle)
        grey = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(grey, 1.1, 4)
        for area in faces:
            if isValidArea(area) and (not debug):
                return area
            # 有效区域用绿框标记，无效区域用红框标记
            color = (0, 255, 0) if isValidArea(area) else (0, 0, 255)
            (x, y, w, h) = area
            cv2.rectangle(rotated, (x, y), (x+w, y+h), color, 2)
            recog_info = f'({x},{y}), {w}x{h}'
            (h2, w2) = rotated.shape[:2]
            pos = (min(w2-170, x), max(y-10, 12))    # 避免信息显示到绘图区外
            cv2.putText(rotated, recog_info, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        if debug:
            win_name = "Actress detection"
            cv2.imshow(win_name, rotated)
            cv2.setWindowTitle(win_name, win_name + f" with ratotion {angle} degrees")
            cv2.waitKey(0)
    return faces


if __name__ == "__main__":
    import argparse
    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image", required=True,
        help="path to the image file")
    args = vars(ap.parse_args(['-i', 'YPPx.jpg']))

    detect_faces(args['image'], True)
