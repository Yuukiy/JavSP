from javsp.config import YufaceEngine
from javsp.cropper.interface import Cropper, DefaultCropper
from javsp.cropper.yuface_crop import YufaceCropper

def get_cropper(engine: YufaceEngine | None) -> Cropper:
    if engine is None:
        return DefaultCropper()
    if engine.name == 'yuface':
        return YufaceCropper()
