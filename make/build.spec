# -*- mode: python ; coding: utf-8 -*-
import os
import inspect
import cloudscraper
import glob

block_cipher = None
cloudscraper_dir = os.path.dirname(inspect.getfile(cloudscraper))
cloudscraper_json = cloudscraper_dir + '/user_agent/browsers.json'

# generate crawlers list (exlcude list is not needed here)
all_crawlers = []
for file in os.listdir('../web'):
    name, ext = os.path.splitext(file)
    if ext == '.py':
        all_crawlers.append('web.' + name)

# workaround for a bug of PyInstaller since 5.0: https://github.com/pyinstaller/pyinstaller/issues/6759
ico_file = os.path.abspath(os.path.join(SPECPATH, "../image/JavSP.ico"))

# pyinstaller locates path relative to the .spec file

datas = [
     (cloudscraper_json, 'cloudscraper/user_agent'),
     ("../core/config.ini", "."),
     ("../image/sub_mark.png", "image"),
     (ico_file, "image")
 ]

# This is so we can preserve the tree structure of the metadata.
globs = ['../data/**/*.json', '../data/**/*.csv']
for glob_pattern in globs:
    for file in list(glob.glob(glob_pattern, recursive=True)):
        dir_path = os.path.dirname(file)
        datas.append((file, os.path.relpath(dir_path, '..')))

extra_toc = Tree('../data', prefix='data', excludes=['.git'])
a = Analysis(['../JavSP.py'],
             pathex=['build'],
             binaries=[],
             datas = datas,
             hiddenimports=all_crawlers,
             hookspath=[],
             runtime_hooks=['ver_hook.py'],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = None
if os.name != 'posix':
    exe = EXE(pyz,
              a.scripts,
              a.binaries,
              a.zipfiles,
              a.datas,
              [],
              name='JavSP',
              debug=False,
              bootloader_ignore_signals=False,
              strip=False,
              upx=True,
              upx_exclude=[],
              runtime_tmpdir=None,
              console=True,
              icon=ico_file)
else:
    exe = EXE(pyz,
              a.scripts,
              a.binaries,
              a.zipfiles,
              a.datas,
              [],
              name='JavSP',
              debug=False,
              bootloader_ignore_signals=False,
              strip=False,
              upx=True,
              upx_exclude=[],
              runtime_tmpdir=None,
              console=True)
              

# vim:set syntax=python:
