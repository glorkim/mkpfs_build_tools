# -*- mode: python ; coding: utf-8 -*-
# Builds the standalone GPL-3.0 mkpfs-worker.exe.
# This exe bundles the GPL `mkpfs` package — that is fine; the worker is GPL.
# The closed-source caller (mkpfs_builds.exe) must NOT bundle mkpfs and only
# invokes this exe as a subprocess.

import os
from PyInstaller.utils.hooks import collect_submodules

ROOT = os.path.dirname(os.path.abspath(SPEC))

hiddenimports = collect_submodules('mkpfs') + ['mkpfs_worker', 'mkpfs_worker.cli']

a = Analysis(
    [os.path.join(ROOT, 'mkpfs_worker_launcher.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'LICENSE'), '.'),
        (os.path.join(ROOT, 'NOTICE'), '.'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mkpfs-worker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
