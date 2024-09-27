from PIL import Image
from javsp.cropper.interface import Cropper, DefaultCropper
from javsp.cropper.utils import get_bound_box_by_face
from slimeface import detectRGB

class SlimefaceCropper(Cropper):
    def crop_specific(self, fanart: Image.Image, ratio: float) -> Image.Image:
        try: 
            bbox_confs = detectRGB(fanart.width, fanart.height, fanart.convert('RGB').tobytes())
            bbox_confs.sort(key=lambda conf_bbox: -conf_bbox[4]) # last arg stores confidence
            face = bbox_confs[0][:-1]
            poster_box = get_bound_box_by_face(face, fanart.size, ratio)
            return fanart.crop(poster_box)
        except:
            return DefaultCropper().crop_specific(fanart, ratio)

if __name__ == '__main__':
    from argparse import ArgumentParser

    arg_parser = ArgumentParser(prog='slimeface crop')

    arg_parser.add_argument('-i', '--image', help='path to image to detect')

    args, _ = arg_parser.parse_known_args()

    if(args.image is None):
        print("USAGE: slimeface_crop.py -i/--image [path]")
        exit(1)

    input = Image.open(args.image)
    im = SlimefaceCropper().crop(input)
    im.save('output.png')

