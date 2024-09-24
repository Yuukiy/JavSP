import os
from typing import List, Tuple
from cx_Freeze import setup, Executable

# https://github.com/marcelotduarte/cx_Freeze/issues/1288
base = None

proj_root = os.path.abspath(os.path.dirname(__file__))


include_files: List[Tuple[str, str]] = [
    (f"{proj_root}/javsp/core/config.ini", 'config.ini'),
    (f"{proj_root}/data", 'data'),
    (f"{proj_root}/image", 'image')
]

includes = []

for file in os.listdir('javsp/web'):
    name, ext = os.path.splitext(file)
    if ext == '.py':
        includes.append('javsp.web.' + name)

build_exe = {
    'include_files': include_files,
    "includes": includes,
    "excludes": ["unittest"],
}

javsp = Executable(
    "./javsp/__main__.py", 
    target_name='JavSP', 
    base=base,
    icon="./image/JavSP.ico",
)

setup(
    name='JavSP',
    options = {'build_exe': build_exe}, 
    executables=[javsp]
)

