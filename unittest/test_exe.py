import os
import sys
import random
import string
import shutil
from glob import glob

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config import cfg


def test_javsp_exe():
    cwd = os.getcwd()
    dist_dir = os.path.normpath(os.path.join(os.path.dirname(__file__) + '/../dist'))
    os.chdir(dist_dir)

    size = cfg.File.ignore_video_file_less_than
    tmp_folder = 'TMP_' + ''.join(random.choices(string.ascii_uppercase, k=6))
    FILE = '300MAAN-642.RIP.f4v'
    try:
        os.system(f"fsutil file createnew {FILE} {size}")
        exit_code = os.system(f"JavSP.exe --auto-exit --input . --output {tmp_folder}")
        assert exit_code == 0, f"Non-zero exit code: {exit_code}"
        # Check generated files
        files = glob(tmp_folder + '/**/*.*', recursive=True)
        assert all('横宮七海' in i for i in files), "Actress name not found"
        assert any(i.endswith('fanart.jpg') for i in files), "fanart not found"
        assert any(i.endswith('poster.jpg') for i in files), "poster not found"
        assert any(i.endswith('.f4v') for i in files), "video file not found"
        assert any(i.endswith('.nfo') for i in files), "nfo file not found"
    finally:
        if os.path.exists(FILE):
            os.remove(FILE)
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)
        os.chdir(cwd)

