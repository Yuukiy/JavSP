# -*- mode: python ; coding: utf-8 -*-
# JavSP macOS 打包配置（onedir 模式：可执行文件 + config.yml/data/image 独立放置）

import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# playwright 需要完整收集（含 driver）
playwright_datas, playwright_binaries, playwright_hiddenimports = collect_all('playwright')

a = Analysis(
    ['javsp/__main__.py'],
    pathex=[os.path.abspath('.')],
    binaries=playwright_binaries,
    datas=[
        ('data', 'data'),
        ('image', 'image'),
    ] + playwright_datas,
    hiddenimports=[
        'javsp.web.airav', 'javsp.web.arzon', 'javsp.web.arzon_iv', 'javsp.web.avsox',
        'javsp.web.avwiki', 'javsp.web.dl_getchu', 'javsp.web.exceptions', 'javsp.web.fanza',
        'javsp.web.fc2', 'javsp.web.fc2fan', 'javsp.web.fc2ppvdb', 'javsp.web.gyutto',
        'javsp.web.jav321', 'javsp.web.javbus', 'javsp.web.javdb', 'javsp.web.javlib',
        'javsp.web.javmenu', 'javsp.web.mgstage', 'javsp.web.njav', 'javsp.web.prestige',
        'javsp.web.proxyfree', 'javsp.web.translate',
        'pendulum',
    ] + playwright_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['unittest', 'pytest', 'torch',
              'PyQt6', 'PySide6', 'matplotlib', 'pandas', 'numpy', 'scipy',
              'IPython', 'zmq', 'jupyter', 'notebook', 'sqlalchemy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JavSP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # 需要终端交互（番号确认），保留控制台
    icon='image/JavSP.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='JavSP',
)
