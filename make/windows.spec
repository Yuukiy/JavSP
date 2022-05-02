# -*- mode: python ; coding: utf-8 -*-
import os
import inspect
import cloudscraper

block_cipher = None
cloudscraper_dir = os.path.dirname(inspect.getfile(cloudscraper))
cloudscraper_json = cloudscraper_dir + '/user_agent/browsers.json'

# generate crawlers list
all_crawlers = []
exclude_files = ('base', 'proxyfree', 'translate')
for file in os.listdir('web'):
    name, ext = os.path.splitext(file)
    if ext == '.py' and name not in exclude_files:
        all_crawlers.append('web.' + name)

# workaround for a bug of PyInstaller since 5.0: https://github.com/pyinstaller/pyinstaller/issues/6759
ico_file = os.path.abspath(os.path.join(SPECPATH, "../image/JavSP.ico"))

# pyinstaller locates path relative to the .spec file
a = Analysis(['../JavSP.py'],
             pathex=['build'],
             binaries=[],
             datas=[
                 (cloudscraper_json, 'cloudscraper/user_agent'),
                 ("../core/config.ini", "."),
                 ("../data/*.*", "data"),
                 (ico_file, "image")
             ],
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
