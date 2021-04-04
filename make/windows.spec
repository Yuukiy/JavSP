# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


# pyinstaller locates path relative to the .spec file
a = Analysis(['../JavSP.py'],
             pathex=['build'],
             binaries=[],
             datas=[
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
