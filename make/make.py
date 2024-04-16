#!/usr/bin/env python

import subprocess
import os
from pathlib import Path
import PyInstaller.__main__
import shutil

def main():

    script_path = Path(os.path.dirname(os.path.realpath(__file__)))

    project_root = script_path / ".."
    os.chdir(str(project_root))

    run = subprocess.run(['git', 'describe', '--tags', '--long'], capture_output=True, encoding='utf-8')
    if run.returncode == 0:
        desc = run.stdout.strip()
        tag_name, minor, _ = desc.split('-')
        if int(minor) == 0: # means current commit exactly matches the tag
            auto_ver = tag_name
        else:
            if tag_name.count('.') == 1:
                auto_ver = tag_name + '.0.' + minor
            else:
                auto_ver = tag_name + '.' + minor
    else:
        auto_ver = "v0.unknown"

    with open('ver_hook.py', 'wt', encoding='utf-8') as f:
        f.write('import sys\n')
        f.write("setattr(sys, 'javsp_version', '" + auto_ver + "')\n")

    PyInstaller.__main__.run([
        '--clean',
        './make/build.spec'
    ])

    os.remove('ver_hook.py')
    try: 
        os.remove('dist/config.ini')
    except FileNotFoundError:
        pass # if the file doesn't exist, it's OK
    try: 
        shutil.rmtree('./dist/data')
    except FileNotFoundError:
        pass # if the files doesn't exist, it's OK
    shutil.copytree('./data', './dist/data')

if __name__ == "__main__":
    main()
