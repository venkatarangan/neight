# Comprehensive Modernization Audit and Plan

**Audit date:** 2026-07-25  
**Repository:** `venkatarangan/neight`  
**Branch reviewed:** `main`  
**Application version reviewed:** `2026.066`  
**Status:** Planning document only. No application changes were made as part of this audit.

## Purpose

This document records a complete read-only review of the Neight source code,
project documentation, known-bug notes, dependencies, settings and saving
behavior, platform integrations, build scripts, and recent relevant history.

The goals of the review were to identify how to:

- update the application to current libraries safely;
- improve performance, especially for large files;
- make Tamil and mixed-script rendering as reliable as Qt permits;
- reconcile overlapping or conflicting fixes;
- improve saving, recovery, fonts, and keyboard behavior on Windows and macOS;
- repair Writer Mode and Techie Mode implementation drift;
- improve macOS trackpad movement and zoom;
- diagnose cursor-placement and last-line problems on both platforms;
- make the codebase cleaner, testable, and reproducible.

## Review Scope and Evidence

The audit covered:

- the complete [`neight.py`](../neight.py) source file;
- [`README.md`](../README.md), [`ADVANCED.md`](../ADVANCED.md),
  [`DEVELOPER.md`](../DEVELOPER.md), [`PRIVACY.md`](../PRIVACY.md), and the
  website files under [`docs/`](../docs/);
- every document in this `knownbugs` folder;
- dependency, build, packaging, and release files;
- recent Git history related to fonts, scrolling, cursor visibility, Windows
  and macOS synchronization, and Tamil rendering;
- the Python interpreter and imports selected by VS Code/Pylance;
- current and latest package versions reported by the package index.

The Windows workspace was clean during the review. Pylance reported no errors
and no unresolved imports. Its informational warnings were primarily unused
imports/parameters and code branches statically unreachable on Windows.

### Important limitation

This audit was performed on Windows. macOS-only code was read and compared with
history and documentation, but it was not executed on macOS hardware. All
macOS rendering, input-source, native-gesture, signing, and Finder integration
changes must therefore be validated on a real Mac before release.

## Executive Summary

Neight has a good functional foundation. It already uses `QPlainTextEdit`,
atomic replacement for several writes, background autosave, debounced status
updates, Unicode-aware token classification, platform-native keyboard APIs,
and detailed notes for difficult Qt rendering behavior.

The largest risks are not missing features. They are interactions between
many individually reasonable fixes:

1. Multiple application processes read and overwrite the same settings file.
2. Applying settings can emit connected action signals and save a partially
   applied configuration.
3. Document saving, autosave, and watchdog recovery can race with each other.
4. The custom line-spacing layout, viewport margins, word wrapping, and cursor
   scrolling all influence the same Qt geometry.
5. macOS trackpad deltas are not accumulated correctly, and native pinch
   gestures are not handled.
6. Large documents still trigger full-document copies and scans.
7. Writer Mode and Techie Mode duplicate hundreds of lines of state mutation.
8. There are no automated tests to protect the platform-specific workarounds.
9. The macOS build cannot be reproduced from a clean clone as documented.
10. Network and settings-location claims conflict across documentation.

The recommended order is to establish tests first, repair persistence and
saving second, then work on input/rendering and performance. Refactoring the
large source file should happen only after behavioral tests exist.

## Current Environment and Library Status

### Selected Python environment

VS Code/Pylance selected:

```text
c:\DevTemp\neight\.venv\Scripts\python.exe
```

The environment is based on Python 3.12. All project imports resolve.

### Installed and latest versions on the audit date

| Package | Installed | Latest reported | Recommendation |
|---|---:|---:|---|
| PySide6 | 6.10.1 | 6.11.1 | Test 6.10.3 first, then 6.11.1 |
| Markdown | 3.10.1 | 3.10.2 | Low-risk patch update after tests |
| Pillow | 12.1.1 | 12.3.0 | Move to design/development dependencies |
| PyInstaller | 6.18.0 | 6.21.0 | Update after build specs are fixed |
| pre-commit | Not installed | 4.6.1 | Install as a development dependency |

[`requirements.txt`](../requirements.txt) uses broad lower bounds such as
`PySide6>=6.0.0`. This does not produce repeatable builds and permits large Qt
behavior changes without review. Runtime, development, design, and packaging
dependencies are also mixed together.

## Findings

Each finding is marked as one of:

- **Verified:** directly demonstrated by current source, documentation, or
  repository history.
- **Documented:** reported in the repository but not reproduced during this
  Windows audit.
- **Hypothesis to test:** a plausible cause requiring a focused runtime test.

## 1. Settings and Preferences

### 1.1 Settings are stored in the wrong primary location

**Status:** Verified  
**Priority:** Critical

[`SettingsManager`](../neight.py#L541-L689) first tries to place
`settings.json` beside the script or executable. For a frozen macOS
application this can be inside `Neight.app`. Replacing or deleting the bundle
can therefore remove preferences.

This conflicts with [`ADVANCED.md`](../ADVANCED.md#L280-L365), which later
states that macOS settings always live under `~/.config/Neight/` and survive
application replacement. [`release_install_notes.md`](../release_install_notes.md)
records the opposite behavior and calls it a known issue.

**Recommended direction:**

- Use `QStandardPaths.AppConfigLocation` as the only normal settings root.
- On Windows, resolve to the user's local application-data area.
- On macOS, resolve to an appropriate user Library location.
- Migrate once from the executable directory, `~/.config/Neight`, and legacy
  `config.json` locations.
- Record the migration version so old files are not imported repeatedly.

### 1.2 Multiple processes overwrite one settings file

**Status:** Verified  
**Priority:** Critical

[`new_window()`](../neight.py#L3060-L3087) starts a detached subprocess. Each
process loads a complete settings dictionary into `_settings_cache` and later
writes the entire dictionary from [`_save_preferences()`](../neight.py#L6352-L6452).

This creates lost updates. For example, one window can change a font while a
second window changes margins, and the second save can restore the old font.
Closing windows in a different order can change the final result.

The settings writer also uses the same `.tmp~` path in every process. Two
processes can write or replace that temporary file concurrently. Atomic rename
prevents a partially written final JSON file, but it does not prevent temp-file
collisions or stale whole-dictionary overwrites.

**Preferred fix:** keep all windows in one `QApplication` process. The
application should own a list of `Notepad` windows and a single preference
store. This removes most cross-process preference races and simplifies macOS
file-open event routing.

**Fallback if subprocess windows are retained:**

- use `QLockFile` around read-modify-write operations;
- use a revision number and key-level merge;
- use unique temporary files;
- reload before each merge rather than writing a stale in-memory snapshot;
- define which settings are application-wide and which are window-local.

### 1.3 Applying settings can write settings

**Status:** Verified  
**Priority:** Critical

[`_apply_settings_dict()`](../neight.py#L6069-L6230) says it applies settings
without disk I/O. However, action signals were connected before startup
preferences are loaded. Calls such as these can emit `toggled` signals:

- `wrap_act.setChecked(...)`;
- `line_numbers_act.setChecked(...)`;
- status-item action `setChecked(...)` calls;
- `unicode_substring_highlight_act.setChecked(...)`;
- `word_index_act.setChecked(...)`.

Their handlers call `_save_preferences()`. During startup, `_settings_cache`
has not yet been populated with the loaded data, so a handler can persist a
partially applied or default-heavy settings dictionary.

**Recommended fix:**

- Add an `_applying_preferences` transaction flag.
- Use `QSignalBlocker` for every action synchronized from settings.
- Make save handlers return immediately while a transaction is active.
- Apply and validate all values first.
- Refresh dependent UI once.
- Save at most once, and only when the caller explicitly requests it.

### 1.4 Save failures are often hidden

**Status:** Verified  
**Priority:** High

Several `_save_preferences()` and direct `settings.save(...)` calls ignore the
boolean result. `_save_preferences()` also catches every exception without
reporting it. The UI may say that a mode or preference was applied even when it
was not persisted.

**Recommended fix:** return a result from `_save_preferences()`, retain the
last error, and show one non-repeating warning. Debug Info should expose the
active path, last successful save time, last error, and migration status.

### 1.5 Settings validation is incomplete

**Status:** Verified  
**Priority:** Medium

Numeric normalization is generally good, but:

- an unavailable font family is passed to Qt and silently substituted;
- a deleted or disconnected default directory remains configured;
- URL prefix validation checks only the scheme prefix;
- broad exception handling can hide malformed values.

Use `QFontDatabase`/`QFontInfo`, verify directories, parse URLs structurally,
and centralize a typed settings schema.

## 2. Document Saving, Autosave, and Recovery

### 2.1 Manual save is less durable than autosave

**Status:** Verified  
**Priority:** High

[`_write_to_path()`](../neight.py#L3299-L3330) writes a temp file and calls
`os.replace`, but does not flush and `fsync` before replacement. Autosave and
recovery do both.

**Recommended fix:** use `QSaveFile` or one shared durable atomic-write helper
for manual save, autosave, recovery, settings, and presets. Preserve permissions
where appropriate and use unique temp files.

### 2.2 Save As commits the path before the write succeeds

**Status:** Verified  
**Priority:** High

`save_file_as()` assigns `current_path`, updates the default directory, and
changes export visibility before `_write_to_path()` reports success. If writing
fails, the window can appear associated with a file that was never saved.

**Recommended fix:** treat Save As as a transaction. Keep the proposed path
local, write successfully, then commit `current_path`, recent-directory state,
title, export actions, modified state, and recovery cleanup.

### 2.3 Encoding and newline style are not preserved explicitly

**Status:** Verified  
**Priority:** High

The loader accepts UTF-8, UTF-16, and UTF-32, but saving always uses UTF-8.
Python universal newline handling can also normalize the original newline
style. This silently changes file representation even when visible text is
unchanged.

**Recommended fix:** store document metadata with each open window:

- detected encoding;
- BOM presence;
- newline style (`LF`, `CRLF`, or `CR`);
- final-newline presence;
- last known file modification time and size;
- optionally a content hash for conflict detection.

Default new files to UTF-8 without BOM and the platform-appropriate newline,
but preserve existing files unless the user explicitly converts them.

Unicode normalization must remain an explicit command. It should not run
automatically on open or save.

### 2.4 External changes are not detected

**Status:** Verified  
**Priority:** High

There is no protection against another editor or another Neight window changing
the current file. Autosave can overwrite those changes without warning.

Use `QFileSystemWatcher` plus an mtime/size/hash check before save. Offer Reload,
Save As, Overwrite, or Compare/Cancel. Suppress watcher events generated by the
application's own atomic replacement.

### 2.5 Manual save and autosave can collide

**Status:** Verified  
**Priority:** Critical

Manual save and autosave use the same PID-qualified temp filename for a target.
They can operate concurrently within one process. One operation can replace or
delete the other's temp file.

Use a per-document save coordinator. Only one write may commit at a time. A
manual save should supersede a queued autosave and use a unique operation ID.

### 2.6 The autosave watchdog can permit stale overwrite

**Status:** Verified  
**Priority:** Critical

When the watchdog decides a worker is hung, it clears `_autosave_in_progress`.
A new autosave can then start while the first thread remains alive. If the old
thread eventually completes after the new one, it can replace the file with an
older snapshot.

Use monotonically increasing save generations. A worker may commit only if its
generation is still current. Prefer a single serialized worker queue rather
than independent daemon threads. The watchdog should mark a generation stale,
not merely clear a boolean.

### 2.7 Recovery cleanup is thoughtfully designed but needs tests

**Status:** Verified positive behavior  
**Priority:** Medium

The recovery path is cleared before deletion, and a late worker result removes
the now-unneeded file with `missing_ok=True`. This handles a common save-while-
recovery-is-running race well.

Tests should still cover close, Save As, New, Open, failed writes, disabled
autosave, and a worker finishing after cleanup.

## 3. Fonts, Unicode, and Tamil Rendering

### 3.1 A single font family is insufficient for consistent mixed-script UI

**Status:** Verified design limitation  
**Priority:** High

The editor, menu actions, and status bar often receive one hardcoded family.
On macOS, a Tamil-capable family can provide Latin glyphs that do not resemble
the native UI font. On Windows, a Latin UI family may rely on implicit fallback
for Tamil.

**Recommended fix:** use explicit fallback-family lists with
`QFont.setFamilies()` where supported. Resolve semantic font roles rather than
hardcoding one family everywhere:

- system UI role;
- Tamil-capable UI fallback role;
- writer serif role;
- technical monospace role plus Tamil fallback;
- PDF export role.

Validate the resolved family with `QFontInfo` and character support with
`QRawFont` or equivalent probes. Store the user's requested family separately
from the family Qt actually resolved.

### 3.2 macOS status-bar font workaround remains unresolved

**Status:** Documented and verified in current code  
**Priority:** Medium

[`Tamil font rendering in status bar on macOS.md`](Tamil%20font%20rendering%20in%20status%20bar%20on%20macOS.md)
explains that setting a Tamil font globally changes the appearance of ordinary
Latin status text. The current source still sets the status-bar font globally.

The preferred long-term solution is a fallback family stack. A temporary font
swap around two messages is acceptable only if the fallback stack cannot be
made reliable on the supported Qt/macOS versions.

### 3.3 Tamil caret segmentation is currently a Qt limitation

**Status:** Documented; requires retest on newer Qt  
**Priority:** High

[`Bug in QT for Tamil text handling.md`](Bug%20in%20QT%20for%20Tamil%20text%20handling.md)
records consonant/pulli navigation behavior in Qt 6.10.0. The application does
not currently override grapheme navigation.

Before adding custom cursor logic:

1. Reproduce on PySide6/Qt 6.10.1, 6.10.3, and 6.11.1.
2. Test Windows 11 and the supported macOS versions.
3. Test arrow movement, Shift-selection, Backspace, Delete, Home/End, mouse
   placement, and IME composition.
4. Check Qt bug reports and release notes.
5. Submit or update an upstream Qt reproducer if the issue remains.

A local workaround that moves by code point could split valid combining
sequences or interfere with IME composition. It should not be implemented
without a complete behavior matrix.

### 3.4 Last-line descender fix is present but intertwined with geometry

**Status:** Verified current implementation; visual retest required  
**Priority:** High

The current combination of custom last-block height and document margin is
described in
[`Tamil last line descender clipping at end of document.md`](Tamil%20last%20line%20descender%20clipping%20at%20end%20of%20document.md).
The recorded measurements are encouraging.

However, the same code also controls viewport snapping, line-spacing edge
margins, wrapping, line numbers, overlays, and scrollbar range. Treat these as
one layout subsystem and test them together. Do not optimize one component in
isolation.

### 3.5 Unicode correctness needs fixture-based tests

**Status:** Testing gap  
**Priority:** High

Create byte-preserved fixtures rather than retyping Tamil test strings during
future automated work. Tests should verify:

- load-save byte preservation when no conversion was requested;
- UTF-8, UTF-8 BOM, UTF-16 LE/BE, and UTF-32 where supported;
- NFC command changes only the selected/document text intended;
- word tokenization includes combining marks;
- selection and clipboard round trips preserve code points;
- PDF export uses a font containing all required glyphs;
- no source or documentation Tamil string is modified by automated formatting.

## 4. Keyboard Layout Behavior

### 4.1 Keyboard selection is based on auto-detection and list order

**Status:** Verified  
**Priority:** High

The application detects the first Tamil and first English family entries, or
uses the first two installed layouts in dynamic mode. Users cannot select and
persist an arbitrary exact pair from the dialog.

Store the two selected platform-native identifiers explicitly. If an identifier
is missing after an OS update, retain it as unavailable and ask the user to
choose a replacement rather than silently selecting another layout.

### 4.2 Startup keyboard policy should be explicit

**Status:** Product decision required  
**Priority:** High

Recommended default: launching, saving, opening a dialog, or changing fonts
must not alter the system keyboard. Writer Mode may offer an optional switch to
the configured Tamil source, but this should be visible and user-controlled.
Techie Mode may optionally switch to the configured English source.

### 4.3 Shortcut semantics need platform validation

**Status:** Hypothesis to test  
**Priority:** High

Qt maps Control, Meta, Command, and portable `QKeySequence` text differently on
macOS. The hardcoded layout shortcuts may not match their labels and can
conflict with conventional macOS shortcuts.

Create shortcuts from explicit Qt modifiers, display them using native text,
and test the actual keys on both platforms. The double-modifier detector should
ignore auto-repeat, shortcut chords, modal/native dialogs, and focus changes.

### 4.4 Platform keyboard code should be isolated

**Status:** Maintainability finding  
**Priority:** Medium

Windows registry/WinAPI logic, macOS TIS/CoreFoundation logic, global detected
choices, and UI behavior currently share one module. Extract a small
`KeyboardLayoutService` interface with Windows, macOS, and unsupported-platform
implementations. Unit-test classification and selection with mocked platform
results; run real switching tests only on target machines.

## 5. Writer Mode and Techie Mode

### 5.1 Mode application is duplicated procedural code

**Status:** Verified  
**Priority:** High

The two mode methods manually update actions, labels, timers, flags, fonts,
theme, settings, and status text in separate large blocks. Some operations use
shared helpers and signal blocking while others update widgets directly. This
is a major source of future drift.

Replace each mode implementation with a declarative validated dictionary. A
single transaction-based `apply_preset` method should:

1. merge the preset with preserved machine/window-local values;
2. validate and normalize every setting;
3. block UI signals;
4. apply application state;
5. update dependent widgets and timers once;
6. resolve fonts through semantic roles;
7. optionally switch the configured keyboard source;
8. persist once and report any error.

### 5.2 Built-in and user presets use overlapping save logic

**Status:** Verified  
**Priority:** Medium

Preset export excludes machine-local keys, but rewriting a bad preset uses the
entire settings cache in the mode methods. This can reintroduce keys that normal
preset export deliberately removes.

Use one preset serialization helper and one list of portable keys for normal
save, repair, migration, and tests.

### 5.3 Font descriptions and actual families need alignment

**Status:** Verified documentation/design mismatch  
**Priority:** Medium

Mode descriptions use semantic terms such as large Tamil serif or compact
monospace-friendly font, but hardcoded platform choices do not always satisfy
those semantics for both Latin and Tamil. Define and test the visual roles,
then document resolved defaults separately for each platform.

## 6. Trackpad, Mouse, Zoom, and Scrolling

### 6.1 Small nonzero trackpad deltas are discarded

**Status:** Verified  
**Priority:** Critical for macOS usability

[`CodeEditor.wheelEvent()`](../neight.py#L1637-L1651) computes integer steps
from `angleDelta()/120`. If the result is zero but `angleDelta` itself is
nonzero, the `pixelDelta` fallback is skipped. Smooth trackpads commonly
produce exactly this pattern.

Maintain fractional angle and pixel accumulators. Consume a zoom step only
after crossing a threshold, retain the remainder, and reset appropriately when
gesture direction changes.

### 6.2 One wheel event can cause many expensive updates

**Status:** Verified  
**Priority:** High

For a large delta, `wheelEvent()` calls `_change_font_size()` repeatedly.
Every call changes the document font, recomputes spacing and margins,
invalidates overlays, saves preferences, and posts a status message.

Calculate one bounded target size per event or gesture. Apply layout once and
debounce preference persistence until the gesture is idle.

### 6.3 Native pinch zoom is not implemented

**Status:** Verified absence  
**Priority:** High on macOS

There is no handling for `QNativeGestureEvent` zoom events. Add native gesture
support only after verifying Qt's event sequence on supported macOS versions.
Prevent duplicate zoom when the same gesture also generates wheel events.

### 6.4 Normal trackpad scrolling should remain Qt-native

**Status:** Recommended constraint  
**Priority:** High

Do not replace ordinary two-finger scrolling with custom movement logic unless
a reproducible Qt defect requires it. Let `QPlainTextEdit` handle kinetic and
pixel scrolling. Custom code should be limited to zoom recognition, threshold
accumulation, and verified boundary correction.

## 7. Cursor Placement, Wrapping, and Custom Layout

### 7.1 Cursor-visibility protection was removed but documentation says it remains

**Status:** Verified from history  
**Priority:** Critical investigation

Commit `ca5a73d` removed approximately 61 lines, including:

- the deferred `_cursor_vis_timer`;
- the `cursorPositionChanged` connection;
- `_schedule_cursor_visibility_check()`;
- `_ensure_cursor_line_fully_visible()`;
- the navigation-key fallback for boundary presses.

The last-line known-bug document still says this strengthening was kept. This
is a concrete conflict between current source, history, and documentation.

Do not restore the old code blindly. First reproduce the cursor error with the
current layout, then compare current behavior, the historical guard, and stock
`QPlainTextDocumentLayout` under identical tests.

### 7.2 Line spacing mutates QTextLine positions in blockBoundingRect

**Status:** Verified architecture risk  
**Priority:** High

[`SpacedPlainTextDocumentLayout`](../neight.py#L1022-L1112) repositions every
visual line whenever `blockBoundingRect()` is queried. Painting, hit-testing,
cursor rectangles, scrolling, line-number drawing, and overlays all query block
geometry. Very long wrapped paragraphs can therefore be expensive, and stale
or repeatedly adjusted layout state is a plausible contributor to cursor
placement errors.

Instrumentation should record:

- logical cursor position, block number, and position within block;
- `cursorRect` and block geometry;
- scrollbar value/range/page step;
- viewport dimensions and margins;
- wrap mode, line spacing, font, and device pixel ratio;
- results before and after resize, zoom, scroll, click, and navigation.

### 7.3 Wrap refresh toggles wrapping off and on

**Status:** Verified  
**Priority:** High

`_refresh_wrap_layout()` switches from `NoWrap` to `WidgetWidth` to force Qt to
recompute wrapping. On large documents this can be expensive and may disturb
scroll or cursor geometry.

Test alternatives supported by the target Qt version, including targeted
layout invalidation or allowing the viewport resize to drive reflow. Preserve
logical cursor position, selection, first visible block, and scroll offset
during any forced reflow.

### 7.4 Viewport margins are calculated in multiple interacting stages

**Status:** Verified  
**Priority:** High

Margins combine line-number width, percentage text margins, word-index top
space, line-spacing edge space, document margin, last-block extra height, and a
bottom snap remainder. `setViewportMargins()` can be called twice during one
calculation.

Refactor this into a pure margin-calculation function plus one application
call. Cache the final tuple and skip identical updates. Add invariants ensuring
the viewport remains positive and the text area retains a documented minimum
width and height.

### 7.5 Required cursor regression matrix

Test both one-line and large documents with:

- wrap on and off;
- every line-spacing preset;
- margins from 0 to 25 percent;
- line numbers and Word Index on and off;
- font sizes from 6 to 100 points, with special attention to 10-28 and 24;
- mixed Latin/Tamil fixtures;
- one extremely long wrapped paragraph;
- at least 10,000 and 100,000 logical lines;
- Home, End, platform document-start/end shortcuts, arrows, Page Up/Down;
- mouse and trackpad clicks near the bottom and right edge;
- selection drag and Shift-navigation;
- zoom during a selection;
- 100%, 125%, 150%, and 200% display scaling where available.

The acceptance criterion is that logical cursor position, visual caret,
selection, clicked position, and line/column status all agree.

## 8. Performance and Large Files

### 8.1 The 50 MB limit is not a performance guarantee

**Status:** Verified design issue  
**Priority:** High

The loader accepts files up to 50 MB, but several features make complete text
copies or full-document passes. A file being below the limit does not mean the
full feature set remains responsive.

Benchmark by document shape, not only byte size:

- many short lines;
- a few extremely long wrapped paragraphs;
- ASCII-only text;
- mixed-script text;
- text with many matches for highlighting;
- Word Index enabled and disabled.

### 8.2 Status updates copy and scan the whole document

**Status:** Verified  
**Priority:** High

The 250 ms debounce helps typing bursts, but `_update_status_bar()` calls
`toPlainText()` and then tokenizes/splits the full document whenever relevant
counters are enabled.

Consider incremental counts based on `contentsChange(pos, removed, added)` or a
background snapshot strategy. Do not read Qt document objects from worker
threads. Capture immutable text or affected blocks on the UI thread.

### 8.3 Text changes bypass part of the highlight debounce

**Status:** Verified  
**Priority:** High

[`_on_text_changed()`](../neight.py#L7410-L7416) directly calls
`_update_word_highlights()` after invalidating the selected-word cache. This can
perform a full-document search during editing even though selection changes use
an 80 ms timer.

Schedule the scan through the existing timer, cancel it when no eligible
selection exists, and avoid scanning while the user is actively composing text
through an IME.

### 8.4 Word Index rebuilds the whole document cache

**Status:** Verified  
**Priority:** Medium to high

The overlay uses sensible cursor and font-metric reuse and suppresses repeated
typing-burst rebuilds. Its cache rebuild still walks every block and extracts
every word span.

Potential improvements, to be benchmarked:

- incremental cache updates from `contentsChange`;
- cache stable block identity/revision rather than only block numbers;
- compute visible labels from visible blocks while maintaining prefix totals;
- disable or warn for extremely large documents;
- move token extraction of immutable strings off the UI thread only if safe.

### 8.5 Introduce a visible Large Document Mode

**Status:** Recommendation  
**Priority:** High

When configurable thresholds are crossed, offer a mode that defaults to:

- Word Index off;
- whole-document match highlighting off;
- reading-time and sentence counting off;
- wrap off for pathological long lines;
- delayed or manual statistics refresh;
- a clear status indication and an option to re-enable features.

The threshold should be based on bytes, block count, and maximum block length,
not bytes alone.

## 9. Architecture and Maintainability

### 9.1 The main source file is too large for safe platform work

**Status:** Verified maintainability risk  
**Priority:** High after tests

`neight.py` contains approximately 7,800 lines. `Notepad` owns menus, dialogs,
settings, platform keyboard behavior, file I/O, recovery, network requests,
Markdown transformations, PDF export, themes, modes, and status computation.

The single-file design once improved portability, but it now makes ownership
and side effects difficult to see. It also causes Pylance on Windows to skip
analysis of statically false macOS branches.

### 9.2 Recommended conservative module boundaries

Extract only after tests exist, one module at a time:

1. `neight_core/settings.py`
   - schema, defaults, migration, validation, atomic store;
2. `neight_core/documents.py`
   - encoding/newline metadata, open/save coordination, conflict detection;
3. `neight_core/autosave.py`
   - serialized generations and recovery;
4. `neight_platform/keyboards.py`
   - interface and platform implementations;
5. `neight_ui/editor.py`
   - `CodeEditor`, line numbers, layout, overlays;
6. `neight_ui/main_window.py`
   - window actions and orchestration;
7. `neight_core/presets.py`
   - declarative Writer/Techie settings and portable preset serialization;
8. `neight_core/text_tools.py`
   - tokenization, counts, normalization helpers, Markdown text transforms;
9. `neight_core/update_check.py`
   - explicit network policy and update worker;
10. `neight_app.py`
    - application startup, window registry, file-open event routing.

Keep `neight.py` as a small compatibility entry point if desired.

### 9.3 Broad exception handling obscures defects

**Status:** Verified  
**Priority:** Medium

Many platform and settings paths use `except Exception: pass`. Some are
appropriate at OS integration boundaries, but others hide configuration,
font, save, and state errors.

Catch expected exceptions narrowly, log diagnostic context locally, and show a
single user-facing message only when action is required.

## 10. Build, Packaging, Release, and Dependencies

### 10.1 The documented macOS spec is not version-controlled

**Status:** Verified  
**Priority:** Critical for releases

[`buildme_mac_app.sh`](../buildme_mac_app.sh#L34-L47) says it uses a committed
`Neight.spec` preserving `info_plist`, `argv_emulation`, and file associations.
[`DEVELOPER.md`](../DEVELOPER.md#L70-L83) makes the same claim.

However, `.gitignore` ignores every `*.spec`, and `Neight.spec` has no Git
history. The local file is a Windows-style `EXE` spec with no `BUNDLE`, no
`COLLECT`, no `info_plist`, and `argv_emulation=False`. A clean clone therefore
does not contain the macOS build input described by the scripts.

**Recommended fix:**

- explicitly unignore and commit stable platform specs;
- use separate names such as `packaging/Neight.windows.spec` and
  `packaging/Neight.macos.spec`;
- stop the Windows command from regenerating the macOS source of truth;
- test both specs in CI;
- verify macOS file associations and bundle identifiers from the built plist;
- keep signing/notarization credentials outside the repository.

### 10.2 Requirements are not reproducible

**Status:** Verified  
**Priority:** High

Introduce `pyproject.toml` with groups or extras:

- runtime: PySide6, Markdown;
- PDF highlighting only if promised: Pygments;
- test: pytest, pytest-qt, coverage;
- quality: Ruff, Pyright or configured Pylance checks;
- build: PyInstaller;
- design: Pillow;
- hooks: pre-commit.

Use a reviewed constraints/lock file for release builds. Dependabot or Renovate
may propose updates, but releases should remain pinned and reproducible.

### 10.3 Upgrade Qt in controlled steps

**Status:** Recommendation  
**Priority:** High

Do not jump directly from 6.10.1 to 6.11.1 in the release build.

1. Run the full matrix on 6.10.1 as baseline.
2. Test 6.10.3 and record rendering/cursor differences.
3. Test 6.11.1 separately.
4. Compare Tamil navigation, shaping, line heights, menus, dialogs, PDF output,
   keyboard APIs, trackpad events, and PyInstaller bundles.
5. Pin the chosen version and its matching `shiboken6` package.

### 10.4 Release binaries are tracked in Git

**Status:** Verified  
**Priority:** Medium

Windows and macOS binary artifacts are committed under `dist/` and `stable/`.
This increases repository size and makes source commits carry opaque binary
changes.

Move release artifacts to GitHub Releases after changing website and README
links to release assets. Keep checksums and release notes in Git if desired.

### 10.5 CI is insufficient

**Status:** Verified  
**Priority:** Critical

The existing workflow protects one Tamil spelling and pre-commit checks BOM and
line endings. There is no syntax, test, type, lint, package, or platform build
job.

Add CI jobs for:

- Python syntax and import checks;
- Ruff without automatic source rewriting in CI;
- Pylance/Pyright diagnostics with platform modules separated so both branches
  can be analyzed;
- unit and pytest-qt tests on Windows and macOS;
- offscreen Qt geometry tests;
- visible/screenshot tests where hosted runners permit them;
- Windows executable smoke build;
- macOS app bundle smoke build and plist assertions;
- Tamil guard and UTF-8/line-ending checks;
- artifact checksums and version consistency.

## 11. Documentation and Privacy

### 11.1 Network claims contradict automatic update behavior

**Status:** Verified  
**Priority:** Critical documentation/product decision

The application schedules a GitHub Releases API request five seconds after the
window is shown. Yet:

- [`PRIVACY.md`](../PRIVACY.md#L35-L43) says network access occurs only after
  explicit user action and that there are no background connections;
- [`docs/index.html`](../docs/index.html#L880-L885) advertises zero network
  calls;
- other README/website sections correctly describe the automatic update check.

Choose one policy:

1. **Privacy-first recommendation:** make update checks manual by default, or
   ask for explicit opt-in on first launch.
2. Keep automatic checks, add a preference, disclose the GitHub request, data
   sent by normal HTTPS metadata, timing, timeout, and failure behavior.

Update all documents in the same change.

### 11.2 Settings-location documentation conflicts internally

**Status:** Verified  
**Priority:** High

`ADVANCED.md` first correctly says the executable directory is preferred, then
later says macOS always uses `~/.config/Neight` and survives deletion. Release
notes record settings loss. Documentation should be updated after the
`QStandardPaths` migration, not before.

### 11.3 Known-bug status needs reconciliation

**Status:** Verified  
**Priority:** Medium

After fixes and tests:

- mark resolved documents as historical and name the validating test;
- keep unresolved Qt limitations clearly separate from app defects;
- update the cursor-visibility note to match current code/history;
- move implementation proposals that are no longer planned into an archive;
- add affected version, last reproduced version, and platform to every bug.

### 11.4 Drag-and-drop file opening remains unimplemented

**Status:** Documented  
**Priority:** Low to medium

[`Drag and drop file from Finder or Explorer.md`](Drag%20and%20drop%20file%20from%20Finder%20or%20Explorer.md)
contains a reasonable proposal. Implement it only after the document-open
transaction and external-change protections are centralized, so drag/drop,
File Open, command-line paths, and macOS file-open events share one safe path.

## Recommended Implementation Plan

## Phase 0: Baseline and Test Harness

**Goal:** Make current behavior measurable before changing it.

### Work

- Add `pyproject.toml` test and quality configuration.
- Add pytest and pytest-qt infrastructure.
- Create byte-preserved fixtures in a test-data directory.
- Add a helper that starts Qt offscreen for geometry tests.
- Add optional visible-window screenshot tests on target machines.
- Capture current performance timings and screenshots.
- Add Windows and macOS CI with the currently pinned dependency versions.
- Preserve the Tamil spelling guard and prohibit automated rewriting of Tamil
  fixture/source strings.

### Minimum tests

- settings load, normalization, corruption, and migration;
- startup application with non-default checked actions and no writes during
  application;
- manual save, failed Save As, encoding, newline, and BOM behavior;
- autosave generation and recovery cleanup;
- preset apply/export/repair;
- font resolution and fallback;
- keyboard-selection logic with mocked lists;
- trackpad delta accumulation as pure logic;
- cursor geometry invariants under wrap, spacing, and margins;
- large-document status/highlight benchmarks.

### Exit criteria

- Current behavior is captured by tests.
- Known failures are marked explicitly rather than hidden.
- CI passes on Windows and macOS using PySide6 6.10.1.

## Phase 1: Persistence and Data Safety

**Goal:** Eliminate settings loss and stale document overwrites.

### Work

- Move settings to `QStandardPaths.AppConfigLocation` with migration.
- Add a typed settings schema and transaction guard.
- Block all action signals during settings/preset application.
- Convert New Window to same-process windows, or add lock/revision/merge if
  subprocesses must remain.
- Centralize durable atomic writes with unique temp paths.
- Add a serialized save coordinator and save generations.
- Make Save As transactional.
- Preserve encoding/newline/BOM metadata.
- Add external-modification detection.
- Surface persistent save failures once and in Debug Info.

### Exit criteria

- Two windows can change unrelated preferences without lost updates.
- Closing windows in any order produces deterministic settings.
- Manual save and autosave cannot race.
- A timed-out worker cannot overwrite a newer save.
- Failed Save As leaves the original document identity unchanged.
- Existing settings migrate and survive application replacement.

## Phase 2: Presets, Fonts, and Keyboard Policy

**Goal:** Make modes and bilingual defaults predictable on both platforms.

### Work

- Replace duplicated mode methods with declarative presets.
- Apply each preset through the settings transaction.
- Centralize portable preset serialization and repair.
- Add semantic platform font roles and explicit fallback families.
- Verify actual resolved fonts and PDF glyph coverage.
- Let users select and persist exact input-source pairs.
- Define startup and per-mode keyboard-switch policy.
- Validate native shortcut display and behavior.
- Isolate platform keyboard services.

### Exit criteria

- Each mode is represented by one data definition.
- Applying a mode causes one settings commit.
- Built-in and custom presets behave identically except for their values.
- Latin and Tamil text use intended fallback families.
- Missing fonts and keyboard sources produce controlled fallbacks.
- No save, file dialog, or ordinary shortcut changes the keyboard unexpectedly.

## Phase 3: Trackpad, Cursor, Layout, and Tamil Rendering

**Goal:** Fix input and geometry behavior with measured evidence.

### Work

- Add smooth wheel-delta accumulation.
- Apply one zoom update per threshold and debounce persistence.
- Add macOS native pinch support with duplicate-event protection.
- Build layout instrumentation and run the full cursor matrix.
- Compare stock layout, current custom layout, and the historical cursor guard.
- Refactor viewport margin calculation into a pure function and one update.
- replace forced wrap toggling if a safer Qt invalidation path is verified.
- Retest Qt Tamil navigation on 6.10.3 and 6.11.1.
- Update or file the upstream Qt issue if needed.

### Exit criteria

- Smooth trackpad zoom works in both directions without jumps.
- Ordinary trackpad scrolling remains native and fluid.
- Cursor logical and visual positions agree across the test matrix.
- Last-line glyphs are visible in real screenshots at supported font sizes.
- No regression in line numbers, selection, overlays, or click placement.
- The chosen Qt version has documented Tamil navigation results.

## Phase 4: Large-Document Performance

**Goal:** Keep typing and navigation responsive under documented limits.

### Work

- Remove immediate whole-document highlight scans from text-change handling.
- Add incremental or deferred statistics.
- Incrementally maintain Word Index data or disable it in Large Document Mode.
- Avoid repeated wrap/layout rebuilds and settings writes during zoom/resize.
- Define thresholds from bytes, block count, and maximum line length.
- Add performance logging available through Debug Info only when enabled.

### Suggested performance budgets

Budgets should be confirmed on representative Windows and Mac hardware:

- ordinary keystroke processing: no visible pause;
- status refresh after idle: under 100 ms for normal documents;
- open 10 MB typical text: target under 2 seconds;
- cursor navigation after open: under one frame for visible-block movement;
- zoom gesture update: one layout update per accepted step;
- no UI-thread operation above 250 ms without progress or feature reduction.

### Exit criteria

- Benchmarks show improvement or no regression against Phase 0.
- Large Document Mode activates predictably and is reversible.
- Typing does not trigger full-document match scans.
- No supported feature causes multi-second UI stalls without warning.

## Phase 5: Dependency and Build Modernization

**Goal:** Produce repeatable Windows and macOS releases.

### Work

- Split runtime and development dependencies.
- Add reviewed lock/constraints files.
- Test and pin PySide6 6.10.3, then evaluate 6.11.1.
- Update Markdown, Pillow, PyInstaller, and pre-commit after tests pass.
- Commit separate platform specs.
- Add CI smoke builds and inspect generated metadata.
- Move distributable binaries to GitHub Releases.
- Add release checks for version, tag, artifact name, architecture, signature,
  plist/file associations, and checksums.

### Exit criteria

- A clean clone can build both unsigned platform artifacts as documented.
- Release builds use pinned versions.
- macOS bundle metadata and Windows icon/file behavior are tested.
- Source commits no longer need opaque binary changes.

## Phase 6: Modular Refactor and Documentation

**Goal:** Reduce maintenance cost without changing behavior.

### Work

- Extract modules in the conservative order listed above.
- Keep each extraction behavior-neutral and test-backed.
- Replace broad exception swallowing with targeted diagnostics.
- Reconcile privacy, settings, update, build, and known-bug documentation.
- Generate architecture documentation from current modules or a maintained
  source rather than a manually stale diagram.

### Exit criteria

- `neight.py` is a small entry point or substantially reduced coordinator.
- Platform services can be tested independently.
- Documentation matches tested behavior and release artifacts.
- Network behavior and settings locations have one unambiguous description.

## Cross-Platform Validation Matrix

Every release candidate touching editor, fonts, keyboard, or saving should run
the following matrix.

| Area | Windows | macOS |
|---|---|---|
| OS | Windows 10 and 11 | Oldest supported plus current macOS |
| Architecture | x64 | Apple Silicon; Intel only if supported |
| Display scale | 100%, 125%, 150%, 200% | Retina and external non-Retina |
| Theme | OS light/dark, forced light/dark | OS light/dark, forced light/dark |
| Font | default UI, writer, technical, custom missing font | same semantic roles |
| Keyboard | configured Tamil and English built-in layouts | configured native input sources |
| Input | typing, composition, shortcuts, clipboard | same plus native shortcut mapping |
| Pointer | wheel, click, drag, selection | trackpad scroll, pinch, click, drag |
| Files | UTF-8/BOM, UTF-16, LF/CRLF, external changes | same plus Finder file-open events |
| Documents | short, 1 MB, 10 MB, near limit, long line | same |
| Layout | wrap, spacing presets, margins, overlays | same |
| Packaging | frozen executable | signed/notarized app bundle |

## Release Acceptance Checklist

- [ ] Pylance/Pyright reports no errors.
- [ ] Ruff reports no new issues in changed code.
- [ ] Unit and pytest-qt suites pass on Windows and macOS.
- [ ] Tamil spelling and UTF-8 guards pass.
- [ ] No existing Tamil source/document string was rewritten by tooling.
- [ ] Settings migrate and survive application replacement.
- [ ] Two-window settings tests pass in both close orders.
- [ ] Save, autosave, watchdog, recovery, and external-change tests pass.
- [ ] Encoding, BOM, and newline round trips pass.
- [ ] Writer Mode and Techie Mode match their declared preset data.
- [ ] Font fallback and keyboard selection are verified on both platforms.
- [ ] Trackpad and cursor matrix passes on real macOS hardware.
- [ ] Tamil last-line screenshots show no clipping.
- [ ] Qt Tamil navigation result is recorded for the pinned version.
- [ ] Large-document benchmark stays within agreed budgets.
- [ ] Clean-clone Windows and macOS smoke builds pass.
- [ ] Generated macOS plist and Windows artifact metadata are checked.
- [ ] Privacy and network documentation matches runtime behavior.
- [ ] Release notes list remaining Qt-level limitations honestly.

## Decisions Required Before Implementation

The maintainer should approve these product/architecture decisions before code
changes begin:

1. Should New Window move to one process, or remain subprocess-based?
2. Should automatic update checks be off by default, opt-in, or always on with
   corrected disclosure?
3. Should existing UTF-16/UTF-32 files be preserved in their encoding, or should
   conversion to UTF-8 be an explicit save option?
4. What is the oldest supported Windows and macOS version?
5. Is Intel macOS support still out of scope?
6. What document size and maximum line length should receive the full feature
   set before Large Document Mode is offered?
7. Should mode keyboard switching be enabled by default or explicitly opted in?
8. Which visual font roles are desired for mixed Latin/Tamil writer and
   technical modes?
9. Should release binaries be removed from Git history going forward and served
   only from GitHub Releases?

## Recommended First Work Package

The safest first implementation package is deliberately narrow:

1. Add settings tests and a startup no-write test.
2. Add `_applying_preferences` plus complete signal blocking.
3. Move settings to `QStandardPaths` with migration tests.
4. Make settings temp files unique and report failed saves.
5. Add two-window close-order tests before changing the window architecture.
6. Add save-generation tests before modifying autosave threads.

This package addresses the most likely causes of font/default inconsistency and
configuration loss without touching Tamil rendering or the custom document
layout. Once it is stable on Windows and macOS, the saving coordinator and
trackpad/cursor phases can proceed with much lower risk.

## Final Assessment

Neight should not be rewritten. Its behavior is valuable and many existing
workarounds encode hard-won platform knowledge. The correct strategy is:

1. capture current behavior with tests;
2. make state and file persistence deterministic;
3. isolate platform integrations;
4. repair trackpad and layout behavior with instrumentation;
5. upgrade Qt under a cross-platform matrix;
6. then split the monolith in small behavior-neutral steps.

Following this order gives the application the best chance of becoming cleaner,
faster, and more reliable without losing the Tamil and bilingual behavior that
motivated the project.