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

Clone the repository, create a virtual environment, and install only the
runtime dependencies.

### Windows (PowerShell)

```powershell
git clone https://github.com/venkatarangan/neight.git
cd neight
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python neight.py
```

### macOS / Linux

```bash
git clone https://github.com/venkatarangan/neight.git
cd neight
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python neight.py
```

## Building from Source

Developers who intend to build distributables or contribute changes should
install both the runtime and development dependencies in a virtual environment.

### Windows (PowerShell)

```powershell
git clone https://github.com/venkatarangan/neight.git
cd neight
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
```

### macOS / Linux

```bash
git clone https://github.com/venkatarangan/neight.git
cd neight
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
```

> **Important:** `pre-commit install` activates the git hooks defined in `.pre-commit-config.yaml`, including the Tamil spelling guard. Run it once after every fresh clone. Without it the hook is silently inactive. See [Tamil Text Safeguards](#tamil-text-safeguards) for details.

## Requirements

- Python 3.10+ (built and tested on 3.12)
- PySide6 / shiboken6 6.11.1 (Qt 6) — pinned
- Markdown 3.10.2 — pinned
- Pygments 2.20.0 — pinned

Runtime dependencies are in [requirements.txt](requirements.txt), pinned so a
release can be reproduced. A Qt minor release can change text layout, cursor
geometry and Tamil shaping without a line of Neight changing, so bump the pin
deliberately and re-run the cross-platform checks.

Build and design tools are separate, in [requirements-dev.txt](requirements-dev.txt):
`pyinstaller` (distributables), `pillow` (design asset generation only — not
imported by the application), and `pre-commit` (repository hooks).
[requirements-build.txt](requirements-build.txt) contains only the pinned
PyInstaller version for clean distributable builds.

> Neight uses **PySide6 exclusively**. All PyQt5 references have been removed. There is no Qt5 fallback.

---

## Building Distributables

### Windows build

The standard build script increments the version number automatically and then runs PyInstaller.

```bat
buildme.bat
```

For a release build, use a fresh virtual environment containing
`requirements.txt` plus the pinned PyInstaller version. Do not build a release
from the general development environment: optional design and presentation
packages can be discovered by PyInstaller hooks and silently added to the
executable even though Neight never imports them.

What it does:
1. Runs `python increment_version.py` to bump `VERSION` in `neight.py`
2. Runs PyInstaller from the checked-in spec: `pyinstaller packaging\Neight.windows.spec`
3. Produces `dist\Neight.exe`
4. Publishes `dist\Neight.exe` to the `dist-latest` branch on a best-effort
   basis without changing the working tree

After a successful build the script prints a reminder:

```
To release this build to GitHub, run:
  powershell -ExecutionPolicy RemoteSigned -File release_windows.ps1
```

### macOS build

The build script targets Apple Silicon (arm64). Run it on an Apple Silicon Mac.
Use a dedicated build environment containing only runtime dependencies and
PyInstaller. This prevents optional design or presentation packages from being
discovered and bundled by PyInstaller hooks.

```bash
git clone https://github.com/venkatarangan/neight.git
cd neight
python3 -m venv .venv-build
source .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-build.txt
./buildme_mac_app.sh
```

What it does:
1. Verifies that it is running on Apple Silicon in an activated virtual environment
2. Runs `python increment_version.py` to bump `VERSION` in `neight.py`
3. Cleans `build/`, `dist/Neight`, `dist/Neight.app`, and Python test caches
4. Runs the active environment's PyInstaller against `packaging/Neight.macos.spec` (the checked-in spec preserves `BUNDLE`, `info_plist`, `argv_emulation`, and file-type associations)
5. Applies an ad-hoc code signature (`codesign --force --deep --sign -`)
6. Zips the result to `dist/Neight-mac-arm64-unsigned.app.zip`
7. Publishes the unsigned zip to the `dist-latest` branch on a best-effort
   basis without changing the working tree

After a successful build the script prints the next steps for creating a signed release.

> Tested on Apple Silicon. The checked-in build workflow intentionally rejects
> Intel hosts because the distributed macOS artifact is arm64-only.

---

## Releasing to GitHub

Releases are published using the [GitHub CLI (`gh`)](https://cli.github.com). Install it once and authenticate:

```bash
gh auth login
```

> **Commit the version bump before releasing.** The build scripts update
> `VERSION` in the working tree, while GitHub creates a new release tag at the
> current `HEAD` commit. Review the build, update the release notes, commit the
> new version directly to `main`, and push it before running either release
> script. Otherwise the tag name can describe the newly built version while
> pointing to source that still contains the previous version.

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

## Microsoft Store (MSIX) Packaging

Neight's `.exe` triggers SmartScreen warnings for new users because it isn't
signed by a certificate with an established reputation. Publishing through
the Microsoft Store sidesteps that entirely — the Store re-signs every
package with its own certificate on publish, so an end user never sees a
SmartScreen prompt. Registration is free for an individual developer account
(Microsoft dropped the old $19 fee).

This packages the existing `Neight.exe` as a classic Win32 app under the
**Desktop Bridge** (`EntryPoint="Windows.FullTrustApplication"`), not as a
native UWP rewrite — no application source changes are needed.

### One-time account setup (manual, only you can do this)

1. Register a free individual developer account at
   [partner.microsoft.com/dashboard](https://partner.microsoft.com/dashboard).
   Identity verification can take a few days.
2. **Apps and games → + New product → reserve the name** `Neight`.
3. Open that app's **Product identity** page (under App management) and copy
   the three values shown there — **Package/Identity/Name**,
   **Package/Identity/Publisher**, **Package/Properties/PublisherDisplayName**
   — into `packaging/msix_identity.json`, replacing the `REPLACE_ME`
   placeholders exactly as shown. Do not guess these values; they must match
   Partner Center's records byte-for-byte or the package will be rejected.

### Building the package

```powershell
buildme.bat                # produces dist\Neight.exe, as usual
build_msix.ps1              # produces dist\Neight.msix
```

`build_msix.ps1`:

- refuses to run while `packaging/msix_identity.json` still has placeholder
  values, or while the working tree has uncommitted changes (same provenance
  discipline as `release_windows.ps1` — the packaged version must match what's
  committed);
- converts Neight's `VERSION` (`"2026.078"`) into the 4-part numeric version
  MSIX requires (`2026.78.0.0`);
- stages `Neight.exe` plus the logo assets from
  `packaging/msix_assets/Assets/` (regenerate them from `neight.ico` any time
  with `python design/gen_msix_assets.py`) and a rendered
  `packaging/AppxManifest.xml.template` into `dist\msix_staging\`;
- runs `makeappx.exe pack` (from the Windows SDK — installed with Visual
  Studio, or standalone from the
  [Windows SDK downloads page](https://developer.microsoft.com/windows/downloads/windows-sdk/))
  to produce `dist\Neight.msix`.

### Testing locally before submitting

Fastest path — no signing needed, just enable **Settings → Privacy & security
→ For developers → Developer Mode** once, then:

```powershell
Add-AppxPackage -Register dist\msix_staging\AppxManifest.xml
```

To test the actual signed `.msix` file (closer to what Partner Center will
receive), run `build_msix.ps1 -Sign`. On first use this creates a throwaway
local test certificate (`packaging\NeightTestCert.pfx`/`.cer`, gitignored —
**never commit these**), signs the package with it, and prints the
`Import-Certificate` / `Add-AppxPackage` commands to trust and install it.
This certificate is for local testing only; it is never uploaded anywhere,
and has no bearing on Store submission.

### Submitting to the Store

Partner Center → your app → **Packages** → upload `dist\Neight.msix`
directly. Partner Center signs it with the Store's own certificate on
publish, so the local test certificate above is not required for submission.
Store listing content (description, screenshots, age rating) is filled in
separately in Partner Center and isn't something a script can meaningfully
automate.

---

## Why `dist/` Isn't on GitHub

`dist/` is gitignored on `main`, and has been since 2026-07-27. It didn't
start that way: `dist/` and `stable/` used to be committed directly, which
meant 127 MB of binaries — 2.68 GB once every past build was counted across
history — so a plain `git clone` pulled down every `.app` and `.exe` ever
built, and every release commit was an opaque binary diff. History was
rewritten with `git-filter-repo` to strip both directories from every commit.
Nothing was lost — every binary had already been published to GitHub
Releases — but see `knownbugs/MACOS-VALIDATION-RESULTS.md` (decision C4) for
the full account, including the safety branch kept in case anything turned
out to be missing.

The practical effect: cloning `main` today gets you a source checkout only.
Binaries live in two places instead —

- **GitHub Releases**, for end users — `releases/latest/download/<asset>`,
  which is what the website and `README.md` link to, and always resolves to
  whatever was published most recently regardless of what's in the tree.
- **The `dist-latest` branch**, for one specific machine consumer, described
  next.

### The `dist-latest` branch

An external code-signing workflow (outside this repo) needs to fetch the
freshly built, *unsigned* Mac and Windows artifacts before they're signed and
released. It does that over a plain `raw.githubusercontent.com` URL — which,
unlike a Release asset, only ever serves a file that is actually committed to
some branch. `dist/` being gitignored on `main` breaks that fetch, and
committing binaries back onto `main` to fix it would undo the entire point of
the rewrite above.

`dist-latest` is a separate branch, unrelated to `main`'s history, that exists
solely to hold the *current* Mac and Windows build artifacts, at these fixed
URLs:

```
https://raw.githubusercontent.com/venkatarangan/neight/dist-latest/dist/Neight-mac-arm64-unsigned.app.zip
https://raw.githubusercontent.com/venkatarangan/neight/dist-latest/dist/Neight.exe
```

Both `buildme_mac_app.sh` and `buildme.bat` publish to it automatically, as
the last step of every successful build — nothing to run separately. Each
publish **amends** the branch's one existing commit and force-pushes, rather
than adding a new commit on top, so the branch is always exactly one commit
holding only the current binaries. Without that, it would slowly turn into
the same kind of binary graveyard `main` used to be, just one branch over. The
macOS and Windows steps each touch only their own file, so either script can
run independently — on its own machine, at its own time — without clobbering
whatever the other has already published. Both run inside a throwaway
temporary clone, so the real working tree (checked out on `main`) is never
touched, and a publish failure — no network, no `origin` remote — is reported
but does not fail the build; the app is already built (and, on macOS, signed)
by that point regardless.

There is nothing to merge or review on this branch. It's a side channel for
one external consumer, not something that ever becomes part of `main`.

---

## Installing an Unsigned macOS Build

Unsigned builds are intended for developers and testers only. If macOS Gatekeeper blocks the app, run this once in Terminal after copying the app to `/Applications`:

```bash
xattr -dr com.apple.quarantine /Applications/Neight.app
```

Alternatively, right-click `Neight.app` in Finder → **Open** → **Open** to bypass Gatekeeper for a one-time launch.

---

## Architecture

Architecture overview for Python developers — covers all seven areas: runtime entry flow, UI & editor engine, persistence & autosave, platform integrations, data locations, outputs, and tech stack. Internal components are shown in white, I/O boundaries in amber, and data/control flow as solid arrows.

![Neight architecture overview for Python developers — runtime entry, UI engine, persistence, platform integrations, data locations, outputs, and tech stack](docs/neight-architecture.png)

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

Neight's macOS app bundle declares support for plain-text (`.txt`, `.text`) and
Markdown (`.md`, `.markdown`) files via its `Info.plist`. This means Finder's
**Open With** menu lists Neight automatically — no manual configuration
required.

**How it works:**

- Right-click any supported plain-text or Markdown file in Finder and choose
  **Open With → Neight**.
- To make Neight the default for a file type, choose **Open With → Other…**,
  select Neight, and tick **Always Open With**. For Markdown, **Help → Debug
  Info** can also set Neight as the default through Launch Services.
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
requirements.txt       — pinned runtime dependencies
requirements-build.txt — minimal pinned distributable build tooling
requirements-dev.txt   — build, design and hook tooling
buildme.bat            — Windows build script
buildme_mac_app.sh     — macOS build script
build_msix.ps1         — packages dist\Neight.exe as a Microsoft Store MSIX
                         (see "Microsoft Store (MSIX) Packaging" above)
packaging/             — the PyInstaller specs the build scripts use:
                         Neight.windows.spec (EXE) and Neight.macos.spec (BUNDLE).
                         These are build inputs, not generated output — do not
                         build with a bare `pyinstaller ... neight.py`, which
                         overwrites a spec instead of using one.
                         Also: AppxManifest.xml.template, msix_identity.json
                         and msix_assets/ for the MSIX package above.
design/                — icon generators, MSIX asset generator, and
                         architecture infographic source
knownbugs/             — documented Qt-level bugs, validation runs and fix records
session-notes/         — per-session handoff records (see "Session notes" above)
tests/                 — regression suite, run in CI on Windows and macOS
screenshots/           — screenshots used in documentation
dist/                  — build output (gitignored — see "Why dist/ Isn't on GitHub")
stable/                — signed macOS release zips (gitignored — see CHANGELOG 2026.070)
CHANGELOG.md           — what changed in each build, tagged by platform
```

Also on GitHub: a `dist-latest` branch, unrelated to `main`'s history, that
exists only to hold the current unsigned Mac and Windows build artifacts for
an external code-signing workflow. See "Why `dist/` Isn't on GitHub" above.

### Session notes

[`session-notes/`](session-notes/) holds a handoff record per working
session — what changed, why, what was verified and how, and what was left open.
Written for a person or an AI assistant starting cold on another machine. Start
with the newest one; **if you are picking this repository up on Windows for the
first time in a while, read its opening section before running `git pull`** —
the July 2026 history rewrite means an old clone cannot fast-forward.

### Regression suite

Plain scripts rather than pytest, so CI needs nothing beyond `requirements.txt`.
Run them before pushing — CI runs exactly these:

```bash
QT_QPA_PLATFORM=offscreen python3 tests/test_startup_settings.py
QT_QPA_PLATFORM=offscreen python3 tests/test_text_integrity.py
QT_QPA_PLATFORM=offscreen python3 tests/test_cursor_layout.py
QT_QPA_PLATFORM=offscreen python3 tests/test_input_gestures.py
```

Each exits non-zero on failure and prints failures as GitHub Actions
annotations. See [tests/README.md](tests/README.md) for what each one guards and
why.

---

## Known Qt Issue

Tamil text navigation in Qt-based editors has a segmentation quirk for some consonant + pulli + consonant combinations. The caret or selection can jump across a whole cluster instead of stepping through individual logical letters.

This is a Qt-level behavior, not specific to Neight. Detailed notes and reproduction examples are in [knownbugs/Bug in QT for Tamil text handling.md](knownbugs/Bug%20in%20QT%20for%20Tamil%20text%20handling.md).

---

## Tamil Text Safeguards

### The problem: LLM tokenization corruption of Tamil vowels

Tamil text in this project is vulnerable to silent corruption by LLMs (including Claude Sonnet 4.6 and GitHub Copilot). These models have a known tokenization bias with Indic scripts that causes them to silently substitute visually similar but phonetically distinct vowel marks. Specifically, they replace the short 'o' vowel ொ with the long 'ō' vowel ோ, producing a word that does not exist in Tamil. We caught this class of bug in output generated by the app itself.

The corrupted form is never correct. It is not a spelling variant — it is a non-word. No developer, tool, or automated system should ever write or commit it.

### Safeguards in place

Three layers of protection have been added to this project:

1. **Pre-commit hook** (`.pre-commit-config.yaml`) — a `pygrep`-based hook scans `.py` and `.html` files for the corrupted form before every commit and aborts with an error if it is found. It also enforces UTF-8 encoding and LF line endings.

2. **GitHub Actions workflow** (`.github/workflows/tamil-guard.yml`) — runs on every push and pull request. Uses `grep -P` (PCRE) to check all `.py` and `.html` files. If the corrupted form is found, the build fails with an explicit error message.

3. **Copilot repository instructions** (`.github/copilot-instructions.md`) —
   tell AI coding tools not to retype, autocomplete, or modify Tamil strings,
   preventing corruption before either automated guard needs to catch it.

### Setup after cloning

After installing the development dependencies as described under
[Building from Source](#building-from-source), activate the hook:

```bash
pre-commit install
```

This is required for the hook to run on `git commit`. Without it, the hook is inactive and the local safeguard is silently bypassed.

**Never disable or bypass the pre-commit hook** (`--no-verify`). The hook exists specifically because the corruption is invisible in most editors — it looks correct on screen but is wrong at the byte level.

### Editor encoding requirements

All source files must be saved as **UTF-8 without BOM**. The pre-commit hook enforces this via `check-byte-order-marker`, but the editor must also be configured correctly:

- The tracked `.editorconfig` sets UTF-8 and LF for the repository.
- In VS Code, set `"files.encoding": "utf8"` and
  `"files.autoGuessEncoding": false` in your user or workspace settings.
- In other editors, ensure UTF-8 without BOM is the default encoding for the
  workspace.

Saving a file in a different encoding (UTF-16, Latin-1, etc.) will corrupt Tamil characters silently and the pre-commit hook will catch it on the next commit.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
