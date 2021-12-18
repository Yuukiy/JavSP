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


def detect_faces(img_path, debug=False):
    img = cv2.imread(img_path)
    faces = []
    # OpenCV的检测效果似乎受图像角度影响很大，因此要尝试旋转图片
    for angle in range(-65, 66, 10):
        rotated = rotate_bound(img, angle)
        grey = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(grey, 1.1, 4)
        if debug:
            for (x, y, w, h) in faces:
                cv2.rectangle(rotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
            win_name = "Actress detection"
            cv2.imshow(win_name, rotated)
            cv2.setWindowTitle(win_name, win_name + f" with ratotion {angle} degrees")
            cv2.waitKey(0)
        # 过滤掉大概率不符合条件的结果
        pass
    return faces


if __name__ == "__main__":
    import argparse
    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image", required=True,
        help="path to the image file")
    args = vars(ap.parse_args(['-i', 'siro-4701.jpg']))

    detect_faces(args['image'], True)
