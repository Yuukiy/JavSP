# Adapted from https://github.com/opencv/opencv_zoo/blob/main/models/face_detection_yunet/yunet.py

# This file is part of OpenCV Zoo project.
# It is subject to the license terms in the yunet.LICENSE file found in the same directory.
#
# Copyright (C) 2021, Shenzhen Institute of Artificial Intelligence and Robotics for Society, all rights reserved.
# Third party copyrights are property of their respective owners.

import numpy as np
import cv2 as cv

from core.config import cfg

class YuNet:
    def __init__(self, modelPath, inputSize=[320, 320], confThreshold=0.6, nmsThreshold=0.3, topK=5000, backendId=0, targetId=0):
        self._modelPath = modelPath
        self._inputSize = tuple(inputSize) # [w, h]
        self._confThreshold = confThreshold
        self._nmsThreshold = nmsThreshold
        self._topK = topK
        self._backendId = backendId
        self._targetId = targetId

        self._model = cv.FaceDetectorYN.create(
            model=self._modelPath,
            config="",
            input_size=self._inputSize,
            score_threshold=self._confThreshold,
            nms_threshold=self._nmsThreshold,
            top_k=self._topK,
            backend_id=self._backendId,
            target_id=self._targetId)

    @property
    def name(self):
        return self.__class__.__name__

    def setBackendAndTarget(self, backendId, targetId):
        self._backendId = backendId
        self._targetId = targetId
        self._model = cv.FaceDetectorYN.create(
            model=self._modelPath,
            config="",
            input_size=self._inputSize,
            score_threshold=self._confThreshold,
            nms_threshold=self._nmsThreshold,
            top_k=self._topK,
            backend_id=self._backendId,
            target_id=self._targetId)

    def setInputSize(self, input_size):
        self._model.setInputSize(tuple(input_size))

    def infer(self, image):
        # Forward
        faces = self._model.detect(image)
        return np.array([]) if faces[1] is None else faces[1]
    
piccfg = cfg.Picture
if piccfg == None:
    raise Exception("Missing `Picture` field from config.ini")
model_path = piccfg.yunet_model
if model_path == None:
    raise Exception("Missing `yunet_model` for ai crop backend yunet")

backend_target_pairs = [
    [cv.dnn.DNN_BACKEND_OPENCV, cv.dnn.DNN_TARGET_CPU],
    [cv.dnn.DNN_BACKEND_CUDA,   cv.dnn.DNN_TARGET_CUDA],
    [cv.dnn.DNN_BACKEND_CUDA,   cv.dnn.DNN_TARGET_CUDA_FP16],
    [cv.dnn.DNN_BACKEND_TIMVX,  cv.dnn.DNN_TARGET_NPU],
    [cv.dnn.DNN_BACKEND_CANN,   cv.dnn.DNN_TARGET_NPU]
]

backend_target = 0
backend_id = backend_target_pairs[backend_target][0]
target_id = backend_target_pairs[backend_target][1]

model = YuNet(
    modelPath=model_path,
    inputSize=[320,320],
    confThreshold=0.9,
    nmsThreshold=0.3,
    topK=5000,
    backendId=backend_id,
    targetId=target_id)

def ai_crop_poster(fanart, poster='', hw_ratio=1.42):
    image = cv.imread(fanart)
    fanart_h, fanart_w, _ = image.shape
    poster_h = fanart_h
    poster_w = fanart_h / hw_ratio 
    model.setInputSize([fanart_w, fanart_h])
    results = model.infer(image)
    if results.shape[0] == 0: 
        raise Exception("No face detected")
    face = results[0]
    [fx, fy, fw, fh] = face[0:4]
    center_x = fx + fw / 2
    center_y = fy + fh / 2
    poster_left = max(center_x - poster_w / 2, 0)
    poster_left = min(poster_left, fanart_w - poster_w)
    poster_left = int(poster_left)
    cropped = image[0:poster_h, poster_left:int(poster_left+poster_w)]
    cv.imwrite(poster, cropped) 
