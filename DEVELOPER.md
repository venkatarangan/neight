# Neight — Developer Reference

This document covers everything relevant to building, running, and understanding Neight from a developer's perspective: source setup, build scripts, architecture, performance design choices, and implementation notes.

For end-user documentation see [README.md](README.md).
For advanced user features see [ADVANCED.md](ADVANCED.md).

---

## Debug Information Panel

Neight includes a built-in debug info panel (**Help → Debug Info…**). It shows the current version, Python and Qt versions, platform details, font configuration, and key runtime settings — useful when troubleshooting an issue or filing a bug report.

![Neight debug info on macOS](screenshots/macos/2026-May-06-mac-debuginfo-screenshot.jpg)

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

See [requirements.txt](requirements.txt) for the current pinned list.

> Neight uses **PySide6 exclusively**. All PyQt5 references have been removed. There is no Qt5 fallback.

---

## Building Distributables

### Windows build

The standard build script increments the version number automatically and then runs PyInstaller.

```bat
buildme.bat
```

What it does:
1. Runs `python increment_version.py` to bump `VERSION` in `neight.py`
2. Runs PyInstaller: `pyinstaller --name Neight --onefile --windowed --icon neight.ico --add-data "neight.ico;." neight.py`
3. Produces `dist\Neight.exe`

After a successful build the script prints a reminder:

```
To release this build to GitHub, run:
  powershell -ExecutionPolicy RemoteSigned -File release_windows.ps1
```

### macOS build

The build script targets Apple Silicon (arm64). Run it on an Apple Silicon Mac.

```bash
chmod +x buildme_mac_app.sh
./buildme_mac_app.sh
```

What it does:
1. Runs `python3 increment_version.py` to bump `VERSION` in `neight.py`
2. Cleans `build/`, `dist/Neight.app`, and `__pycache__`
3. Runs `pyinstaller Neight.spec` (the checked-in spec preserves `info_plist`, `argv_emulation`, and file-type associations)
4. Applies an ad-hoc code signature (`codesign --force --deep --sign -`)
5. Zips the result to `dist/Neight-mac-arm64-unsigned.app.zip`

After a successful build the script prints the next steps for creating a signed release.

> Tested on Apple Silicon. An Intel build would need to be produced on appropriate hardware.

---

## Releasing to GitHub

Releases are published using the [GitHub CLI (`gh`)](https://cli.github.com). Install it once and authenticate:

```bash
gh auth login
```

### Windows release

After `buildme.bat` completes and `dist\Neight.exe` exists:

```powershell
powershell -ExecutionPolicy RemoteSigned -File release_windows.ps1
```

The script reads `VERSION` from `neight.py`, creates a GitHub release tagged `v{VERSION}`, and uploads `dist\Neight.exe`. If a release with that tag already exists it uploads the executable to the existing release instead.

### macOS release — unsigned build

The unsigned zip (`dist/Neight-mac-arm64-unsigned.app.zip`) is for developer testing or sharing with technical users. End users should always use the signed build.

To distribute an unsigned build, share the zip directly — do not publish it as the primary GitHub release asset.

### macOS release — signed build

The recommended workflow:

```
Step 1 — Build:
  ./buildme_mac_app.sh
  → dist/Neight-mac-arm64-unsigned.app.zip and dist/Neight.app

Step 2 — Sign externally (Apple Developer account required):
  Notarize/sign dist/Neight.app through Xcode or notarytool

Step 3 — Re-zip the signed app into stable/:
  ditto -c -k --sequesterRsrc --keepParent dist/Neight.app \
        stable/Neight-mac-arm64-signed.zip

Step 4 — Publish to GitHub:
  ./release_macos.sh
```

`release_macos.sh` reads `VERSION` from `neight.py`, creates a tagged release, and uploads `stable/Neight-mac-arm64-signed.zip`. If a release with that tag already exists, it uploads the zip to the existing release.

> The signed macOS build is contributed by a well-wisher with an Apple Developer account. Without notarization, macOS Gatekeeper may block launch. See the **Installing an unsigned macOS build** section below for the developer workaround.

---

## Installing an Unsigned macOS Build

Unsigned builds are intended for developers and testers only. If macOS Gatekeeper blocks the app, run this once in Terminal after copying the app to `/Applications`:

```bash
xattr -dr com.apple.quarantine /Applications/Neight.app
```

Alternatively, right-click `Neight.app` in Finder → **Open** → **Open** to bypass Gatekeeper for a one-time launch.

---

## Architecture

Architecture infographic (high-level):

![Neight architecture infographic](design/architecture_infographic_readme.png)

Neight is a single-file Python application (`neight.py`) built on PySide6. There are no modules, packages, or service layers — all logic lives in one file for portability and simplicity. The main architectural elements are:

- **`NeightApplication` (QApplication subclass)** — custom app class that handles macOS `QFileOpenEvent` (Apple Events / Open With) both at startup and while running
- **`Notepad` (QMainWindow)** — main window, menus, settings lifecycle
- **`CodeEditor` (QPlainTextEdit subclass)** — the editor widget with custom key handling, drag-drop, font zoom via Ctrl+Scroll, triple-click search, and plain-text paste
- **`SpacedPlainTextDocumentLayout` (QPlainTextDocumentLayout subclass)** — custom layout engine for per-visual-line spacing
- **`WordIndexOverlay` (QWidget)** — floating overlay that numbers each word in the document
- **`FindReplaceDialog` (QDialog)** — modeless find/replace with an escape sequences helper (`\n`, `\t`, `\r`, `\xHH`, `\u0000`, etc.)
- **`LineNumberArea` (QWidget)** — gutter sidebar showing paragraph-level line numbers
- **`ClickableLabel` (QLabel)** — emits a `clicked` signal; used for the Words: status bar label
- **`SettingsManager`** — settings path resolution (primary → fallback), load/save, legacy migration, autosave log path

Dialogs such as the Language Switch settings, Appearance settings, and Reading Time settings are created inline within `Notepad` methods (`_show_keyboards_dialog`, `_show_appearance_dialog`, `_show_reading_time_dialog`). Autosave writes run on a plain `threading.Thread` (not a QThread subclass); results are marshalled back to the UI thread via Qt signals.

---

## Performance Design

Neight is optimized for typing speed. Writers working in long documents, or with non-Latin scripts like Tamil, need the editor to stay fast and out of the way.

Key optimizations:

- **Debounced status bar updates** — word, sentence, and character counts update 250 ms after you stop typing, never on every keystroke. If all counters are hidden, the O(n) full-text copy is skipped entirely.
- **Debounced word-match highlighting** — the whole-document word scan is deferred 80 ms after selection changes, with an early-exit if the selected word has not changed since the last scan.
- **Smart token reuse** — when both word count and reading time are enabled, the word tokenization pass runs only once per update cycle.
- **Auto-save on a background thread** — disk writes run entirely off the UI thread. The document text is snapshotted on the UI thread before the write begins; results are posted back via Qt signals.
- **`contentsChange` signal** — Neight uses Qt's lower-level `contentsChange` signal (which fires with change coordinates) rather than `contentsChanged` (which fires blindly for every event), so updates can be targeted rather than global.
- **Custom line spacing engine** — Qt's `QPlainTextEdit` does not support true line-height adjustments through its standard formatting API. Neight uses a custom `SpacedPlainTextDocumentLayout` subclass that overrides `blockBoundingRect()` to reposition every visual `QTextLine` within each paragraph's layout. This produces genuine per-visual-line spacing — identical in effect to Word's line spacing — so wrapped lines within a paragraph are spaced, not just paragraph breaks.

---

## Implementation Notes

### Sentence count

Sentence count is calculated from sentence-ending punctuation rather than grammar analysis. Neight splits text on common boundaries (`.`, `!`, `?`, and several Unicode equivalents), ignores empty fragments, and counts what remains. Lightweight, fast, and practical for mixed-language drafts.

### macOS Open With

Neight's macOS app bundle declares support for `.txt` and `.text` files via its `Info.plist`. This means Finder's **Open With** menu lists Neight automatically — no manual configuration required.

**How it works:**

- Right-click any `.txt` or `.text` file in Finder and choose **Open With → Neight**.
- To make Neight the default for `.txt` files, choose **Open With → Other…**, select Neight, and tick **Always Open With**.
- When Neight receives a file this way, macOS sends an Apple Event (`QFileOpenEvent`) rather than passing the path through command-line arguments. Neight handles this transparently — the file opens exactly as if you had used **File → Open** from inside the app.
- Files received via **Open With** before the main window is ready are buffered and opened as soon as the window appears, so nothing is lost even during a cold launch.

> The app bundle targets **Apple Silicon (arm64)**. Intel Mac support would require a separate build on appropriate hardware.

### Autosave watchdog and diagnostic log

If an auto-save write fails or a watchdog detects a hung write thread (e.g., on a slow or disconnected network drive), Neight appends a timestamped entry to a diagnostic log file in the same folder as `settings.json`.

The log is named with today's date: `neight_autosave_YYYY-MM-DD.log`. A new file is started each calendar day, so no single log file grows unbounded. Days with no errors produce no file at all.

### Settings validation

All numeric settings loaded from `settings.json` are validated and clamped before use. A corrupted or maliciously crafted settings file cannot cause a crash or out-of-range value being applied to the UI:

- Font size is clamped to 4–256 pt
- Auto-save interval is restricted to the allowed set `{0, 2, 5, 15, 30}` minutes
- Font family must be a string
- File size is checked before loading — files larger than **50 MB** are rejected with a clear error message

### Customizable URL prefixes

Two URL prefixes in `settings.json` can be updated without rebuilding the app:

- `google_search_url_prefix` — used by **Edit → Search with Google** (`Ctrl+E`)
- `sorkuvai_search_url_prefix` — used by the right-click **Search Sorkuvai** context menu item

Update either prefix if the service URLs change.

---

## Project Layout

```
neight.py              — the entire application
neight.ico / .icns     — app icons
requirements.txt       — Python dependencies
buildme.bat            — Windows build script
buildme_mac_app.sh     — macOS build script
Neight.spec            — PyInstaller spec (auto-generated, checked in for reference)
design/                — icon generators and architecture infographic source
knownbugs/             — documented Qt-level bugs and reproduction notes
screenshots/           — screenshots used in documentation
stable/                — signed macOS release zips
```

---

## Known Qt Issue

Tamil text navigation in Qt-based editors has a segmentation quirk for some consonant + pulli + consonant combinations. The caret or selection can jump across a whole cluster instead of stepping through individual logical letters.

This is a Qt-level behavior, not specific to Neight. Detailed notes and reproduction examples are in [knownbugs/Bug in QT for Tamil text handling.md](knownbugs/Bug%20in%20QT%20for%20Tamil%20text%20handling.md).

---

## License

MIT License. See [LICENSE](LICENSE) for details.
