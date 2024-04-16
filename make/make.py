#!/usr/bin/env python

import subprocess
import os
from pathlib import Path
import PyInstaller.__main__
import shutil

from . import gen_ver_hook

def main():

    script_path = Path(os.path.dirname(os.path.realpath(__file__)))
    os.chdir(script_path)

    gen_ver_hook.gen_ver_hook()

    PyInstaller.__main__.run([
        '--clean',
        './build.spec'
    ])

    os.remove('ver_hook.py')

if __name__ == "__main__":
    main()
