# -*- mode: python ; coding: utf-8 -*-
import os
from glob import glob

block_cipher = None

# search and add data files to the bundle
data_dir = './data'
data_files = [
    ("../core/config.ini", ".")
]
for f in glob(data_dir + '/*.*'):
    pair = (os.path.abspath(f), 'data')
    data_files.append(pair)


# pyinstaller locates path relative to the .spec file
a = Analysis(['../JavSP.py'],
             pathex=['build'],
             binaries=[],
             datas=data_files,
             hiddenimports=[
                 'core/config.py'
             ],
             hookspath=[],
             runtime_hooks=[],
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
          console=True , icon='../make/JavSP.ico')
