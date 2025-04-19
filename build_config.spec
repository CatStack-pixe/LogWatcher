# -*- mode: python ; coding: utf-8 -*-
import sys
import site
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
project_root = Path('.').absolute()

# 收集数据文件
datas = []
datas.extend([(str(project_root / 'resources'), 'resources')])
datas.extend(collect_data_files('ttkbootstrap'))
datas.extend(collect_data_files('matplotlib'))
datas.extend(collect_data_files('tkinterdnd2'))

# 收集 tkdnd DLL 和相关文件
binaries = []
try:
    # 在 site-packages 中查找 tkdnd
    tkdnd_paths = []
    for site_path in site.getsitepackages():
        tkdnd_path = Path(site_path) / 'tkinterdnd2' / 'tkdnd'
        if tkdnd_path.exists():
            tkdnd_paths.append(tkdnd_path)
            
    # 在 Python 安装目录中查找
    python_tkdnd = Path(sys.prefix) / 'tcl' / 'tkdnd2.8'
    if python_tkdnd.exists():
        tkdnd_paths.append(python_tkdnd)
        
    # 添加找到的 tkdnd 路径
    for tkdnd_path in tkdnd_paths:
        print(f'Found tkdnd at: {tkdnd_path}')
        binaries.extend([(str(p), f'tkdnd/{p.name}') for p in tkdnd_path.glob('*.*')])
except Exception as e:
    print(f'Warning: Error collecting tkdnd files: {e}')

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'tkinter',
        'tkinterdnd2',
        'ttkbootstrap',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LogWatcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 临时设置为True以便查看错误信息
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico'
)