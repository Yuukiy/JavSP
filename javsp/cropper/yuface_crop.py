from typing import List
from PIL import Image
from javsp.cropper.interface import Cropper, DefaultCropper
from javsp.cropper.utils import get_bound_box_by_face
from yuface import detect
import numpy as np

def pillow2bgr(im: Image.Image) -> List[List[List[int]]]:
    bytes = list(im.convert('RGB').tobytes())
    output: List[List[List[int]]] = []
    ptr = 0
    for col in range(im.width):
        output.append([])
        for _ in range(im.height):
            r, g, b = bytes[ptr:ptr+3]
            output[col].append([b, g, r])
            ptr += 3
    return output

class YufaceCropper(Cropper):
    def crop_specific(self, fanart: Image.Image, ratio: float) -> Image.Image:
        try: 
            image_mat = np.array(fanart.convert('RGB'))[:, :, ::-1]
            confs, bboxes, _ = detect(image_mat)
            conf_bboxes = list(zip(confs, bboxes))
            conf_bboxes.sort(key=lambda conf_bbox: -conf_bbox[0])
            face = conf_bboxes[0][1]
            poster_box = get_bound_box_by_face(face, fanart.size, ratio)
            return fanart.crop(poster_box)
        except Exception as e:
            print("fuck: ", e)
            return DefaultCropper().crop_specific(fanart, ratio)

if __name__ == '__main__':
    from argparse import ArgumentParser

    arg_parser = ArgumentParser(prog='yuface crop')

    arg_parser.add_argument('-i', '--image', help='path to image to detect')

    args, _ = arg_parser.parse_known_args()

    if(args.image is None):
        print("USAGE: yuface_crop.py -i/--image [path]")
        exit(1)

    input = Image.open(args.image)
    im = YufaceCropper().crop(input)
    im.save('output.png')

