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
# This spec has been validated from a clean clone on Apple Silicon. The
# generated bundle launched, passed codesign verification, carried the source
# version, and registered its plain-text and Markdown document types.

import re
from pathlib import Path

_neight_source = (Path(SPECPATH) / '..' / 'neight.py').read_text(encoding='utf-8')
_version_match = re.search(r'^VERSION = "(\d{4}\.\d{3})"', _neight_source, re.MULTILINE)
if not _version_match:
    raise SystemExit("Could not find VERSION in neight.py")
APP_VERSION = _version_match.group(1)

a = Analysis(
    ['../neight.py'],
    pathex=[],
    binaries=[],
    datas=[('../neight.icns', '.')],
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
    # Apple Silicon only.  Intel and any macOS predating Apple Silicon are
    # out of scope, so there is no universal2 slice to build or test.
    target_arch='arm64',
    codesign_identity=None,
    # Deliberately None even though packaging/Neight.entitlements exists.
    # PyInstaller applies this file whether or not codesign_identity is set --
    # it ad-hoc signs the bootloader either way -- so naming it here stamps
    # com.apple.security.app-sandbox onto the direct-download build, which has
    # no provisioning profile to make a sandbox survivable.  The Store signing
    # step runs elsewhere and passes the entitlements itself; see DEVELOPER.md.
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
    bundle_identifier='com.murasu.neight',
    info_plist={
        'CFBundleName': 'Neight',
        'CFBundleDisplayName': 'Neight',
        'CFBundleExecutable': 'Neight',
        'CFBundlePackageType': 'APPL',
        'CFBundleShortVersionString': APP_VERSION,
        'CFBundleVersion': APP_VERSION,
        'NSHighResolutionCapable': True,
        # The lowest macOS this project intends to support.  Nothing targets
        # Intel, so the only question is how far back on Apple Silicon to go,
        # and PySide6 6.11 sets the answer: its own bindings -- QtCore.abi3.so,
        # QtWidgets.abi3.so, libpyside6 -- are built with minos 15.0, and every
        # run imports them.  Below 15.0 is not reachable without changing Qt.
        #
        # This key is a claim, not a fact, and shipping a claim lower than the
        # truth is worse than shipping an honest higher one: macOS installs the
        # app and then it fails to launch.  buildme_mac_app.sh measures every
        # Mach-O in the finished bundle and raises this value if the toolchain
        # actually needs more (a Homebrew Python, for instance, is built for the
        # current macOS and drags the floor up to it), so what ships is always
        # true.  Check a built bundle by hand with:
        #   otool -l <binary> | awk '/LC_BUILD_VERSION/{f=1} f&&/minos/{print;exit}'
        'LSMinimumSystemVersion': '15.0',
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
