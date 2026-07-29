# 2026-07-29 — Trackpad zoom, click placement, build publishing, repository cleanup

**Machine:** macOS 26.5.2 · Apple M4 · arm64 · Python 3.14.6 · PySide6 6.11.1
**Version:** `2026.070` → `2026.073`
**Range:** `4b08936` → `8382501` (9 commits)
**State at close:** `main` clean and in sync with GitHub, all CI green, site deployed

---

## Read this first if you are on Windows

**A plain `git pull` will probably fail, and that is expected.**

On 2026-07-27 the repository history was rewritten with `git-filter-repo` to
strip `dist/` and `stable/` from every commit (127 MB of tracked binaries,
2.68 GB across history). That **changed every commit SHA** and was force-pushed.
If a Windows clone last synced before that date, its `main` shares *no common
ancestor* with GitHub's, and git will refuse with:

```
fatal: refusing to merge unrelated histories
```

Pulling harder will not fix it. Check where you stand:

```bat
git fetch origin
git log --oneline -1 origin/main
git status
```

`origin/main` should be `8382501`. If your local branch has diverged or reports
unrelated histories, **back up any uncommitted work**, then discard local
history and match GitHub — this is destructive:

```bat
git fetch origin --tags --force --prune --prune-tags
git reset --hard origin/main
```

The `--force --prune-tags` matters: all eight version tags were force-pushed in
July, and an ordinary `git fetch` will not update tags that already exist
locally.

> **Simpler and safer: clone fresh into a new folder.** Nothing in the
> repository is machine-specific, and your `settings.json` lives outside it
> (`%APPDATA%`-adjacent on Windows — see `ADVANCED.md`). Build once from the
> new clone, confirm it works, then delete the old folder.

Nothing else needs configuring on Windows. Line endings are handled by
`.gitattributes` — verified from a fresh clone that `.bat` and `.ps1` check out
**CRLF** while `.py`/`.sh`/`.md` stay **LF**.

---

## What was wrong, and what changed

### 1. The caret jumped around long files, and a browser opened uninvited

**This was the headline bug, and the cause was not what it looked like.**

Hit testing was measured *before* any code was touched, and it was already
correct — so **no layout code was changed**. Every block painted in the viewport
was located by its own painted geometry (`firstVisibleBlock` +
`blockBoundingRect`, deliberately *not* `cursorRect`, so the check is
independent of the caret) and clicked at its vertical centre:

- **30 of 30 configurations clean** — wrap on/off × three line spacings × five
  scroll offsets, on both the offscreen plugin and real Cocoa.
- **0 of 248 ASCII caret positions mis-mapped.**
- The only mismatches were 14 *inside Tamil grapheme clusters* — clicking a
  combining mark such as `்` or `ீ` snaps to the cluster boundary, which is
  correct Unicode behaviour, not a defect.
- Clicking a freshly loaded 20,000-line file before layout settled: correct.

The actual culprit was **triple-click-to-search**, and it was inverted:

Qt delivers the second click of a double click as `MouseButtonDblClick`, **not**
`MouseButtonPress`. The old handler counted presses, so it could only ever reach
two — meaning the documented feature **never fired on a real triple click**.
What it *did* fire on was three presses Qt had not paired into a double click,
with no distance test and macOS's generous 500 ms interval. That is precisely
what ordinary clicks to reposition the caret in a long document look like.
Typing in between did not reset the counter either.

Result: a word selected that the user never selected, plus a browser window.

Rebuilt on Qt's own model — `mouseDoubleClickEvent` opens the window in which a
third click counts, and that click must land within `startDragDistance()` (10 px)
of it. Typing, scrolling and focus loss end the sequence. `super().mousePressEvent()`
now always runs, so `QWidgetTextControl` keeps coherent selection and drag state;
the old code returned early and Qt never saw the press at all.

### 2. Zoom

Four separate defects, all in event bookkeeping:

| Defect | Detail |
|---|---|
| **Reversal was damped** | `_consume_zoom_steps` compared the sign of the *accumulator*, not the incoming delta, so a reversal was only noticed once the accumulator crossed zero. After zooming in it took **five** reversed notches for the first step down, against three for the first step up. |
| **Trackpads used the mouse-wheel scale** | The pixel-precise path only ran when `angleDelta` was exactly zero, which on macOS it never is. `pixelDelta` now takes precedence when present. |
| **No gesture boundary** | Travel banked in one gesture ate the start of the next, possibly minutes later. A 250 ms quiet gap now ends a gesture. |
| **Pinch ~3× too fast** | At 0.08 magnification per point, an ordinary pinch moved the font **14 points** and a fast one **18** — from a 12 pt document, the size limit in a single gesture. |

Plus: a dropped `EndNativeGesture` used to disable Ctrl+wheel zoom for the rest
of the session. A pinch idle for 0.5 s is now treated as finished.

**The tunable constants** (`neight.py`, class `CodeEditor`) — these are the knobs
if the feel is still wrong. **Larger is slower** in every case:

| Constant | Value | Governs |
|---|---|---|
| `_PINCH_MAGNIFICATION_PER_STEP` | `0.20` | Pinch-to-zoom speed. ≈5 font points per full pinch; `0.30` ≈ 3. |
| `_PINCH_MAX_STEPS_PER_EVENT` | `1` | Cap so one outsized delta cannot jump several points. |
| `_NATIVE_ZOOM_IDLE_S` | `0.5` | When a pinch with no `End` event is considered finished. |
| `_PIXEL_STEP` | `80.0` | Ctrl + two-finger zoom (trackpad). |
| `_WHEEL_STEP` | `120.0` | Ctrl + wheel zoom (mouse). One notch. |
| `_ZOOM_GESTURE_IDLE_S` | `0.25` | Quiet gap that ends a wheel-zoom gesture. |

> **Still unverified:** nobody has pinched a real trackpad. The arithmetic is
> test-covered and the magnitude is sane; the *feel* is not confirmed. This is
> the one genuinely open item from this session.

### 3. Merged from the maintainer's own commit (`26a4523`)

Arrived on GitHub mid-session and was merged, not overwritten:

- **BOM-less UTF-16/32 detection tightened.** The July heuristic (skip a decode
  leaving NULs, prefer a wide encoding) could itself misclassify a genuine UTF-8
  file containing a real NUL. A lane check now confirms the NULs fall in a
  consistent position (every other byte for UTF-16, every fourth for UTF-32)
  before accepting that decode.
- **`tests/test_text_integrity.py` made newline-aware** via `Notepad.NATIVE_NEWLINE`.
  The "already-correct file must round-trip byte-identically" fixtures were built
  against a bare `\n`, which is *not* what "already correct" means on Windows —
  Neight normalises to CRLF there. The suite had been proving the Windows path
  with Unix newlines.

A merge commit was used rather than a rebase, deliberately: rebasing would have
rewritten `4b08936`, an existing unpushed commit. The two sides touched different
regions of `neight.py` (`Notepad._open_file_path` vs `CodeEditor` input
handling) and auto-merged with no conflicts.

---

## Build and release infrastructure

### The `dist-latest` branch — new, and easy to misread

`dist/` is gitignored on `main` (the July rewrite, above). But an **external
code-signing workflow** fetches the unsigned build over a plain
`raw.githubusercontent.com` URL — and raw URLs only serve files actually
*committed to a branch*. They do not serve Release assets, and they do not serve
ignored files. Committing binaries back to `main` would undo the entire point of
the rewrite.

So `dist-latest` exists: a branch **unrelated to `main`'s history**, holding only
the current Mac and Windows artifacts, at fixed URLs:

```
https://raw.githubusercontent.com/venkatarangan/neight/dist-latest/dist/Neight-mac-arm64-unsigned.app.zip
https://raw.githubusercontent.com/venkatarangan/neight/dist-latest/dist/Neight.exe
```

**Both build scripts publish to it automatically** as the last step of every
successful build — nothing extra to run. Each publish **amends the branch's one
existing commit and force-pushes**, so it is always exactly one commit holding
only current binaries; without that it would slowly become the same binary
graveyard `main` used to be. The macOS and Windows steps each touch only their
own file, so either machine can publish independently without clobbering the
other. Both run inside a throwaway temporary clone, so the real working tree
never leaves `main`, and a failure (no network, no remote) is reported but does
**not** fail the build.

> **Never branch from `dist-latest`, merge it, or commit source to it.**
> This is also recorded in `.github/copilot-instructions.md`.

Verified against the live repository, not just written: first publish creates the
branch from scratch, a second amends rather than appends (hash changed, commit
count stayed 1), a simulated Windows publish coexisted with the Mac artifact in
one tree at one commit, and the raw URL returned `200` with
`content-type: application/zip`.

### `buildme_mac_app.sh` clean-step fix

It removed `dist/Neight.app` but not `dist/Neight` — the COLLECT directory the
spec also writes. PyInstaller refuses to reuse a non-empty output directory, so
**every rebuild after the first failed** with *"the output directory is not
empty"*. This actually happened mid-session, after the version had already been
incremented. Both outputs are now removed.

### Release status — nothing has been published

The latest **GitHub Release is still `v2026.065`** (2026-05-23). Everything since
— all of the July work and this session — is on `main` but **never released**.
`dist/Neight.app` is ad-hoc signed only; `release_macos.sh` deliberately refuses
to publish without a properly signed `stable/Neight-mac-arm64-signed.zip`.

---

## Documentation

| File | What happened |
|---|---|
| **`CHANGELOG.md`** | **Was gitignored the entire time** — `.gitignore:210` excluded it by name, so `git add -A` silently skipped it and it never reached GitHub. Un-ignored and now tracked. Entries added for 2026.071, 2026.072, 2026.073, tagged `[Windows]`/`[macOS]`/`[Both]`. |
| **`DEVELOPER.md`** | New section **"Why `dist/` Isn't on GitHub"** — the C4 history rewrite, and what `dist-latest` is and why it force-pushes. Project layout and regression-suite instructions updated. |
| **`tests/README.md`** | Documents `test_input_gestures.py`. |
| **`release_install_notes.md`** | Gained a "What's in this update" section — it is the body of the GitHub Release and previously described only *how* to install, never *what* changed. |
| **`README.md`** | Links the changelog. |
| **`docs/index.html`** | Live Markdown preview folded into the existing Markdown feature card; menu table updated; second "go deeper" row linking the changelog, architecture diagram and the presentation. |
| **`knownbugs/TRACKPAD-ZOOM-AND-CLICK-FIXES.md`** | New — the full findings record for this session's app fixes. |

The `CHANGELOG.md` gitignore entry dated to October 2025, grouped with two
personal scratch files, from when a changelog was replaced by a `changes/` folder
that was itself later removed.

### A note on the website change

Adding the Markdown preview as a **13th** feature card broke the layout — a fixed
3-column grid leaves two empty cells in the final row. This was caught by
rendering it in a browser, then reverted; the content was folded into the existing
Markdown card instead, keeping the grid at a clean 12. Verified at desktop,
tablet and mobile widths.

---

## Repository cleanup

**Removed from `knownbugs/`** (11 files → 6). Five documents whose content now
lives elsewhere:

- `Comprehensive modernization audit and plan.md`, `Independent assessment and fix plan.md`,
  `MACOS-TODO-pending-validation.md` — superseded by `MACOS-VALIDATION-RESULTS.md`
  and `CHANGELOG.md`
- `Issues to fix.md` — its single entry was fixed in 2026.070
- `new window default font issue and fix.txt` — a raw 516-line AI chat transcript

The six real analysis documents were kept.

**Also removed:** `screenshots/Initial Version/` (5 superseded PNGs),
`devnotes/` (two one-line `git pull --rebase && git push` aliases),
`design/White-icons/` (unused alternative icon set; the shipped icons are
`neight.ico`/`.icns` at the root).

Four references would have been left dangling — in `neight.py`,
`tests/test_startup_settings.py`, `tests/README.md` and
`MACOS-VALIDATION-RESULTS.md` — and were rewritten to point at what replaced
them. Verified afterwards that **no reference to any deleted file survives
anywhere in the tree.**

**Deleted on GitHub:** the `pre-history-rewrite-2026-07-27` safety branch. Before
deleting, it was confirmed redundant: all 8 tags are in `main`'s history, and the
releases carry real binaries (v2026.065 has both a 40 MB Mac zip and a 51 MB
`.exe`). Only `main` and `dist-latest` remain.

### Two configuration contradictions

1. **`.pre-commit-config.yaml` was fighting `.gitattributes`.** The
   `mixed-line-ending --fix=lf` hook ran on *every* file including `.bat` and
   `.ps1`, which `.gitattributes` deliberately checks out as **CRLF** so they run
   natively on Windows. The hook rewrote them to LF on every commit — it did
   exactly that to `buildme.bat` mid-session. Those extensions are now excluded.
2. **`.github/copilot-instructions.md` claimed "there is only one branch in this
   repository"**, untrue once `dist-latest` existed. It now describes what that
   branch is and that it must never be branched from, merged, or committed to.

### Size

| | Before | After |
|---|---|---|
| Local `.git` | 856 MB | **56 MB** |
| Fresh `git clone` | ~704 MB | **~57 MB** |

Of that 57 MB, **44.8 MB is the `dist-latest` zip** — source alone is ~11 MB.
That is the standing cost of the raw-URL signing design. For a lean checkout:
`git clone --single-branch --branch main`.

---

## Verification

Regression suite — `tests/`, plain scripts (not pytest) so CI needs nothing
beyond `requirements.txt`:

```bash
QT_QPA_PLATFORM=offscreen python3 tests/test_startup_settings.py   # 3 checks
QT_QPA_PLATFORM=offscreen python3 tests/test_text_integrity.py     # 67 checks
QT_QPA_PLATFORM=offscreen python3 tests/test_cursor_layout.py      # 514 checks
QT_QPA_PLATFORM=offscreen python3 tests/test_input_gestures.py     # 25 checks
```

All green on **both** the offscreen plugin and real Cocoa. (`test_cursor_layout`
reports 514 offscreen and 710 on Cocoa — the count scales with viewport size;
both are correct.)

**`tests/test_input_gestures.py` is new** — 25 checks covering wheel and pinch
accumulation and the triple-click rules. **Nine of them fail on the pre-fix
code**, verified by stashing the fix and running against it, so they guard
behaviour rather than passing vacuously. Native gesture events cannot be
synthesised, so the pinch checks drive `_handle_native_gesture` through a
`FakeGesture` stand-in and assert a point *budget* rather than an exact size,
since the constants are meant to be tuned against real hardware.

Also verified: all CI jobs pass (Checks on Windows + macOS, Tamil Spelling Guard,
Pages deployment); the built app launches, `codesign --verify --deep --strict`
passes, and `Info.plist` reports `2026.073`; the live site at **neight.app**
serves the new content and the presentation (`200`, 686 KB).

---

## Open items

1. **Pinch-zoom calibration on a real trackpad** — the only genuinely unverified
   thing from this session. Tune `_PINCH_MAGNIFICATION_PER_STEP`.
2. **Nothing is released.** Latest Release is `v2026.065`; `main` is at
   `2026.073`. Publishing needs a Developer ID signature, then
   `stable/Neight-mac-arm64-signed.zip`, then `./release_macos.sh`.
3. **Windows build has never run** with the new `dist-latest` publish step. The
   logic mirrors the macOS version, which was verified end to end, but the batch
   implementation itself is untested.
4. Carried forward from July, unchanged: drag-and-drop from Finder (not
   implemented), Tamil/English keyboard switching and `.md` associations (need
   manual verification), bottom-line snapping for mixed-script documents
   (cosmetic), and the Qt Tamil navigation quirk (upstream).

---

## Commits

| Commit | |
|---|---|
| `26a4523` | `reconcilled` — the maintainer's own commit, merged in |
| `ac173df` | Fix trackpad zoom accumulation and triple-click cursor hijacking |
| `b591f1d` | Document the recent Windows and macOS fixes |
| `f8faa5e` | Build 2026.071; fix the macOS build script's clean step |
| `7f6bfce` | Merge origin/main: BOM-less wide-encoding lane check and newline-aware tests |
| `0fad3fe` | Build 2026.072 |
| `bcb7400` | Build 2026.073; auto-publish unsigned builds to a dist-latest branch |
| `e1ec4a1` | Document the trackpad, wide-encoding, and dist-latest work; track CHANGELOG.md |
| `8382501` | Clean out superseded files and reconcile two config contradictions |

34 files changed · 1,304 insertions · 3,347 deletions
