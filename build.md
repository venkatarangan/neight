# Neight — Build and Developer Guide

This document covers everything needed to run Neight from source, build distributable packages, and manage releases.

---

## Running from Source

```bash
git clone https://github.com/venkatarangan/neight.git
cd neight
python -m pip install --upgrade pip
pip install -r requirements.txt
python neight.py
```

### Requirements

- Python 3.10+
- PySide6 6.x (Qt 6)
- markdown
- pillow (for design helpers only)
- pyinstaller (only if building distributables)

See [requirements.txt](requirements.txt) for the exact pinned versions.

> Neight uses **PySide6 exclusively**. There is no Qt5 fallback.

---

## Version Numbering

Versions follow the format `YYYY.NNN` — a four-digit year and a three-digit build counter that resets to `001` at the start of each new year.

Examples: `2026.043`, `2026.044`, `2027.001`

`increment_version.py` handles all version bumping automatically. It is called by the build scripts and should not be run manually in normal workflows.

```
python increment_version.py    # bumps version in neight.py
```

---

## In-App Update Checker

Neight checks for updates by querying the GitHub Releases API at startup:

```
https://api.github.com/repos/venkatarangan/neight/releases/latest
```

The app reads the `tag_name` of the latest published release (e.g. `v2026.045`), strips the `v` prefix, and compares it against the running `VERSION`. If the release tag is newer, a subtle badge appears on the Help menu and a brief status bar message is shown. No dialog interrupts the user.

The update checker is also accessible from **Help → Check for Updates...**

**Users only see an update notification when you explicitly publish a GitHub Release.** Building and pushing code does not trigger any notification.

---

## Windows Build

### Prerequisites

- Python 3.10+ with pip
- PyInstaller installed in the active environment

### Build command

```bat
buildme.bat
```

### What it does

1. Calls `increment_version.py` — increments the version number in `neight.py`
2. Runs PyInstaller to produce `dist/Neight.exe` (single-file, windowed)
3. Prints a reminder with the exact command to publish the release

### After building

Commit and push `neight.py`. Then run the release script when ready to publish:

```bat
powershell -ExecutionPolicy RemoteSigned -File release_windows.ps1
```

### Manual build (without the script)

```bat
python increment_version.py
pyinstaller --name Neight --onefile --windowed --icon neight.ico --add-data "neight.ico;." neight.py
```

---

## macOS Build

### Prerequisites

- Python 3.10+ with pip
- PyInstaller installed in the active environment
- `codesign` (Xcode command line tools) — already present on any macOS developer machine
- `ditto` — pre-installed on macOS

### Workflow overview

| Step | Command | What happens |
|---|---|---|
| 1. Build unsigned app | `./buildme_mac_app.sh` | Version incremented in `neight.py`, app built, ad-hoc signed, `dist/Neight-mac-arm64-unsigned.app.zip` created |
| 2. Sign externally | *(manual step)* | Replace `dist/Neight.app` with the externally signed and notarized version |
| 3. Re-zip signed app | `ditto -c -k --sequesterRsrc --keepParent dist/Neight.app stable/Neight-mac-arm64-signed.zip` | Creates the signed zip in `stable/` |
| 4. Publish release | `./release_macos.sh` | Uploads `stable/Neight-mac-arm64-signed.zip` to GitHub Releases |

> `stable/Neight-mac-arm64-signed.zip` is the only file the release script accepts. The `-unsigned` zip can never accidentally reach end users through the release script.

### Step 1 — Unsigned build

```bash
chmod +x buildme_mac_app.sh
./buildme_mac_app.sh
```

This:

1. Increments the version in `neight.py`
2. Cleans old build artifacts
3. Runs PyInstaller from `Neight.spec`
4. Applies an ad-hoc signature (`codesign --sign -`) for local integrity
5. Creates `dist/Neight-mac-arm64-unsigned.app.zip` for test distribution

The ad-hoc signature is not a Developer ID signature. First-time users will need to right-click → Open, or run:

```bash
xattr -dr com.apple.quarantine /Applications/Neight.app
```

### Step 2 — External signing

Replace `dist/Neight.app` with the signed and notarized version provided externally.

### Step 3 — Re-zip the signed app

```bash
ditto -c -k --sequesterRsrc --keepParent dist/Neight.app stable/Neight-mac-arm64-signed.zip
```

### Step 4 — Publish signed release

```bash
./release_macos.sh
```

See [Release Scripts](#release-scripts) below.

### Manual macOS build (without the script)

```bash
python3 increment_version.py
pyinstaller Neight.spec
codesign --force --deep --sign - dist/Neight.app
```

---

## Release Scripts

Two scripts publish builds to GitHub Releases. Both require the **GitHub CLI** (`gh`) — install it from [cli.github.com](https://cli.github.com) and authenticate once with `gh auth login`.

### Windows — `release_windows.ps1`

```bat
powershell -ExecutionPolicy RemoteSigned -File release_windows.ps1
```

- Reads `VERSION` from `neight.py` and derives the tag (e.g. `v2026.045`)
- Checks that `dist\Neight.exe` exists
- Creates a new GitHub Release with that tag, or uploads to it if it already exists
- Uses `release_install_notes.md` as the release body

### macOS — `release_macos.sh`

```bash
./release_macos.sh
```

- Reads `VERSION` from `neight.py` and derives the tag
- Checks that `stable/Neight-mac-arm64-signed.zip` exists (unsigned zip is intentionally rejected)
- Creates a new GitHub Release with that tag, or uploads to it if it already exists
- Uses `release_install_notes.md` as the release body

### Typical full release

1. **Windows machine:** `buildme.bat` → `powershell -ExecutionPolicy RemoteSigned -File release_windows.ps1`
2. **Mac machine:** `./buildme_mac_app.sh` → sign → re-zip → `./release_macos.sh`

Both scripts target the same tag, so running them in either order results in one release with both platform binaries.

---

## The `Neight.spec` File

The macOS build uses a committed `Neight.spec` file rather than a bare `pyinstaller` command, so that `info_plist`, `argv_emulation`, icon paths, and other bundle settings are preserved consistently across builds. Do not regenerate the spec file from scratch — edit it directly when bundle parameters need changing.

---

## Design Helpers

The `design/` folder contains standalone scripts used to generate icons and social preview images. These are not part of the app build.

| Script | Purpose |
|---|---|
| `design/gen_neight_icon.py` | Generates the app icon (dark variant) |
| `design/gen_neight_icon_white.py` | Generates the app icon (light/white variant) |
| `design/gen_social_preview.py` | Generates the GitHub social preview image |

Run them with `python design/<script>.py` when regenerating assets.

---

## Repository Layout (developer view)

```
neight.py                  Main application source
neight.ico / neight.icns   App icons (Windows / macOS)
Neight.spec                PyInstaller spec for macOS bundle
buildme.bat                Windows build script
buildme_mac_app.sh         macOS build script
release_windows.ps1        Publishes Windows build to GitHub Releases
release_macos.sh           Publishes macOS build to GitHub Releases
release_install_notes.md   Release body text shown on every GitHub Release
increment_version.py       Version bump utility
requirements.txt           Python dependencies
settings.json              Default / dev settings file
dist/
  Neight.exe               Windows distributable (committed)
  Neight-mac-arm64-unsigned.app.zip   Unsigned macOS build (committed, for test distribution)
stable/
  Neight-mac-arm64-signed.zip   Signed macOS build (committed, uploaded to GitHub Releases)
design/                    Icon and social preview generation scripts
screenshots/               App screenshots used in README
knownbugs/                 Known Qt-level issues
changes/                   Changelog entries
```
