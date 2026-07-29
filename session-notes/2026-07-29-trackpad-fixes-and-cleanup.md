# 2026-07-29 — Trackpad zoom, click placement, build publishing, repository cleanup, docs audit

**Machine:** macOS 26.5.2 · Apple M4 · arm64 · Python 3.14.6 · PySide6 6.11.1
**Version:** `2026.070` → `2026.073` committed (`2026.075` sitting locally, uncommitted — see below)
**Range:** `4b08936` → `196ae11` (13 commits)
**State at close:** `main` clean and in sync with GitHub, all CI green, site deployed —
**except** `neight.py`'s `VERSION` line, which is 2 builds ahead of the last commit. See
["Uncommitted local state at close"](#uncommitted-local-state-at-close).

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

## Uncommitted local state at close

**This machine's working tree is not clean, and the next session should decide
what to do about it rather than be surprised by it.**

At some point after the `2026.073` build/publish commit, `buildme_mac_app.sh`
was run locally at least twice more, outside of any commit in this note. Each
run auto-increments `VERSION` and auto-publishes to `dist-latest` (see "Build
and release infrastructure" below) — both of which happened, and **neither
was committed**:

```
$ git status --short
 M neight.py                       # only the VERSION line differs from HEAD
$ git show HEAD:neight.py | grep VERSION
VERSION = "2026.073"                # what's actually committed
$ grep VERSION neight.py
VERSION = "2026.075"                # what's on disk
$ git log --oneline origin/dist-latest -1
3cce48c Latest unsigned build artifacts   # newer than the 28b5c3e verified in this note
```

So: `dist-latest` on GitHub already serves a `2026.075` build (the publish step
worked exactly as designed — that part is fine, it's meant to run unattended).
What's missing is the corresponding `VERSION = "2026.075"` line landing in a
commit on `main`. Every other build in this note *did* get a matching commit
(`f8faa5e` → `2026.071`, `0fad3fe` → `2026.072`, `bcb7400` → `2026.073`); this
one or two builds did not.

**Nothing is broken** — this is a one-line version bump sitting in an otherwise
clean working tree, not a code defect. But whoever picks this up should either commit
it (`git add neight.py && git commit`, describing why, or folding it into
whatever they build next) or reset it (`git checkout -- neight.py`) before
building again, rather than let a silent third bump happen on top.

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

### 4. The Documents folder was spelled two different ways

Found while double-checking `README.md`/`ADVANCED.md` against the actual code
(below) rather than trusting the prose. Saved presets wrote to
`~/Documents/neight` (lowercase); recovery copies used `~/Documents/Neight`
(capital) — four call sites, two spellings. On macOS and Windows the
filesystem is case-insensitive by default, so those resolved to *one*
directory and the split was completely invisible. On a case-sensitive
filesystem (any Linux build from source) they are two separate folders, and
presets silently stop appearing where the recovery folder is.

Fixed by introducing one constant, `Notepad.USER_DOCUMENTS_DIR_NAME = "Neight"`,
and routing all four call sites through it — chosen over the lowercase spelling
because three of the four sites already used it, and it matches the app name
and the recovery-folder menu label. `_get_user_documents_dir()` also adopts
presets from the old lowercase folder when it is genuinely a separate
directory (`samefile()` check, so it is inert everywhere the filesystem folds
case), copying rather than moving and never overwriting a newer file.

Verified on a real case-sensitive APFS volume (`hdiutil create -fs
"Case-sensitive APFS"`), not just by reading the logic: both presets were
adopted, the lowercase originals survived (copy, not move), a second run with
an edited target left it untouched (no clobbering), and pointing `HOME` at a
normal case-insensitive location made the whole migration path a no-op that
resolved straight to the one existing directory. Full suite green afterward.

`README.md` and `ADVANCED.md` had eight references to the lowercase path;
all corrected in the same commit (`196ae11`).

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
| **`README.md`** | Links the changelog; separately audited line-by-line against the source — see below. |
| **`docs/index.html`** | Live Markdown preview folded into the existing Markdown feature card; menu table updated; second "go deeper" row linking the changelog, architecture diagram and the presentation. |
| **`knownbugs/TRACKPAD-ZOOM-AND-CLICK-FIXES.md`** | New — the full findings record for this session's app fixes. |
| **`session-notes/`** | New — this file and its folder index, written for a cold handoff. Originally placed under `docs/session-notes/`; caught that `docs/` is the GitHub Pages source (confirmed both files were live at `neight.app/session-notes/`, `200`), and moved it to a top-level `session-notes/` before anyone could find it there. Not something a search engine indexed in the ~6 minutes it was live, but worth knowing this folder briefly existed at that URL. |

The `CHANGELOG.md` gitignore entry dated to October 2025, grouped with two
personal scratch files, from when a changelog was replaced by a `changes/` folder
that was itself later removed.

### A note on the website change

Adding the Markdown preview as a **13th** feature card broke the layout — a fixed
3-column grid leaves two empty cells in the final row. This was caught by
rendering it in a browser, then reverted; the content was folded into the existing
Markdown card instead, keeping the grid at a clean 12. Verified at desktop,
tablet and mobile widths.

### `README.md` audit — three more staleness bugs, beyond the two that were asked for

The user asked to remove two obsolete `Future Ideas` lines (Markdown preview —
shipped; Sorkuvai lookup — struck through, not removed). Checking the rest of
the file against the actual code, rather than assuming the prose was still
accurate, found three more:

- **"Open With integration … for `.txt` files"** predated the `.md`/`.markdown`
  associations added in 2026.070. Corrected to describe both extensions,
  that Markdown gets its own ProgID (Explorer shows *Markdown Document*), and
  that Windows has hash-protected the *default*-handler choice since Windows 8
  — Neight's dialog says so rather than pretending to succeed.
- **Zoom** listed only `Ctrl+/-` and `Ctrl+wheel`; macOS trackpad pinch-to-zoom
  has existed since 2026.070 (and was retuned earlier in this session).
- **Auto-save** didn't mention it can be switched off entirely.

Also qualified `Alt+M` in the shortcuts table: it is a Qt menu mnemonic, so it
works on Windows/Linux but not macOS, where menus don't use Alt. It had been
listed unqualified next to genuinely cross-platform shortcuts.

Every remaining shortcut in the table was checked against the actual
`QKeySequence(...)` calls in `neight.py` (all correct), and all 13 local
links/images in the file were confirmed to resolve — several files had been
deleted in the repository-cleanup commit just before this.

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

The Documents-folder case fix (item 4 above) was additionally verified on a
real case-sensitive APFS volume, not just by reading the migration logic — see
that section for the four things checked there.

Also verified: all CI jobs pass on every push in this session (Checks on
Windows + macOS, Tamil Spelling Guard, Pages deployment) — including after the
`session-notes/` move and the `README.md`/Documents-folder commit, both late
additions; the built app launches, `codesign --verify --deep --strict` passes;
the live site at **neight.app** serves the new content and the presentation
(`200`, 686 KB); and, after the `docs/session-notes/` → `session-notes/` move,
`neight.app/session-notes/` was re-checked and confirmed **404** — it is no
longer public.

---

## Open items

1. **Pinch-zoom calibration on a real trackpad** — the only genuinely unverified
   *application behaviour* from this session. Tune `_PINCH_MAGNIFICATION_PER_STEP`.
2. **The local `VERSION` bump is uncommitted.** See "Uncommitted local state at
   close" near the top — this is the most immediate thing to resolve, since it
   affects what the next `buildme_mac_app.sh` run will do.
3. **Nothing is released.** Latest Release is `v2026.065`; `main` is at
   `2026.073` (with `2026.075` sitting uncommitted locally, per above).
   Publishing needs a Developer ID signature, then
   `stable/Neight-mac-arm64-signed.zip`, then `./release_macos.sh`.
4. **Windows build has never run** with the new `dist-latest` publish step. The
   logic mirrors the macOS version, which was verified end to end, but the batch
   implementation itself is untested.
5. Carried forward from July, unchanged: drag-and-drop from Finder (not
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
| `64ef31e` | Add docs/session-notes with a handoff record for this session |
| `c62b5e6` | Move session-notes out of docs/ so it is not published |
| `7002b95` | Bring README up to date with what actually ships |
| `196ae11` | Normalise the Documents folder name to a single spelling |

37 files changed · 1,743 insertions · 3,367 deletions
