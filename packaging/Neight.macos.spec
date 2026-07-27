# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the macOS .app bundle build of Neight.
#
# This file is version-controlled and is the source of truth for macOS builds.
# Run it from the repository root:
#
#     pyinstaller packaging/Neight.macos.spec
#
# buildme_mac_app.sh does exactly that.
#
# Previously no spec was committed at all (`*.spec` was ignored wholesale), and
# the untracked local Neight.spec was a Windows EXE spec that buildme.bat
# regenerated on every Windows build.  A clean clone therefore could not produce
# the macOS bundle the build script and DEVELOPER.md describe.
#
# NOTE: this spec has not been executed on macOS hardware.  Verify the generated
# Info.plist (bundle identifier, version, document types) before the next
# release, per the release checklist.

a = Analysis(
    ['../neight.py'],
    pathex=[],
    binaries=[],
    datas=[('../neight.icns', '.')],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='Neight',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    # Lets a file dragged onto the app, or opened via "Open With", arrive in
    # sys.argv as well as through the QFileOpenEvent path in NeightApplication.
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Neight',
)

app = BUNDLE(
    coll,
    name='Neight.app',
    icon='../neight.icns',
    bundle_identifier='com.venkatarangan.neight',
    info_plist={
        'CFBundleName': 'Neight',
        'CFBundleDisplayName': 'Neight',
        'CFBundleExecutable': 'Neight',
        'CFBundlePackageType': 'APPL',
        'NSHighResolutionCapable': True,
        # Neight is a document-based editor; without these it cannot be chosen
        # from Finder's "Open With" menu or set as the default .txt handler.
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Plain Text Document',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Alternate',
                'LSItemContentTypes': [
                    'public.plain-text',
                    'public.utf8-plain-text',
                    'public.text',
                ],
            },
            {
                'CFBundleTypeName': 'Markdown Document',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Alternate',
                'LSItemContentTypes': ['net.daringfireball.markdown'],
            },
        ],
    },
)
