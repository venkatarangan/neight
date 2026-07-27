# macOS TODO — Everything Pending

> **This was worked through on 2026-07-27.** Results, the four bugs it found and the five
> items that still need a person are in
> [`MACOS-VALIDATION-RESULTS.md`](MACOS-VALIDATION-RESULTS.md). Read that first; this file
> is kept as the record of what was asked for.

**Written:** 2026-07-27 on Windows 11 · Python 3.12.10 · PySide6 6.11.0
**Applies to:** `neight.py` @ 8,842 lines, `VERSION = "2026.066"`
**Commits this covers:** `7b19c33` (settings/saving/input/build) and `e15bfd0` (Markdown preview)
**Companion:** [`Independent assessment and fix plan.md`](Independent%20assessment%20and%20fix%20plan.md)

---

## How to use this file

On the Mac, open this file and say:

> **"Read `knownbugs/MACOS-TODO-pending-validation.md` and work through it."**

Or pick a single item: *"do item B1 from the macOS TODO."*

This file is written to be **self-contained** — a fresh session has no memory of the Windows work, so everything needed is here: what changed, why, how to test it, and what to do when it breaks.

**Nothing below has ever been executed on macOS.** All of it was written and tested on Windows. Items are ordered by priority within each part.

### First, capture a baseline

```bash
cd /path/to/neight
git log --oneline -3
python3 --version
python3 -c "import PySide6; print('PySide6', PySide6.__version__)"
python3 -c "import markdown; print('markdown', markdown.__version__)"
sw_vers
uname -m
```

Record the PySide6 version. Windows was verified on **6.11.0**; a different version here means we are shipping two different Qt builds, which matters because Qt minor releases change text layout, cursor geometry and Tamil shaping. See **C2**.

### Ground rules

- **Back up `settings.json` before testing.** Find its real path via **Help → Debug Info** — do not assume `~/.config/Neight/`. See **A2**.
- **Never let automated tooling rewrite Tamil strings.** The repo has a pre-commit guard for one misspelling; it does not protect everything.
- Run the regression suite (bottom of this file) after any change.

---

## Part A — Verify the Windows work on real hardware

These are implemented and passing on Windows. They touch platform-specific behaviour and need confirmation here.

### ☐ A1. Pinch-to-zoom — highest risk, entirely new code

`CodeEditor.event()` intercepts `QEvent.Type.NativeGesture` (there is no `nativeGestureEvent` virtual on `QWidget` in PySide6 — I confirmed this and corrected it during implementation). `_handle_native_gesture()` at `neight.py:1988` accumulates `ZoomNativeGesture` values at **0.08 per font point**, and `_native_zoom_active` suppresses the wheel path so one gesture cannot zoom twice.

Synthesised events move the font size correctly. **A real trackpad has never driven it.**

**Test**
1. Open a document; note the font size.
2. Pinch out slowly — size should climb one point at a time, smoothly, no jumps.
3. Pinch in — should fall symmetrically.
4. Pinch fast — must not slam into the 6 pt or 100 pt limit in a single gesture.
5. Two-finger **scroll** (no pinch, no Ctrl) must feel exactly as before — kinetic and native, untouched.

**If wrong:** tune the `0.08` constant in `_handle_native_gesture` — raise it if zoom is too fast, lower it if too slow. If *nothing* happens, log `event.gestureType()` and `event.value()` for a real pinch and report the values; macOS may deliver a different sequence than assumed.

### ☐ A2. Where your settings actually live — do this before any other testing

Open **Help → Debug Info** and read the **Settings JSON** path.

- If it is inside `/Applications/Neight.app/…`, your settings **will be destroyed** when you replace the app. That is the known issue in [`release_install_notes.md`](../release_install_notes.md), and `ADVANCED.md` has been corrected to say so plainly instead of claiming `~/.config/Neight` is always used.
- Debug Info also now shows, in red, if the settings store ever silently relocated after a failed write, plus the last write error.

**Report which path you see.** It decides how urgent **C1** is.

### ☐ A3. The multi-window font bug is actually fixed

This was the open item in [`Issues to fix.md`](Issues%20to%20fix.md): *"when two windows are open, the second doesn't get the font settings correctly."*

**Root cause** (found by reproduction, not inspection): applying settings synchronised checkable `QAction`s without blocking their signals. Any action whose stored value differed from its construction default emitted `toggled()`, whose handler called `_save_preferences()` — at a point where `_settings_cache` was still empty *and before the font was applied at the end of the method*. Every launch therefore transiently wrote Qt's default font to `settings.json`.

Measured on Windows before the fix: one startup rewrote `font_family` `"Nirmala UI" → "Sans Serif"` and `font_size` `14 → 9`.

**Test**
1. Set a distinctive font (e.g. Tamil MN, 20 pt). Quit.
2. Copy `settings.json` (path from A2) somewhere safe.
3. Launch, wait for the window, quit. `diff` the file — only `window_size` may differ.
4. Launch, then **File → New Window**. The second window must show the same font.
5. Close in both orders. The font must survive both.

### ☐ A4. Two windows no longer lose each other's preferences

Settings writes now take a `QLockFile`, carry a `settings_revision`, and merge **only the keys this window changed** over a freshly re-read copy.

**Test:** open two windows. Change the font in A, change margins in B. Close in either order — both changes must survive. Repeat with the other close order.

### ☐ A5. Slow trackpad zoom no longer does nothing

**This was a genuine macOS bug.** `wheelEvent` computed `int(delta / 120)` and only fell back to `pixelDelta` when `angleDelta` was *exactly* zero. A small non-zero `angleDelta` — normal smooth-trackpad output — produced no zoom **and** the event was still `accept()`ed, so Ctrl+trackpad neither zoomed nor scrolled. Deltas are now accumulated with the remainder carried between events (`_consume_zoom_steps`, `neight.py:1917`).

**Test:** hold Ctrl and move two fingers *very slowly*. The size must eventually change. Before, it never would.

### ☐ A6. Markdown split preview

**Markdown → Preview**, `⌘⇧M`. Editor left, rendered Markdown right, divider draggable. `.md`/`.markdown` only. `⌘⇧R` refreshes.

Renderer is Qt's own rich-text engine (`QTextDocument` in a `QTextBrowser`) — the same one that already makes your PDFs, so no new dependency and no size increase (~5.5 KB of code).

**Test**
1. Open a `.md` with mixed Tamil and English. `⌘⇧M` should split the window.
2. **Confirm `⌘⇧M` actually fires.** Qt maps `Ctrl`→`Command` automatically, but this has not been tried on a Mac keyboard. Check it doesn't collide with anything system-level.
3. Drag the divider, quit, reopen — the ratio should be restored.
4. Type — preview follows after a short pause.
5. Switch light/dark (Settings → Appearance). The preview must re-render in the new palette, not stay light.
6. Zoom with `⌘+`/`⌘-` or pinch — preview text should resize too.
7. Open a `.txt` — preview must close and the menu item grey out.
8. Check Tamil in the preview: headings, table cells, deep marks (`ஶ்ரீ`, `ஞூ`, `கூ`).
9. Open a large `.md` (>200 KB). Status bar should announce on-demand mode; typing must stay fluid.

### ☐ A7. "Open .md files with Neight" — macOS-only code path, never run

**Help → Debug Info → File Associations** has **Open .md files with Neight**, calling `LSSetDefaultRoleHandlerForContentType` through ctypes (`neight.py:671`). The Windows half of this feature is tested; **this half is not**.

**Test**
1. Open Debug Info — it should report the current default handler for `.md`.
2. Running from source, it should instead say the built app is required (Launch Services identifies handlers by bundle identifier, which a source run lacks). Confirm that message appears rather than a crash or silent failure.
3. From `Neight.app` in `/Applications`: click the button, then check a `.md` file's Get Info shows Neight, and double-clicking opens Neight.
4. Re-open Debug Info — should now say Neight *is* the default, button disabled.

**If it fails:** likely (a) app not yet registered with Launch Services — launch once from `/Applications` first; (b) the `net.daringfireball.markdown` UTI not claimed, which depends on `CFBundleDocumentTypes` in `packaging/Neight.macos.spec` — and **that spec has never been built** (see B1); or (c) a non-zero `OSStatus`, which the code reports as a refusal. Log the status if digging.

Note: deprecated API on macOS 12+. Still functional; the modern replacement is `NSWorkspace.setDefaultApplicationAtURL:toOpenContentType:`, which needs PyObjC — a dependency the project does not have.

### ☐ A8. Encoding and newline notice

Neight normalises on save: UTF-8 without BOM, plus the platform newline. **On macOS that is LF; on Windows it is CRLF.** This is Python's default translation and was previously undocumented — the earlier audit wrongly claimed "always LF".

**Test:** open a CRLF file and a UTF-16 file. A status-bar note should say saving will convert them, and Debug Info should show the detected format. A file already UTF-8 + LF must produce **no** notice and round-trip byte-identically.

### ☐ A9. Tamil last-line descender still renders correctly

No layout code was changed, but the file was heavily edited and the layout is sensitive.

**Test:** in a **visible** window, put Tamil with deep marks on the final line — `ஶ்ரீ முற்றும்`, `ஞூமூகூ`, `தூ பூ கூ` — and press `⌘↓`. Screenshot the bottom strip at 10, 14, 18, 24, 28 pt. No glyph may be clipped. Compare against the table in [`Tamil last line descender clipping at end of document.md`](Tamil%20last%20line%20descender%20clipping%20at%20end%20of%20document.md).

### ☐ A10. Saving is durable and Save As is transactional

All writes now go through one helper: unique temp → write → `flush` → `fsync` → `os.replace`. Manual save previously skipped `flush`/`fsync` and shared a temp filename with the autosave worker. Save As commits the new document identity only after a successful write. Autosave carries a generation checked immediately before the rename, so a hung worker cannot overwrite newer content.

**Test:** save a file and kill the process immediately — file intact, no `.tmp~` left. Try Save As into a read-only directory — the title bar and current path must still refer to the original document.

### ☐ A11. Writer and Techie modes still behave

Both call `_apply_settings_dict()`, which the signal-blocking change in A3 directly affects.

**Test:** apply each mode; confirm font, margins, line spacing, status-bar items, autosave interval and keyboard switching all land as documented, and that each application produces exactly one settings write.

### ☐ A12. Keyboard-layout switching is unaffected

Nothing in the macOS TIS/CoreFoundation code was touched, but the Keyboards dialog now persists through the shared save path instead of a bespoke whole-file write.

**Test:** Settings → Keyboards, change quick-switch and the Anjal-English option, confirm they persist across a restart, and that the Tamil/English switch still works (double ⌃ Control).

---

## Part B — Work that needs a Mac to even begin

### ☐ B1. Build the macOS app — do this before any release

`packaging/Neight.macos.spec` is **new and has never been executed.**

Previously *no* spec was committed at all (`.gitignore` had a blanket `*.spec`), so `buildme_mac_app.sh` ran `pyinstaller Neight.spec` against a file a clean clone did not have — the documented macOS build was impossible from a fresh checkout. Worse, `buildme.bat` used a bare `pyinstaller … neight.py`, which *generates* a spec and destroyed the macOS one on every Windows build. Both scripts now point at committed specs under `packaging/`.

**Test from a genuinely clean clone**, not your working copy:

```bash
git clone https://github.com/venkatarangan/neight.git /tmp/neight-clean
cd /tmp/neight-clean
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
./buildme_mac_app.sh
```

Then inspect what came out:

```bash
plutil -p dist/Neight.app/Contents/Info.plist | grep -Ei 'bundle|version|document'
codesign --verify --deep --strict --verbose=2 dist/Neight.app
```

**Confirm:** `CFBundleIdentifier` is `com.venkatarangan.neight`; version matches `VERSION` in `neight.py`; `CFBundleDocumentTypes` lists plain-text and Markdown; the app launches; double-clicking a `.txt` and a `.md` opens it; "Open With → Neight" works.

**Note:** `buildme_mac_app.sh` runs `increment_version.py`, so it bumps `VERSION`. Do not commit that bump from a throwaway clone.

**If the spec is wrong**, the likely culprits are the icon path (`../neight.icns`, relative to `packaging/`) and the `COLLECT`/`BUNDLE` structure.

### ☐ B2. Cursor and layout instrumentation — deliberately not started

This is the one part of the plan left undone on purpose.

`SpacedPlainTextDocumentLayout.blockBoundingRect()` (`neight.py:1285`) repositions every `QTextLine` **as a side effect of being queried**, and `_apply_viewport_margins()` (`neight.py:1557`) calls it while computing margins — so measuring the layout mutates it. Changing that without measurements first is guesswork, and the measurements need a real Mac and a visible window.

**Reconcile before touching code:** commit `ca5a73d` removed 61 lines — the deferred `_cursor_vis_timer`, `_schedule_cursor_visibility_check()`, `_ensure_cursor_line_fully_visible()` and the navigation-key fallback. The known-bug document has been corrected to record this. **Do not restore that code blindly** — it was removed as part of macOS scrolling fixes, so putting it back may reintroduce what it was removed to solve.

**Approach**
1. Add temporary instrumentation behind Debug Info: logical position, block number, `cursorRect`, block geometry, scrollbar value/range/pageStep, viewport size, margins, wrap mode, spacing, font, device pixel ratio.
2. Run the matrix from §7.5 of [`Comprehensive modernization audit and plan.md`](Comprehensive%20modernization%20audit%20and%20plan.md): wrap on/off, every spacing preset, margins 0–25%, line numbers and Word Index on/off, font sizes 6–100 (especially 10–28), mixed Latin/Tamil, one very long wrapped paragraph, 10k and 100k lines, Home/End/arrows/PageUp/PageDown, clicks near the bottom and right edges, selection drag, zoom during selection, Retina and non-Retina.
3. **Acceptance:** logical cursor position, visual caret, selection, clicked position and the line/column status must all agree.
4. Only then consider changing `_refresh_wrap_layout()`'s `NoWrap → WidgetWidth` toggle (`neight.py:1453`) or making margin calculation a pure function with a single `setViewportMargins` call.

### ☐ B3. Drag and drop from Finder

Proposal in [`Drag and drop file from Finder or Explorer.md`](Drag%20and%20drop%20file%20from%20Finder%20or%20Explorer.md). Now more attractive than before: the open path is centralised and records document encoding/newline in one place, so drag-drop, File → Open, command-line paths and macOS `QFileOpenEvent` can all share it.

### ☐ B4. Status-bar Tamil font workaround

[`Tamil font rendering in status bar on macOS.md`](Tamil%20font%20rendering%20in%20status%20bar%20on%20macOS.md) — setting a Tamil font globally on the status bar changes the look of ordinary Latin status text. The code still does exactly that (search `_sb_tamil_font_name` in `Notepad.__init__`). The proper fix is a fallback-family stack via `QFont.setFamilies()`, which has never been attempted. Needs a Mac to judge.

---

## Part C — Open decisions (need your call, not just testing)

### ☐ C1. Settings location

Neight prefers `settings.json` **beside the executable**, which inside a `.app` means inside the bundle, which means settings die with the app.

The obvious fix is `QStandardPaths.AppConfigLocation` with a one-time migration. **Deliberately not implemented**: it relocates every existing user's settings, could not be validated on macOS from Windows, and on Windows would break the portable "settings next to the .exe" workflow this repository itself uses.

- **Option 1 (recommended):** macOS only — never write inside the bundle; use `~/Library/Application Support/Neight/`, migrating once from the bundle and from `~/.config/Neight/`. Windows portability untouched.
- **Option 2:** `QStandardPaths` on both platforms, accepting the loss of Windows portable mode.
- **Option 3:** leave as is; the documentation now describes reality.

If you pick 1 or 2, `ADVANCED.md` must change in the same commit — it currently describes present behaviour and would become wrong.

### ☐ C2. Qt version convergence

An earlier audit claimed PySide6 6.10.1 was installed and planned a staged upgrade. The Windows environment is actually on **6.11.0**, and because `requirements.txt` previously said only `PySide6>=6.0.0`, releases were already linking whatever happened to be installed. It is now pinned to `6.11.0` / `shiboken6==6.11.0`.

**Check what this Mac has.** If it differs, decide which version both platforms ship. Then re-test the Tamil caret-navigation behaviour recorded in [`Bug in QT for Tamil text handling.md`](Bug%20in%20QT%20for%20Tamil%20text%20handling.md) and note the result against the pinned version.

### ☐ C3. Pygments — `codehilite` is currently a no-op

The Markdown pipeline requests the `codehilite` extension, but **Pygments is not bundled** (verified: 0 modules in the shipped build). Code blocks therefore have no syntax highlighting in either the preview or exported PDFs — they render as plain monospace on a grey background.

- **Add Pygments** (~3–5 MB to both binaries) for real highlighting, or
- **Drop `codehilite`** from `MARKDOWN_EXTENSIONS` and stop implying a feature that does nothing.

### ☐ C4. Release binaries in Git

`.git` is **653 MB** because `dist/` (88 MB) and `stable/` (39 MB) hold committed binaries. Moving to GitHub Releases needs a history rewrite plus updating README and website links. Your decision.

### ☐ C5. Preset keys that reset to hardcoded defaults

Pre-existing, not introduced by this work, but it is the same class as the A3 bug. `_apply_settings_dict()` (`neight.py:6971`) defaults several keys to hardcoded values when absent. A preset file written before a setting existed therefore silently resets it.

I fixed this for `update_check_on_launch` and `markdown_preview_visible` (they fall back to the *current* value). Still affected: `quick_switch_enabled`, `force_anjal_english`, and arguably others. Decide whether presets should define the complete configuration (current behaviour) or leave unknown keys alone.

---

## Part D — Deferred backlog

- **Module split** — deferred by your decision. `neight.py` is 8,842 lines. Revisit once a real test suite exists.
- **Single-process windows** — not needed; the cross-window merge (A4) addresses the races in place.
- **Large Document Mode** — not attempted. The preview already has a size threshold; the editor does not.

---

## Regression suite

There is **no committed test suite** — the checks were written as standalone scripts on Windows and live in a scratch directory, so they are not in the repo. Worth creating properly under `tests/` at some point.

Committed CI (`.github/workflows/checks.yml`) does run on macOS: import-and-construct, a guard that startup never persists a font the user did not choose, Ruff, and BOM/UTF-8 checks. Pushing exercises that automatically.

Locally, at minimum:

```bash
# 1. Syntax
python3 -c "import ast, io; ast.parse(io.open('neight.py', encoding='utf-8').read()); print('syntax OK')"

# 2. Constructs headlessly
QT_QPA_PLATFORM=offscreen python3 -c "
import sys, neight
app = neight.NeightApplication(sys.argv)
win = neight.Notepad(initial_file=None, restore_last_session=False)
print('constructed OK')
"

# 3. Startup must not rewrite settings — the A3 regression
QT_QPA_PLATFORM=offscreen python3 - <<'PY'
import json, pathlib, sys, shutil, tempfile
import neight
S = 'settings.json'
backup = tempfile.mktemp(); shutil.copy2(S, backup)
pathlib.Path(S).write_text(json.dumps({
    'font_family': 'Courier New', 'font_size': 17,
    'unicode_substring_highlight': True, 'word_wrap': False,
    'line_numbers_visible': False, 'status_show_words': False,
}), encoding='utf-8')
writes = []
orig = neight.SettingsManager.save
neight.SettingsManager.save = lambda self, d: (
    writes.append((d.get('font_family'), d.get('font_size'))) or orig(self, d))
app = neight.NeightApplication(sys.argv)
win = neight.Notepad(initial_file=None, restore_last_session=False)
bad = [w for w in writes if w != ('Courier New', 17)]
shutil.copy2(backup, S)
assert not bad, f'startup persisted a font the user never chose: {bad}'
print(f'OK — {len(writes)} write(s), all preserving the stored font')
PY

# 4. Tamil spelling guard
grep -rP "சோல்வெளி" --include="*.py" --include="*.html" . && echo "FAIL" || echo "tamil guard passed"
```

Then exercise by hand — all of these run through code that changed: **Writer Mode, Techie Mode, Save, Save As, Open, New Window, Markdown Preview, keyboard switch, Debug Info.**

---

## Reference — what changed on Windows

Full detail in [`Independent assessment and fix plan.md`](Independent%20assessment%20and%20fix%20plan.md).

| Area | Change |
|---|---|
| Settings | Transaction guard so applying settings cannot save; all synchronised actions signal-blocked; write failures reported instead of swallowed; store no longer relocates silently |
| Multi-window | Advisory lock, revision counter, key-level merge — a window writes only what it changed, so it cannot revert another window |
| Saving | One durable atomic-write helper everywhere (unique temp → `fsync` → rename); manual save previously skipped `fsync`; Save As transactional; save generations stop a hung autosave overwriting newer content |
| Documents | Encoding, BOM and newline detected on open and conversion announced; UTF-8 BOM no longer leaks a stray U+FEFF; UTF-32 detected before UTF-16 |
| Input | Wheel/trackpad deltas accumulated with remainder carry; one bounded font change per gesture; debounced persistence; native pinch support |
| Performance | Highlight scans coalesced — a 20-edit burst ran 20 whole-document scans at ~35 ms each, now 1 |
| Markdown | Split-view live preview (`⌘⇧M`) sharing one renderer with PDF export; `sane_lists` added, which also fixed an existing bug where PDF export merged an ordered list into a following bulleted one |
| Associations | `.md`/`.markdown` "Open With" on Windows plus a button to Default Apps; Launch Services default-handler support on macOS |
| Privacy | `update_check_on_launch` preference (default on); `PRIVACY.md`, `docs/index.html`, `README.md` corrected — they claimed "0 network calls" while the app called GitHub on every launch |
| Build | Both PyInstaller specs committed under `packaging/`; scripts point at them; dependencies pinned and split runtime/dev; CI extended |

### Key locations in `neight.py`

| What | Where |
|---|---|
| macOS Launch Services helpers | `_macos_set_default_handler` @ 671 |
| Windows association helpers | `_WIN_FILE_KINDS` table @ 459, `_win_register_association` @ 482 |
| Custom line-spacing layout | `SpacedPlainTextDocumentLayout` @ 1285 |
| Wrap refresh (`NoWrap` toggle) | `_refresh_wrap_layout` @ 1453 |
| Viewport margin calculation | `_apply_viewport_margins` @ 1557 |
| Wheel/trackpad accumulation | `_consume_zoom_steps` @ 1917 |
| macOS pinch gesture | `_handle_native_gesture` @ 1988 |
| Shared Markdown renderer | `_markdown_to_styled_html` @ 5173 |
| Preview show/hide | `_toggle_markdown_preview` @ 5244 |
| Settings application | `_apply_settings_dict` @ 6971 |

Line numbers drift — search by name if they no longer match.
