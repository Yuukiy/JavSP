import os
import random
import string
import shutil
import subprocess
from glob import glob


def test_javsp_exe():
    cwd = os.getcwd()
    dist_dir = os.path.normpath(os.path.join(os.path.dirname(__file__) + '/../dist'))
    os.chdir(dist_dir)

    size = 300 * 2**20
    tmp_folder = '.TMP_' + ''.join(random.choices(string.ascii_uppercase, k=6))
    FILE = '300MAAN-642.RIP.f4v'
    try:
        os.system(f"fsutil file createnew {FILE} {size}")
        r = subprocess.run(f"JavSP.exe --auto-exit --input . --output {tmp_folder}".split(), capture_output=True, encoding='utf-8')
        print(r.stdout, r.stderr.encode().decode("unicode_escape"), sep='\n')
        r.check_returncode()
        # Check generated files
        files = glob(tmp_folder + '/**/*.*', recursive=True)
        print('\n'.join(files))
        # assert all('横宮七海' in i for i in files), "Actress name not found"
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
