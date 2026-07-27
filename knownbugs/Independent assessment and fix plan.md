# Independent Assessment and Fix Plan

**Assessment date:** 2026-07-27
**Repository:** `venkatarangan/neight`
**Branch reviewed:** `main`
**Application version reviewed:** `2026.066`
**Reviewed against:** [`Comprehensive modernization audit and plan.md`](Comprehensive%20modernization%20audit%20and%20plan.md) (2026-07-25)
**Status:** Assessment and plan. Implementation tracked separately.

## Purpose

This document is a second, independent pass over the Neight source, documentation, git
history and build environment. The earlier comprehensive audit was used as a lead list,
not as a source of truth: every finding acted on below was re-verified against the actual
code.

Its conclusions differ from the earlier audit in three ways that matter:

1. It identifies a **specific root cause** for the one bug currently open in
   [`Issues to fix.md`](Issues%20to%20fix.md), which the earlier audit catalogued the
   ingredients of but never connected to the symptom.
2. It corrects a **factually stale section** of the earlier audit that would have led to a
   pointless multi-step Qt upgrade plan.
3. It records **five defects the earlier audit did not find**.

### Limitation

Like the earlier audit, this review was carried out on Windows. macOS-specific code was
read and compared against history and documentation but not executed. Everything touching
macOS rendering, input sources, native gestures, signing and Finder integration must be
validated on real hardware before release. Items requiring that are marked
**[needs macOS]**.

---

## Part 1 — Verification of the earlier audit

The following findings were re-checked against the source and are confirmed. Line numbers
are as of version `2026.066`.

| Earlier finding | Verdict | Evidence |
|---|---|---|
| 1.1 Settings stored beside the executable | Confirmed | `neight.py:541-608`. `_determine_active_path()` prefers `base_dir/settings.json`; on a frozen macOS build that is inside `Neight.app`. It also writes a `.write_test` probe into that directory at startup. |
| 1.2 Multiple processes overwrite one settings file | Confirmed | `new_window()` (`neight.py:3060`) spawns a detached subprocess; every process performs a whole-dictionary read-modify-write in `_save_preferences()` (`neight.py:6352`), and `SettingsManager.save()` uses the same `.tmp~` path in every process. |
| 1.3 Applying settings can write settings | Confirmed — **this is the live bug.** See Part 2. |
| 1.4 Save failures hidden | Confirmed | `SettingsManager.save()` correctly returns `bool`, but `_save_preferences()` discards it (`neight.py:6450`) and wraps the whole body in `except Exception: pass` (`:6452`). |
| 2.1 Manual save less durable than autosave | Confirmed | `_write_to_path()` (`:3294`) has no `flush`/`fsync`; the autosave worker (`:3360-3366`) has both. |
| 2.2 Save As commits the path before the write succeeds | Confirmed | `:3289-3292` assigns `current_path`, updates the default directory and export visibility, *then* calls `_write_to_path()`. |
| 2.3 Encoding and newline not preserved | Confirmed, with a correction | `_open_file_path()` decoded UTF-8/16/32 but discarded which encoding won, and both write paths hardcode `encoding="utf-8"`. **The earlier audit says saving "always uses UTF-8" with LF; the LF half is wrong.** Python's default newline translation on write means Neight emits **CRLF on Windows and LF on macOS** — measured, not inferred. So the conversion is platform-determined: an LF file becomes CRLF on Windows, a CRLF file becomes LF on macOS. A UTF-8 BOM was also left in the document as a stray U+FEFF. |
| 2.5 Manual save and autosave can collide | Confirmed | Both construct the identical temp name `f"{name}.{os.getpid()}.tmp~"` (`:3300` and `:3359`). PID qualification defends against *other windows*; it does nothing about the two writers inside one window. |
| 2.6 Watchdog permits stale overwrite | Confirmed | `_autosave_watchdog_check()` (`:3564`) only clears `_autosave_in_progress`. The hung daemon thread is never signalled and still executes `os.replace` whenever it wakes. |
| 6.1 Small trackpad deltas discarded | Confirmed, and worse than described. See Part 3. |
| 6.2 One wheel event causes many expensive updates | Confirmed | `for _ in range(abs(steps)): handler(direction)` (`:1647-1648`); each `_change_font_size()` runs `setFont` plus `_save_preferences()` (`:7373-7387`). |
| 7.1 Cursor-visibility guard removed but documented as kept | Confirmed | `git show ca5a73d` removes `_cursor_vis_timer`, the `cursorPositionChanged` connection, `_schedule_cursor_visibility_check()` and `_ensure_cursor_line_fully_visible()` — 61 lines. [`Tamil last line descender clipping at end of document.md`](Tamil%20last%20line%20descender%20clipping%20at%20end%20of%20document.md) still states "**kept in code**" and "Option A … are kept". |
| 7.2 / 7.3 / 7.4 Layout risks | Confirmed | `SpacedPlainTextDocumentLayout.blockBoundingRect()` (`:1070`) repositions every `QTextLine` on each query; `_refresh_wrap_layout()` toggles `NoWrap`→`WidgetWidth` (`:1202-1203`); `_apply_viewport_margins()` calls `setViewportMargins` twice (`:1297`, `:1353`). |
| 8.3 Text changes bypass the highlight debounce | Confirmed, and quantified | `_on_text_changed()` called `_update_word_highlights()` synchronously. Measured: the scan costs **32–46 ms** on a 3 MB document, and a 20-edit burst with a single-word selection live ran **20 separate whole-document scans**. Note the trigger is narrower than the audit implies — ordinary typing *replaces* the selection, so it does not hit this path; edits that leave a selection intact do. |
| 10.1 macOS spec is not version-controlled | Confirmed, and worse than described. See Part 3. |
| 10.5 CI is insufficient | Confirmed | `.github/workflows/` contains only `tamil-guard.yml`, a single `grep` for one Tamil misspelling. |
| 11.1 Network claims contradict behaviour | Confirmed | `showEvent()` schedules `_run_startup_update_check` five seconds after first show (`:2779-2781`). `PRIVACY.md:43` states "no background or automatic network connections"; `docs/index.html:883` shows "0 network calls"; `:1201` and `:1225` claim "zero network calls". |

The earlier audit's positive observations also hold. The recovery-cleanup design
(`_clear_recovery_file` / `_on_recovery_success`), the `toPlainText()` skip when no counter
needs the text (`:7667-7669`), the 1000-match highlight cap, the 512 KB preset size guard
and the `_applying_margins` re-entry guard are all sound and should be preserved.

---

## Part 2 — Root cause of the open two-window font bug

[`Issues to fix.md`](Issues%20to%20fix.md) records:

> When two windows of neight are open, the second app doesn't get the font settings
> correctly. For example in tamil, it takes the default tamil font and not the assigned
> font.

The earlier investigation in
[`new window default font issue and fix.txt`](new%20window%20default%20font%20issue%20and%20fix.txt)
concluded the cause was over-strict type guards on `font_family` / `font_size` in
`_apply_settings_dict`, and patched those. That was a real defect, but it was not this one.
The actual mechanism is a startup write ordering fault.

### Construction order

`Notepad.__init__` runs, in order (`neight.py:2225-2232`):

```
_create_actions()  →  _create_menus()  →  _connect_signals()  →  _install_shortcuts()  →  _load_preferences()
```

Every `toggled` connection is therefore **live before any setting has been loaded**.

### The trigger

`_apply_settings_dict()` synchronises menu actions from the loaded dictionary. It blocks
signals for exactly two of them — `auto_hide_scrollbar_act` (`:6105-6107`) and
`reopen_last_act` (`:6229-6231`) — and leaves the rest unblocked:

- `line_numbers_act` is constructed unchecked (`:2366`). Loading `line_numbers_visible:
  true` calls `setChecked(True)` at `:6099`, which emits `toggled` →
  `_toggle_line_numbers` → `_save_preferences()`.
- `unicode_substring_highlight_act` is constructed `setChecked(False)` (`:2425`). The
  current `settings.json` contains `"unicode_substring_highlight": true`, so
  `setChecked(True)` at `:6159` emits `toggled` →
  `_toggle_unicode_substring_highlight` → `_save_preferences()`.

The same exposure exists for `wrap_act` (`:6094`), the five `status_*_act` (`:6116-6120`)
and `word_index_act` (`:6192`) whenever the stored value differs from the construction
default.

### The damage

At the moment those handlers run:

- `self._settings_cache` is still `{}`. It is initialised empty at `:2215` and only
  assigned the loaded data at `:6344`, *after* the apply completes. So
  `data = dict(self._settings_cache)` at `:6357` starts from nothing, and only the keys
  `_save_preferences()` explicitly writes survive into the file.
- **The font has not been applied yet.** `_apply_settings_dict` deliberately applies the
  font last, at `:6194-6222` — 35 lines after the `unicode_substring_highlight` trigger and
  95 lines after the `line_numbers` trigger. So `font = self.editor.font()` at `:6356`
  reads **Qt's default font**, and `:6389-6394` writes that default family together with
  `font_size: 12` into `settings.json`.
- The `line_numbers` trigger fires earlier still — before `_set_text_margin_percent`
  (`:6129`), `_set_line_spacing_preset` (`:6133`) and `_apply_theme_preferences` (`:6155`)
  — so it also writes default margin, line-spacing and theme values.

### Why the symptom looks intermittent and two-window-specific

Every window, on every launch, transiently rewrites `settings.json` with default fonts
before applying the real ones. The window itself then looks correct, because the correct
font is applied to its own editor immediately afterwards, and the good data is restored to
`_settings_cache` at `:6344` so the next save repairs the file.

With one window that self-repair usually wins and nothing is noticed. With two processes
running, whichever process reads or writes during that corrupt window loses the assigned
font — which is exactly the reported behaviour, and exactly why it is hard to reproduce on
demand.

### Consequence for the fix

This is a startup-ordering fault, not an artefact of the subprocess-per-window design. It
can be fixed without changing the process model. That is why Stage 1 below is small and why
the New Window architecture is being kept.

---

## Part 3 — Corrections and additions to the earlier audit

### 3.1 The dependency table is stale

The earlier audit's "Installed and latest versions" table reports PySide6 6.10.1 as
installed and builds a three-step upgrade plan (`6.10.1 → 6.10.3 → 6.11.1`) on that basis.
The actual contents of `.venv` are different:

| Package | Earlier audit claims | Actually installed |
|---|---|---|
| PySide6 / shiboken6 | 6.10.1 | **6.11.0** |
| Markdown | 3.10.1 | **3.10.2** |
| Pillow | 12.1.1 | **12.2.0** |
| PyInstaller | 6.18.0 | **6.20.0** |
| pre-commit | not installed | not installed (audit correct) |

Python is 3.12.10. Because `requirements.txt` specifies only `PySide6>=6.0.0`, builds link
whatever happens to be installed — meaning releases are **already on the 6.11 line**. The
earlier audit's advice not to jump to 6.11 describes a migration that has silently already
occurred. The real task is to pin what is actually in use, not to plan a staged upgrade.

### 3.2 `SettingsManager.save()` silently relocates the settings file mid-session

On write failure, `save()` reassigns `self.path = self.fallback_path` (`:671`) and retries.
That mutation is permanent for the life of the process and is never reported to the user.
Two windows that encounter different failure conditions end up reading and writing
*different files* while both believe they are authoritative. Because `log_path` derives from
`self.path.parent` (`:578`), the autosave diagnostic log silently moves as well.

### 3.3 `_apply_viewport_margins()` mutates layout while measuring it

The snap calculation calls `self.blockBoundingRect(_snap_block)` at `:1346`, and that
override repositions every `QTextLine` in the block as a side effect. Margin calculation is
therefore not idempotent — measuring changes the thing being measured. Separately, the
method's own `_applying_margins` re-entry guard means the second `setViewportMargins()` at
`:1353` silently suppresses the line-number-width refresh it would otherwise trigger.

This is a plausible contributor to the cursor-placement problems and should be instrumented
before any layout code is changed.

### 3.4 Every file open runs a full-document highlight scan

`_open_file_path()` calls `setPlainText()` at `:3158`, which fires `textChanged` →
`_on_text_changed` → `_update_word_highlights()` plus a status refresh — on a file that may
be up to the 50 MB `_MAX_OPEN_FILE_BYTES` limit. The explicit `_update_status_bar()` call at
`:3165` then repeats part of that work.

### 3.5 `buildme.bat` destroys the macOS spec

`buildme.bat` runs `pyinstaller --name Neight --onefile --windowed --icon neight.ico
--add-data "neight.ico;." neight.py` with no spec argument, which *writes* `Neight.spec` as
a side effect. Combined with `*.spec` being ignored at `.gitignore:34`, this means:

- `git log -- Neight.spec` and `git ls-files "*.spec"` are both empty — no spec is committed;
- a clean clone has **no spec file at all**, so `pyinstaller Neight.spec` in
  `buildme_mac_app.sh` fails outright, not merely with wrong settings;
- even a hand-written macOS `BUNDLE` spec is destroyed by the next Windows build.

The earlier audit reported the file contents were wrong. The stronger statement is that the
documented macOS build cannot be performed from a clean clone at all.

### 3.6 Repository size

`.git` is 653 MB, with 88 MB in `dist/` and 39 MB in `stable/` of committed binaries. The
earlier audit describes this as increasing repository size; in practice it makes cloning a
multi-minute operation and every release commit an opaque binary diff.

### 3.7 The trackpad finding is understated

`CodeEditor.wheelEvent()` at `:1640-1643` reads:

```python
delta = event.angleDelta().y()
steps = int(delta / 120) if delta else 0
if steps == 0 and not delta:
    pixel_delta = event.pixelDelta().y()
    steps = 1 if pixel_delta > 0 else -1 if pixel_delta < 0 else 0
```

The `pixelDelta` fallback is gated on `not delta`, so it only runs when `angleDelta` is
exactly zero. A *nonzero but small* `angleDelta` — the normal output of a smooth trackpad —
yields `steps == 0`, no zoom occurs, **and `event.accept()` at `:1649` still swallows the
event**. So Ctrl+trackpad neither zooms nor scrolls. **[needs macOS]**

### 3.8 Disagreements of judgement

- The earlier audit's recommended first step is a ten-area test harness before any defect
  is fixed. For a single-maintainer project that front-loads a large amount of pytest-qt
  infrastructure that does not yet exist, ahead of a user-visible bug that takes roughly
  forty lines to fix. The order below fixes the verified persistence fault first, then
  builds tests around the corrected behaviour.
- The earlier audit's §9 ten-module split is the right long-term direction but the wrong
  next move. The Tamil and Qt layout workarounds are precisely the code least protected by
  tests, and they are what a split would disturb first.

---

## Part 4 — The plan, and what was implemented

Decisions taken by the maintainer and reflected below: keep the subprocess-per-window
design and fix the race within it; keep the automatic update check but add an off switch
and correct the documentation; keep normalisation on save but warn the user on open; fix
correctness now and defer the module split.

**Status: Stages 1–6, 8 and 9 are implemented and verified. Stage 7 is documentation-only
so far. See [Part 5](#part-5--implementation-status) for exactly what was and was not
done, and what still needs a Mac.**

### Stage 1 — Settings transaction (fixes the open bug)

1. Add an `_applying_preferences` flag, set for the duration of `_apply_settings_dict()`
   and cleared in a `finally`; `_save_preferences()` returns early while it is set.
2. Block signals for every action synchronised in `_apply_settings_dict()`, not just the
   two handled today: `wrap_act`, `line_numbers_act`, the five `status_*_act`,
   `unicode_substring_highlight_act`, `word_index_act`.
3. Assign `self._settings_cache = data` **before** `_apply_settings_dict(data)` in
   `_load_preferences()`, so no path can ever serialise from an empty cache.
4. Make `_save_preferences()` return `bool`, propagate `SettingsManager.save()`'s result,
   retain `last_save_error`, and surface one non-repeating warning. Narrow the bare
   `except Exception: pass`.
5. Stop `SettingsManager.save()` silently reassigning `self.path`; make the fallback an
   explicit, reported migration.

### Stage 2 — Cross-process settings safety

6. Unique temp filenames per process, matching the pattern already used by
   `_recovery_write()`.
7. `QLockFile` around the read-modify-write in `_save_preferences()`, plus a `revision`
   counter: acquire lock → re-read from disk → merge this window's keys over the fresh
   copy → bump revision → write → release. This converts whole-dictionary overwrites into
   key-level merges without changing the process model.
8. Hoist the `_MACHINE_LOCAL` key set — currently duplicated inside both preset methods —
   to a module-level constant used by all four call sites so the definitions cannot drift.

### Stage 3 — Document save durability

9. One durable atomic-write helper (temp → write → `flush` → `fsync` → `os.replace`, unique
   temp name), used by `_write_to_path()`, the autosave worker, `_recovery_write()`,
   `SettingsManager.save()` and both preset writers. This gives manual save the `fsync` it
   lacks and removes the manual-save/autosave temp-name collision in a single change.
10. Make `save_file_as()` transactional: write first, commit `current_path`, default
    directory, export visibility, title and recovery cleanup only on success.
11. Add a monotonic save generation. The autosave worker refuses to `os.replace` if its
    generation is stale; the watchdog invalidates the generation rather than merely
    clearing a boolean.

### Stage 4 — Encoding and newline warning

12. Detect BOM, source encoding and newline style from raw bytes on open.
13. Show one non-modal notice when saving will convert the file, and expose the detected
    encoding and newline style in **Help → Debug Info**. Saving remains UTF-8 + LF.

### Stage 5 — Trackpad and zoom **[needs macOS]**

14. Accumulate fractional `angleDelta` and `pixelDelta`; consume a step past a threshold;
    keep the remainder; reset on direction change. Only `accept()` the event when a zoom is
    actually consumed.
15. Compute one bounded target size per event and apply it once; debounce the preference
    write so a gesture produces a single save.
16. Add `QNativeGestureEvent` pinch handling with duplicate-event suppression.

### Stage 6 — Text-change performance

17. Route `_on_text_changed()` through the existing `_word_highlight_timer` instead of
    scanning synchronously, and skip the scan when there is no eligible single-word
    selection.
18. Suppress the open-time scan by blocking `textChanged` around `setPlainText()` in
    `_open_file_path()`.

### Stage 7 — Cursor and layout instrumentation **[needs macOS]**

19. First reconcile
    [`Tamil last line descender clipping at end of document.md`](Tamil%20last%20line%20descender%20clipping%20at%20end%20of%20document.md)
    with commit `ca5a73d`, so the record matches the code.
20. Add Debug-Info-gated instrumentation (logical position, block number, `cursorRect`,
    block geometry, scrollbar value/range/pageStep, viewport size, margins, wrap mode,
    spacing, font, device pixel ratio) and run the earlier audit's §7.5 matrix to collect
    real numbers.
21. Only then decide on the `NoWrap`→`WidgetWidth` toggle and on making margin calculation
    a pure function with a single `setViewportMargins` call. **The removed
    `_ensure_cursor_line_fully_visible()` must not be restored blindly.**

### Stage 8 — Update check and documentation truth

22. Add an `update_check_on_launch` preference, default **on**, honoured in `showEvent()`
    and exposed in the Settings menu.
23. Correct `PRIVACY.md`, `docs/index.html` (three places) and `README.md` to disclose the
    GitHub Releases request, its five-second delay, timeout, failure behaviour and the new
    off switch.
24. Correct `ADVANCED.md`, which presents the `%LOCALAPPDATA%` / `~/.config` fallback as the
    primary settings location. Preferably perform the `QStandardPaths.AppConfigLocation`
    migration first and then document that, since `release_install_notes.md` records real
    settings loss on macOS.

### Stage 9 — Build reproducibility

25. Remove the blanket `*.spec` ignore; commit `packaging/Neight.windows.spec` and
    `packaging/Neight.macos.spec`, the latter with `BUNDLE`, `info_plist`, file
    associations and `argv_emulation=True`.
26. Point `buildme.bat` and `buildme_mac_app.sh` at their respective specs so neither
    regenerates nor destroys the other's build input.
27. Pin `requirements.txt` to the versions actually in use and split runtime from
    development, design and build dependencies. Pillow is not imported by `neight.py` and
    belongs in a design group.
28. Extend CI beyond `tamil-guard.yml` with syntax/import and lint jobs on Windows and
    macOS, preserving the Tamil spelling guard and the BOM / line-ending hooks.

### Deferred, with reasons

- **Module split.** Deferred until Stages 1–6 are covered by tests; the Tamil and Qt
  workarounds are the least protected code in the project.
- **Single-process windows.** Not required for the reported bug; Stage 2 addresses the
  races within the existing architecture.
- **Drag-and-drop from Finder/Explorer.** Correctly identified in the earlier audit as
  dependent on a centralised open path; Stage 4 is the prerequisite.
- **Large Document Mode.** Worth doing after Stage 6 measurements show where the cost
  actually is, rather than before.

---

## Verification

**Stage 1 — reproduce and confirm the fix.** With `"unicode_substring_highlight": true` and
a non-default `font_family` in `settings.json`:

1. Copy `settings.json` aside, launch Neight, wait for the window, quit, and diff. Today the
   file returns with a default font family and `font_size: 12`. After the fix it must be
   identical apart from `window_size`.
2. Open window A, set a distinctive font, use **File → New Window**. Window B must show the
   same font. Close in both orders; the font must survive both.
3. Assert temporarily that `_save_preferences()` is never entered while
   `_applying_preferences` is set, and confirm the assertion does not trip during startup.

**Stage 2.** Two windows, change font in A and margins in B, close in both orders — both
changes must persist. Repeat with the settings file made read-only and confirm the failure
is reported rather than swallowed.

**Stage 3.** Save, kill the process immediately, confirm the file is intact and no `.tmp~`
remains. Force a Save As failure against a read-only directory and confirm the title bar
and `current_path` still refer to the original document.

**Stage 4.** Open a CRLF file and a UTF-16 file; confirm the conversion notice appears and
Debug Info reports the detected encoding and newline style.

**Stages 5 and 7.** The delta accumulator can be unit-tested as pure logic on any platform,
but pinch gestures, trackpad feel and Tamil last-line rendering must be confirmed on real
macOS hardware with screenshots. These will be reported as unvalidated until that happens.

**Stage 6.** Measure `_update_status_bar` and the highlight scan on a large document before
and after; typing must not trigger a whole-document `doc.find()` loop.

**Stage 9.** The real test is a clean clone into an empty directory followed by
`buildme.bat` on Windows and `buildme_mac_app.sh` on macOS. The macOS path cannot pass
today.

**Regression guard for every stage:** an `ast.parse` syntax check of `neight.py`, the Tamil
spelling guard, and a manual pass over Writer Mode and Techie Mode — both call
`_apply_settings_dict()` and are directly affected by the Stage 1 signal-blocking change.

---

## Part 5 — Implementation status

Everything below was verified by running it. Where a claim could be tested against the
pre-change code, it was: the "before" column is measured on `HEAD` as of `e580c00`, not
assumed.

### Done and verified on Windows

| Stage | Change | Evidence |
|---|---|---|
| 1 | Settings transaction: `_applying_preferences` guard, all synchronised actions signal-blocked via one `_sync_action_checked()` helper, `_settings_cache` seeded before apply, `_save_preferences()` returns `bool` and reports failures once, `SettingsManager.save()` no longer relocates silently | **Before:** one startup rewrote `settings.json`, changing `font_family` `"Nirmala UI" → "Sans Serif"` and `font_size` `14 → 9`. **After:** zero writes, file byte-identical. |
| 2 | Cross-process safety: unique temp filenames, `QLockFile` around read-modify-write, `settings_revision` counter, key-level merge that writes only what this window changed, `MACHINE_LOCAL_SETTINGS_KEYS` hoisted to one module constant | **Before:** two windows changing unrelated preferences lost one change in each close order, and unknown keys were dropped. **After:** both changes survive in both orders; unknown keys preserved. |
| 3 | Durability: one `_atomic_write_text()` helper (unique temp → write → `flush` → `fsync` → `os.replace`) used by manual save, autosave, recovery, settings and both preset writers; transactional `save_file_as()`; monotonic save generation checked immediately before the rename; watchdog invalidates the generation | Manual save now fsyncs; a failed Save As leaves `current_path` unchanged; a superseded write is abandoned with the newer content intact and no temp file left behind. |
| 4 | Format detection: BOM/encoding/newline recorded on open, one-time conversion notice, format shown in Debug Info; UTF-32-before-UTF-16 BOM ordering; UTF-8 BOM no longer left in the text | Verified across UTF-8, UTF-8+BOM, UTF-8 CRLF, UTF-16 LE, UTF-16+BOM and UTF-32+BOM fixtures with Tamil content, including a byte-identical round trip. |
| 5 | Zoom: fractional angle/pixel accumulation with remainder carry and direction reset, one bounded font-size change per gesture, debounced settings write, macOS pinch via `QEvent.Type.NativeGesture` | Six 20-unit deltas now produce one step (previously zero, and the event was swallowed); a 5-step gesture is one layout pass and zero immediate saves; synthesised pinch events move the size correctly. |
| 6 | Highlighting routed through the existing 80 ms timer; `textChanged` blocked around `setPlainText()` on open | **Before:** 20 scans for a 20-edit burst, and a pending scan left armed after deselection. **After:** 1 scan, timer disarmed. |
| 8 | `update_check_on_launch` preference (default on) honoured in `showEvent()`; `PRIVACY.md`, `docs/index.html` (×3), `README.md` and `ADVANCED.md` corrected | The "0 network calls" / "no background connections" claims were false; they now describe the GitHub request, its timing, timeout, failure behaviour and off switch. `ADVANCED.md` no longer presents the fallback settings path as the primary one. |
| 9 | `packaging/Neight.windows.spec` and `packaging/Neight.macos.spec` committed (macOS one with `BUNDLE`, `info_plist`, document types, `argv_emulation=True`); `.gitignore` un-ignores them; both build scripts point at them; `requirements.txt` pinned to 6.11.0/3.10.2 with build and design tools split into `requirements-dev.txt`; CI extended | New `checks.yml` runs import-and-construct on Windows and macOS, a Ruff report, BOM and UTF-8 guards, and a regression guard for the font bug that **fails on the old code and passes on the new**. |

### Partially done

**Stage 7 (cursor and layout).** Only the documentation reconciliation is done:
[`Tamil last line descender clipping…`](Tamil%20last%20line%20descender%20clipping%20at%20end%20of%20document.md)
now records that Option A was removed in `ca5a73d`, instead of claiming it is still in the
code. **No layout code was changed.** The instrumentation and the cursor matrix are
deliberately outstanding — running that matrix needs a real Mac and a visible window, and
changing `blockBoundingRect()`, the wrap toggle or the margin calculation without those
measurements is exactly the mistake this document argues against.

### Not done, and why

- **Module split.** Deferred by decision.
- **Single-process windows.** Not needed; Stage 2 addresses the races in place.
- **`QStandardPaths` settings migration.** Deliberately not done. It changes where every
  existing user's settings live and cannot be validated on macOS from here; on Windows it
  would also break the portable "settings next to the .exe" workflow this repository
  itself uses. The documentation now describes the real behaviour, including the macOS
  bundle caveat, so nothing is misleading in the meantime. **This remains an open
  decision.**
- **Moving release binaries out of Git** (`.git` is 653 MB). Needs a history rewrite and a
  release-hosting migration — a maintainer decision, not a code change.
- **Drag-and-drop from Finder/Explorer.** Still unimplemented, as before.
- **Large Document Mode.** Not attempted.

### Needs validation on a Mac before release

1. **Pinch-to-zoom.** The wiring is verified against Qt's event dispatch with synthesised
   events, but no real trackpad has driven it. Check that a pinch zooms smoothly, that it
   does not double-apply against the wheel path, and that ordinary two-finger scrolling is
   untouched.
2. **Wheel accumulation feel.** The arithmetic is unit-tested; the *feel* on a real
   trackpad is not.
3. **Tamil last-line rendering.** Unchanged by this work, but the layout is sensitive and
   the descender fix should be re-screenshotted.
4. **The macOS spec.** `packaging/Neight.macos.spec` has never been executed. Build from a
   clean clone and inspect the generated `Info.plist` — bundle identifier, version and
   document types — before publishing.
5. **Settings location.** Confirm via Help → Debug Info whether your installed build keeps
   `settings.json` inside `Neight.app`, which determines whether the documented caveat
   applies to you.
