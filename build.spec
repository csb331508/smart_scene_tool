# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller build script for Scene Segmentation Tool
Builds a standalone Windows executable with all dependencies bundled
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

block_cipher = None

# Collect TensorFlow data files and submodules
tensorflow_datas = collect_data_files('tensorflow')
tensorflow_hiddenimports = collect_submodules('tensorflow')

# Collect MoviePy data files
moviepy_datas = collect_data_files('moviepy')

# Collect package metadata (fixes importlib.metadata errors)
# Use try-except because not all packages may have metadata
all_metadata = []
try:
    all_metadata.extend(copy_metadata('imageio'))
except Exception:
    pass
try:
    all_metadata.extend(copy_metadata('moviepy'))
except Exception:
    pass
try:
    all_metadata.extend(copy_metadata('decorator'))
except Exception:
    pass
try:
    all_metadata.extend(copy_metadata('proglog'))
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # TransNetV2 model weights
        ('transnetv2-weights', 'transnetv2-weights'),
        # TensorFlow data files
        *tensorflow_datas,
        # MoviePy data files
        *moviepy_datas,
        # Package metadata (fixes importlib.metadata errors)
        *all_metadata,
    ],
    hiddenimports=[
        # Core dependencies
        'tensorflow',
        'numpy',
        'moviepy',
        'moviepy.editor',
        'moviepy.video.io.VideoFileClip',
        # TensorFlow submodules
        *tensorflow_hiddenimports,
        # PyQt6
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # ImageIO (for MoviePy)
        'imageio',
        'imageio.core',
        'imageio.plugins',
        # Additional modules
        'PIL',
        'json',
        'pathlib',
        'subprocess',
        're',
        'random',
        'math',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary packages to reduce size
        'matplotlib',
        'scipy',
        'pandas',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
    ],
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
    name='双星科技场景智能分割工具 v1.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for main application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ico.ico',  # Program icon
)
