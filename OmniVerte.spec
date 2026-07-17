# -*- mode: python ; coding: utf-8 -*-

# scipy (pulled in transitively) has a very deep import graph; PyInstaller walks
# it recursively and blows the default 1000-frame limit with a RecursionError.
# Raising the limit is PyInstaller's own recommended workaround.
import sys
sys.setrecursionlimit(sys.getrecursionlimit() * 5)


a = Analysis(
    ['OmniVerte.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('favicon.ico', '.'),  # Include favicon for tray icon
        ('VERSION', '.'),       # About page reads this from the bundle root (_MEIPASS)
    ],
    hiddenimports=[
        # keyring needs the Windows backend bundled explicitly under PyInstaller
        'keyring.backends.Windows',
        'keyring.backends.fail',
        'keyring.backends.null',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',                # Not used - CUDA check via ctranslate2 now
        'torchaudio',           # Not used - sounddevice handles audio
        'torchvision',          # Not used - no image processing
        'matplotlib',           # Not used
        'pandas',               # Not used
        'tkinter',              # Not used - full Qt migration; tkinter.test was the legacy exclude
        'tkinter.test',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# onedir build: the EXE holds only the bootloader + scripts; binaries and datas
# are laid out alongside it by COLLECT into dist/OmniVerte/. This avoids
# onefile's ~30s self-extraction to a temp dir on every launch (a real problem
# for a heavy PySide6 + faster-whisper app) and lets the installer place a plain
# folder under the user's Programs dir.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OmniVerte',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='favicon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OmniVerte',
)
