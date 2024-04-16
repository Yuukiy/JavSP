#!/usr/bin/env python

import os
import shutil
import subprocess
import sys
import platform
from pathlib import Path
import PyInstaller.__main__

def get_version():
    auto_ver = ""
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
    return auto_ver

def gen_ver_hook(version, hook_file):
    with open(hook_file, 'wt', encoding='utf-8') as f:
        f.write('import sys\n')
        f.write("setattr(sys, 'javsp_version', '" + version + "')\n")

def main():
    version = get_version()
    print(f"Packaging JavSP {version}...")

    script_path = Path(os.path.dirname(os.path.realpath(__file__)))
    os.chdir(script_path)

    gen_ver_hook(version, 'ver_hook.py')

    PyInstaller.__main__.run([
        '--clean',
        './build.spec'
    ])

    # create zip
    sys_info = platform.uname()
    zip_file = f'dist/JavSP-{version}-{sys_info.system}-{sys_info.machine}.zip'
    shutil.make_archive(zip_file, 'zip', 'dist')

    os.remove('ver_hook.py')

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[-1] == 'version':
        print(get_version())
    else:
        main()
