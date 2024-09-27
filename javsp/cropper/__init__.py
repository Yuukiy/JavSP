from javsp.config import SlimefaceEngine
from javsp.cropper.interface import Cropper, DefaultCropper
from javsp.cropper.slimeface_crop import SlimefaceCropper

def get_cropper(engine: SlimefaceEngine | None) -> Cropper:
    if engine is None:
        return DefaultCropper()
    if engine.name == 'slimeface':
        return SlimefaceCropper()
