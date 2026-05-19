# PyInstaller spec — one-file build of the Immortal-Zip GUI.
# Used on Windows, macOS, and Linux runners.

import os
import sys

block_cipher = None
here = os.path.abspath(os.path.dirname(SPEC))
root = os.path.abspath(os.path.join(here, os.pardir))

a = Analysis(
    [os.path.join(root, 'build', 'launcher.py')],
    pathex=[root],
    binaries=[],
    datas=[],
    hiddenimports=['immortal_zip', 'immortal_zip.cli', 'immortal_zip.gui', 'immortal_zip.core'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'PIL', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'darwin':
    icon = os.path.join(root, 'build', 'immortal-zip.icns')
elif sys.platform == 'win32':
    icon = os.path.join(root, 'build', 'immortal-zip.ico')
else:
    icon = os.path.join(root, 'build', 'immortal-zip-1024.png')

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='immortal-zip',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon if os.path.exists(icon) else None,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='Immortal-Zip.app',
        icon=icon if os.path.exists(icon) else None,
        bundle_identifier='io.github.socrtwo.immortalzip',
        info_plist={
            'CFBundleName': 'Immortal-Zip',
            'CFBundleDisplayName': 'Immortal-Zip',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.13.0',
        },
    )
