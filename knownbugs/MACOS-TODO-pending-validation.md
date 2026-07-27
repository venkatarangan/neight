# macOS Pending Work — Validation and Fixes

**Created:** 2026-07-27
**Created on:** Windows 11 (Python 3.12.10, PySide6 6.11.0)
**Companion document:** [`Independent assessment and fix plan.md`](Independent%20assessment%20and%20fix%20plan.md)

---

## How to use this file

Open this file on your Mac and say to Claude Code:

> **"Read `knownbugs/MACOS-TODO-pending-validation.md` and work through the pending macOS items."**

Everything below was written on Windows and therefore **could not be executed on macOS**.
Each item states what to run, what a correct result looks like, and what to do if it is
wrong. Work top to bottom: Part A is verification of work already done, Part B is work that
could not be started without a Mac.

**Before starting anything**, capture a baseline so a regression is recognisable:

```bash
cd /path/to/neight
git log --oneline -3
python3 -c "import PySide6; print('PySide6', PySide6.__version__)"
python3 -c "import sys; print(sys.version)"
```

Record the PySide6 version in your findings. The Windows side was verified on **6.11.0**;
if your Mac has a different version, say so, because Qt minor releases change text layout
and cursor geometry.

---

## Part A — Verify what was changed on Windows

These changes are implemented and pass on Windows. They touch platform-sensitive behaviour
and need confirmation on real hardware.

### A1. Pinch-to-zoom actually works — **highest risk item**

Native gesture support was added to `CodeEditor` in `neight.py`:

- `event()` intercepts `QEvent.Type.NativeGesture` (there is no `nativeGestureEvent`
  virtual on `QWidget` in PySide6 — confirmed, this was corrected during implementation).
- `_handle_native_gesture()` accumulates `ZoomNativeGesture` values at ~0.08 per font point.
- `_native_zoom_active` suppresses the wheel path so a gesture cannot zoom twice.

**It has never run on a real trackpad.** Synthesised events were verified to move the font
size correctly, but macOS may deliver a different sequence or different `value()` scaling.

**Test:**
1. Open a document. Note the font size in the status bar.
2. Pinch out slowly on the trackpad. The size should climb smoothly, one point at a time,
   with no jumps and no runaway.
3. Pinch in. It should fall symmetrically.
4. Pinch quickly. It must not shoot to the 6 pt or 100 pt limit in one gesture.
5. Two-finger **scroll** (no pinch, no Ctrl) must behave exactly as before — kinetic,
   native, untouched.
6. Ctrl + two-finger scroll should zoom, including very slow movement (see A2).

**If it misbehaves:** the tuning constant is `0.08` in `_handle_native_gesture`. If zoom is
too fast, raise it; too slow, lower it. If nothing happens at all, log
`event.gestureType()` and `event.value()` for a real pinch and report the values — the
enum may be delivered differently than expected.

### A2. Slow trackpad zoom no longer does nothing

**This was a real bug on macOS.** `wheelEvent` computed `int(delta / 120)` and only fell
back to `pixelDelta` when `angleDelta` was *exactly* zero. A small non-zero `angleDelta` —
the normal output of a smooth trackpad — produced zero zoom **and** the event was still
`accept()`ed, so Ctrl+trackpad neither zoomed nor scrolled. It is now accumulated with the
remainder carried between events (`_consume_zoom_steps`).

**Test:** hold Ctrl and move two fingers *very slowly*. The size must eventually change.
Before this fix it would never change.

### A3. Tamil last-line descender still renders correctly

No layout code was changed, but the file was heavily edited and the layout is sensitive.

**Test:** in a **visible** window (not offscreen), put Tamil with deep marks on the final
line — `ஶ்ரீ முற்றும்`, `ஞூமூகூ`, `தூ பூ கூ` — and press `Cmd+Down`. Screenshot the bottom
strip at 10, 14, 18, 24 and 28 pt. No glyph may be clipped. Compare against the table in
[`Tamil last line descender clipping at end of document.md`](Tamil%20last%20line%20descender%20clipping%20at%20end%20of%20document.md).

### A4. Where your settings actually live

Open **Help → Debug Info** and read the "Settings JSON" path.

- If it is inside `/Applications/Neight.app/…`, your settings **will be destroyed** when you
  replace the app. This is the known issue in
  [`release_install_notes.md`](../release_install_notes.md), and `ADVANCED.md` has been
  corrected to say so plainly instead of claiming `~/.config/Neight` is always used.
- Debug Info now also shows a red note if the settings store ever silently relocated to the
  fallback directory after a failed write, and the last settings-write error.

**Report which path you see** — it decides whether B3 below is urgent.

### A5. The multi-window font bug is gone

This was the open item in [`Issues to fix.md`](Issues%20to%20fix.md). Root cause: applying
settings emitted action `toggled()` signals whose handlers saved the half-applied window,
writing Qt's default font over the stored one before the real font was applied.

**Test:**
1. Set a distinctive font, e.g. Tamil MN at 20 pt. Quit.
2. Copy `settings.json` (path from Debug Info) somewhere safe.
3. Launch Neight, wait for the window, quit. Diff the file — only `window_size` may differ.
4. Launch, then **File → New Window**. The second window must show the same font.
5. Close in both orders. The font must survive both.

On Windows, step 3 previously rewrote `font_family` to `"Sans Serif"` and `font_size` to
`9`. On macOS the wrong value will differ but the failure is the same.

### A6. Encoding and newline notice

Neight normalises on save: UTF-8 without BOM, and the platform newline. **On macOS that is
LF; on Windows it is CRLF** — this is Python's default translation and was previously
undocumented. Files are now inspected on open and the conversion announced.

**Test:** open a CRLF file and a UTF-16 file on the Mac. A status-bar note should say
saving will convert them, and **Help → Debug Info** should show the detected format. A file
that is already UTF-8 + LF must produce **no** notice and must round-trip byte-identically.

### A7. Keyboard-layout switching is unaffected

Nothing in the macOS TIS/CoreFoundation code was touched, but the Keyboards dialog now
persists through the shared save path instead of a bespoke whole-file write.

**Test:** open **Settings → Keyboards**, change quick-switch and the Anjal-English option,
confirm they persist across a restart, and confirm the Tamil/English layout switch still
works.

---

## Part B — Work that needs a Mac to begin

### B1. The macOS build has never been run — **do this before any release**

`packaging/Neight.macos.spec` is **new and has never been executed.** Previously no spec was
committed at all (`.gitignore` had a blanket `*.spec`), so `buildme_mac_app.sh` ran
`pyinstaller Neight.spec` against a file a clean clone did not have — the documented macOS
build was impossible from a fresh checkout. Additionally `buildme.bat` used a bare
`pyinstaller … neight.py`, which *generates* a spec and destroyed the macOS one on every
Windows build. Both scripts now point at committed specs under `packaging/`.

**Test from a genuinely clean clone**, not your working copy:

```bash
git clone https://github.com/venkatarangan/neight.git /tmp/neight-clean
cd /tmp/neight-clean
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
./buildme_mac_app.sh
```

Then inspect the generated bundle metadata:

```bash
plutil -p dist/Neight.app/Contents/Info.plist | grep -Ei 'bundle|version|document'
codesign --verify --deep --strict --verbose=2 dist/Neight.app
```

Confirm: `CFBundleIdentifier` is `com.venkatarangan.neight`; the version matches `VERSION`
in `neight.py`; `CFBundleDocumentTypes` lists plain-text and Markdown; the app launches;
double-clicking a `.txt` file opens it; "Open With → Neight" works.

**Note:** `buildme_mac_app.sh` runs `increment_version.py`, so it bumps `VERSION`. Do not
commit that bump from the throwaway clone.

**If the spec is wrong,** fix `packaging/Neight.macos.spec` and re-run. The most likely
problems are the icon path (`../neight.icns`, relative to `packaging/`) and the
`COLLECT`/`BUNDLE` structure.

### B2. Cursor and layout instrumentation — deliberately not started

This is the one stage of the plan that was left undone on purpose. The reasoning:
`SpacedPlainTextDocumentLayout.blockBoundingRect()` repositions every `QTextLine` as a side
effect of being *queried*, and `_apply_viewport_margins()` calls it while computing margins
— so measuring the layout mutates it. Changing that without measurements first is guesswork,
and the measurements need a real Mac and a visible window.

**Also reconcile before touching code:** commit `ca5a73d` removed 61 lines — the deferred
`_cursor_vis_timer`, `_schedule_cursor_visibility_check()`,
`_ensure_cursor_line_fully_visible()` and the navigation-key fallback. The known-bug
document has been corrected to record this. **Do not restore that code blindly** — it was
removed as part of macOS scrolling fixes, so putting it back may reintroduce what it was
removed to solve.

**Suggested approach:**
1. Add temporary instrumentation (logical position, block number, `cursorRect`, block
   geometry, scrollbar value/range/pageStep, viewport size, margins, wrap mode, spacing,
   font, device pixel ratio), gated behind Debug Info.
2. Run the matrix in §7.5 of
   [`Comprehensive modernization audit and plan.md`](Comprehensive%20modernization%20audit%20and%20plan.md):
   wrap on/off, every spacing preset, margins 0–25%, line numbers and Word Index on/off,
   font sizes 6–100 with attention to 10–28, mixed Latin/Tamil, one very long wrapped
   paragraph, 10k and 100k lines, Home/End/arrows/PageUp/PageDown, clicks near the bottom
   and right edges, selection drag, zoom during selection, Retina and non-Retina displays.
3. **Acceptance:** logical cursor position, visual caret, selection, clicked position and
   the line/column status must all agree.
4. Only then consider changing `_refresh_wrap_layout()`'s `NoWrap → WidgetWidth` toggle or
   making margin calculation a pure function with a single `setViewportMargins` call.

### B3. Settings location — open decision, needs your call

Currently Neight prefers `settings.json` **beside the executable**, which inside a `.app`
means inside the bundle, which means settings die with the app.

The obvious fix is `QStandardPaths.AppConfigLocation` with a one-time migration. **It was
deliberately not implemented**, because it relocates every existing user's settings, could
not be validated on macOS from Windows, and on Windows would break the portable
"settings next to the .exe" workflow this repository itself uses.

**Decide, then implement:**
- **Option 1 (recommended for macOS):** on macOS only, never write inside the bundle — use
  `~/Library/Application Support/Neight/`, migrating once from the bundle and from
  `~/.config/Neight/`. Leaves Windows portability untouched.
- **Option 2:** `QStandardPaths` on both platforms, accepting the loss of Windows portable
  mode.
- **Option 3:** leave as is; the documentation now describes the real behaviour.

If you implement Option 1 or 2, `ADVANCED.md` must be updated in the same change — it has
been rewritten to describe current behaviour and will become wrong.

### B4. Qt version decision

The earlier audit's dependency table was stale: it claimed PySide6 6.10.1 was installed and
planned a staged upgrade to 6.11.1. The Windows environment is actually on **6.11.0**, and
because `requirements.txt` previously said only `PySide6>=6.0.0`, releases were already
linking whatever was installed. It is now pinned to `6.11.0` / `shiboken6==6.11.0`.

**On the Mac:** confirm what your environment has. If it differs, we are shipping two
different Qt versions across platforms and should converge deliberately. Also re-test the
Tamil caret-navigation behaviour recorded in
[`Bug in QT for Tamil text handling.md`](Bug%20in%20QT%20for%20Tamil%20text%20handling.md) and
note the result against the pinned version.

### B5. Not started, lower priority

- **Drag and drop from Finder** —
  [`Drag and drop file from Finder or Explorer.md`](Drag%20and%20drop%20file%20from%20Finder%20or%20Explorer.md).
  Worth doing now that the open path records document format in one place.
- **Status-bar Tamil font workaround** —
  [`Tamil font rendering in status bar on macOS.md`](Tamil%20font%20rendering%20in%20status%20bar%20on%20macOS.md).
  Still sets a Tamil font globally on the status bar; the fallback-family stack
  (`QFont.setFamilies()`) has not been attempted.
- **Release binaries in Git** — `.git` is **653 MB** because `dist/` and `stable/` hold
  committed binaries. Moving to GitHub Releases needs a history rewrite; your decision.
- **Large Document Mode** — not attempted.
- **Module split** — deferred by your decision.

---

## Regression suite

There is no committed test suite yet; the checks were written as standalone scripts. The
committed CI (`.github/workflows/checks.yml`) runs an import-and-construct check on
**both** Windows and macOS plus a guard for the font bug, so pushing will exercise macOS
automatically.

Locally on the Mac, at minimum:

```bash
python3 -c "import ast, io; ast.parse(io.open('neight.py', encoding='utf-8').read()); print('syntax OK')"
QT_QPA_PLATFORM=offscreen python3 -c "
import sys, neight
app = neight.NeightApplication(sys.argv)
win = neight.Notepad(initial_file=None, restore_last_session=False)
print('constructed OK')
"
```

Then exercise by hand: Writer Mode, Techie Mode, Save, Save As, Open, New Window, and the
keyboard switch — all of these go through code that changed.

---

## Summary of what changed on Windows

For context when reviewing. Full detail in
[`Independent assessment and fix plan.md`](Independent%20assessment%20and%20fix%20plan.md).

| Area | Change |
|---|---|
| Settings | Transaction guard so applying settings cannot save; all synchronised actions signal-blocked; failures reported instead of swallowed; store no longer relocates silently |
| Multi-window | Advisory lock, revision counter and key-level merge — a window now writes only what it changed, so it cannot revert another window |
| Saving | One durable atomic-write helper (unique temp → `fsync` → rename) everywhere; manual save previously skipped `fsync`; Save As is transactional; save generations stop a hung autosave overwriting newer content |
| Documents | Encoding, BOM and newline detected on open and the conversion announced; UTF-8 BOM no longer leaks a stray U+FEFF into the text; UTF-32 detected before UTF-16 |
| Input | Wheel/trackpad deltas accumulated with remainder carry; one bounded font change per gesture; debounced persistence; native pinch support |
| Performance | Highlight scans coalesced — a 20-edit burst ran 20 whole-document scans at ~35 ms each, now 1 |
| Privacy | `update_check_on_launch` preference (default on); `PRIVACY.md`, `docs/index.html`, `README.md` corrected — they claimed "0 network calls" while the app called GitHub on every launch |
| Build | Both PyInstaller specs committed under `packaging/`; scripts point at them; dependencies pinned and split runtime/dev; CI extended |
