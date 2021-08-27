# -*- mode: python ; coding: utf-8 -*-
import os
import inspect
import cloudscraper

block_cipher = None
cloudscraper_dir = os.path.dirname(inspect.getfile(cloudscraper))
cloudscraper_json = cloudscraper_dir + '/user_agent/browsers.json'

# pyinstaller locates path relative to the .spec file
a = Analysis(['../JavSP.py'],
             pathex=['build'],
             binaries=[],
             datas=[
                 (cloudscraper_json, 'cloudscraper/user_agent'),
                 ("../core/config.ini", "."),
                 ("../data/*.*", "data")
             ],
             hiddenimports=[
                 'core/config.py'
             ],
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
          icon='./JavSP.ico')
