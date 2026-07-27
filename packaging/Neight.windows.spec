# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the Windows build of Neight.
#
# This file is version-controlled and is the source of truth for Windows builds.
# Run it from the repository root:
#
#     pyinstaller packaging/Neight.windows.spec
#
# buildme.bat does exactly that.  Do NOT build with a bare
# `pyinstaller ... neight.py` command line: that regenerates a spec file and
# silently discards whatever is configured here.

a = Analysis(
    ['../neight.py'],
    pathex=[],
    binaries=[],
    datas=[('../neight.ico', '.')],
    # Pygments is reached only through Markdown's codehilite extension, which is
    # itself loaded by name through entry points.  Naming it here guarantees
    # PyInstaller's bundled hook-pygments runs and collects the lexers and styles
    # it loads dynamically; without them code blocks ship unhighlighted.
    hiddenimports=['pygments'],
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
    name='Neight',
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
    icon=['../neight.ico'],
)
