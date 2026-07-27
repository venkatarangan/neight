# macOS Validation — Results

**Run:** 2026-07-27 on macOS 26.5.2 (build 25F84) · Apple M4 · arm64
**Environment:** Python 3.14.6 · PySide6 6.11.1 · Markdown 3.10.2 · Pygments 2.20.0
**Covers:** [`MACOS-TODO-pending-validation.md`](MACOS-TODO-pending-validation.md) and the
Part C decisions it left open
**Starting point:** `74831d3` · **Ending point:** `b13d370`

This records what was actually executed on real Apple hardware, what it found, and what
still cannot be verified without a person at the keyboard. The companion TODO describes
work that had *never* run on macOS; this file is the answer to it.

Note the environment drift from the Windows work, which was Python 3.12.10 / PySide6
6.11.0. Both platforms are now pinned to **6.11.1**, which closes **C2**.

---

## Summary

Everything scriptable in Parts A and B was verified and passes. Four real bugs were found
that the Windows-side work could not have caught, two of them silent text corruption. All
four Part C decisions were taken and implemented. A regression suite now exists and runs in
CI, so none of this depends on remembering to re-check by hand.

| | |
|---|---|
| Bugs found and fixed | 4 |
| Automated checks now committed | 759 (67 text integrity + 692 cursor/layout) |
| Ad-hoc checks run during validation | ~7,700 cursor round trips on a 10,000-line document |
| Still requires manual testing | 5 items (trackpad, keyboard, Finder) |

---

## Bugs found and fixed

These are the substantive findings. None were in the TODO — they were found by reading the
code and round-tripping real files.

### 1. Every save silently destroyed non-breaking spaces — `79a8bc0`

`QTextDocument.toPlainText()` substitutes ASCII lookalikes for a few characters; a
no-break space (U+00A0) comes back as an ordinary space. All three disk-write paths
(manual save, autosave, recovery) and three whole-document transforms (collapse blank
lines, insert blank lines, NFC normalise) read the document that way. Opening a file
containing NBSP — common in anything pasted from a web page — and saving it replaced every
one with a plain space, permanently, with no indication.

Fixed by adding `CodeEditor.documentText()`, which uses `toRawText()` and maps the U+2029 /
U+2028 block separators back to newlines, and routing all six call sites through it.
Byte-identical round trips were confirmed for plain, Tamil, emoji, CRLF, empty and
no-trailing-newline files, so nothing changed except that NBSP now survives.

### 2. BOM-less UTF-16 / UTF-32 files opened as garbage — `79a8bc0`

ASCII encoded as UTF-16 decodes perfectly well as UTF-8, leaving a NUL between every
character, so the file opened looking like `H e l l o`. Decoding now rejects a result
containing NULs and prefers a wide encoding that yields clean text, keeping the NUL-bearing
decode only as a last resort so a genuine UTF-8 file containing a NUL still opens and round
trips exactly as before.

### 3. The built app reported version `0.0.0` — `be08576`

`packaging/Neight.macos.spec` set no `CFBundleShortVersionString` or `CFBundleVersion`, so
PyInstaller defaulted both to `0.0.0`. Every macOS release would have shipped claiming to
be version zero — which also breaks any update comparison based on the bundle version. The
spec now reads `VERSION` out of `neight.py` at build time. This is exactly what **B1** was
written to catch, and it could only be caught by running the build.

### 4. The status bar used a Tamil font for all text — `be08576`

`self.status.setFont()` set Tamil Sangam MN as the *sole* family, so ordinary Latin status
text (`Words: 0`, `Ln 1`, `Col 1`) rendered in Tamil Sangam MN's Latin glyphs instead of
the system UI font. Replaced with `setFamilies([system UI font, Tamil font])` so Qt falls
back per-run and only Tamil picks up the Tamil face. This is **B4**, and the fix is the
fallback stack that document proposed but had never been attempted. Confirmed by rendering
the widget and inspecting the output.

---

## Part A — verification on real hardware

| Item | Result | Evidence |
|---|---|---|
| A1 Pinch-to-zoom | **Partial** | Accumulator logic unit-tested (8 % per point, symmetric, duplicate-suppressed). A real trackpad has still never driven it. |
| A2 Settings location | **Done** | Now `~/Library/Application Support/Neight/settings.json` after C1. Was previously beside the executable. |
| A3 Multi-window font bug | **Pass** | Startup makes **0** writes against a stored non-default font; the bug would have written Qt's default. |
| A4 Cross-window merge | **Pass** | Two windows changing font and margins independently: both changes survive in **both** close orders. |
| A5 Slow trackpad zoom | **Pass** | Six 20-unit deltas accumulate to exactly 1 step (previously 0, event swallowed). Remainder carried; direction reversal not damped. |
| A6 Markdown preview | **Pass (rendering)** | Preview and PDF both produce `codehilite` markup with Pygments tokens, tables, ordered/unordered lists and Tamil; light and dark stylesheets differ. Interactive use still manual. |
| A7 `.md` associations | **Not verified** | Needs the installed app and Finder. Left alone deliberately — see below. |
| A8 Encoding and newline | **Pass** | UTF-8, UTF-8+BOM, CRLF, UTF-16±BOM, UTF-32 all detected correctly; no stray U+FEFF; already-correct files produce no conversion notice and round trip byte-identically. |
| A9 Tamil last-line descender | **Pass** | No clipping at 10 / 14 / 18 / 24 / 28 pt, checked both by screenshot and by asserting the caret stays inside the viewport at the end of the document. |
| A10 Save durability | **Pass** | Atomic write leaves no `.tmp~` behind, aborted writes leave the target untouched, and a failed Save As reverts `current_path` to the original document. |
| A11 Writer / Techie modes | **Pass** | Font, margins, wrap, line numbers, status items and autosave interval all land as documented, and each mode produces **exactly one** settings write. |
| A12 Keyboard switching | **Not verified** | Needs a real keyboard. |

### Cursor placement in long documents

Worth calling out separately, because it was the largest open worry and **no defect was
found**. The property tested is agreement: position → painted caret rect → click at that
rect → position must describe the same visual line.

- **6,802 round trips** on a 10,000-line mixed Tamil/Latin document containing wrapped
  paragraphs, across wrap on/off × three line spacings × three font sizes × two margin
  settings × five scroll positions. Zero disagreements.
- Down-arrow visits consecutive blocks over 300 presses without skipping.
- The caret never leaves the viewport over 400 presses.
- Status-bar Ln/Col agrees with the real cursor position.
- Re-applying the wrap layout moves neither the cursor nor the scroll position.
- Repeated `_apply_viewport_margins()` calls settle instead of creeping.
- Clicking below the last line lands on the last line.

One hypothesis was checked and **disproved**: visual lines inside a wrapped block do *not*
vary in height when scripts are mixed (measured uniform at 19.0 px across five lines), so
positioning them from the first line's height is sound.

---

## Part B

- **B1 macOS build — done.** Built from a genuinely clean clone with a fresh venv.
  `CFBundleIdentifier` is `com.venkatarangan.neight`, document types list plain text and
  Markdown, `codesign --verify --deep --strict` reports *valid on disk* and *satisfies its
  Designated Requirement*, and the app launches. Found and fixed the `0.0.0` version bug
  above.
- **B2 Cursor instrumentation — effectively answered, code untouched.** The measurement
  this item asked for was taken as automated assertions rather than logged instrumentation,
  and found nothing to fix, so no layout code was changed. The removed
  `_ensure_cursor_line_fully_visible()` was **not** restored.
- **B3 Drag and drop from Finder — not implemented.** Still open.
- **B4 Status-bar Tamil font — fixed.** See bug 4 above.

---

## Part C — decisions taken

| | Decision | Status |
|---|---|---|
| **C1** Settings location | macOS-only move to Application Support | Implemented, `af9cae9` |
| **C2** Qt version convergence | Converge on 6.11.1 | Closed — both platforms pinned |
| **C3** Pygments | Add it | Implemented, `c7bb766` |
| **C4** Release binaries in Git | Rewrite history | Done, `b778ce6` — **read the caveat below** |
| **C5** Preset keys | Fix the rest | Implemented, `bea8f93` |

**C1** writes to `~/Library/Application Support/Neight/`, migrating once from the bundle
and then from `~/.config/Neight`, copying and never deleting, and only when the new file
does not already exist. Windows portable behaviour is untouched. Because `self.path` is
never `primary_path` on macOS, the old "silently relocate on write failure" branch cannot
fire there — a failure is reported instead. `ADVANCED.md` and `release_install_notes.md`
were corrected in the same commit.

**C5** went beyond the two named keys: 17 preset-loadable settings now fall back to the
current in-memory value rather than a hardcoded literal. Deliberately excluded, with
reasons in the commit message: `reopen_last_file_on_launch` (comes from the launch
argument, not stored settings), the word-index opacity keys (defaults derive from the
chosen colour) and `autosave_interval` (attribute does not exist before first apply).

### C4 — history rewrite, and the caveat that matters

`dist/` and `stable/` were stripped from all 110 commits with `git-filter-repo`, then
`main` and all eight tags were force-pushed. `.gitignore` now excludes both directories,
and `README.md` and `docs/index.html` were repointed from `blob/main` and `raw/main` URLs
— which would now 404 — to `releases/latest/download/<asset>`, which always resolves to the
current release. Nothing was lost: every binary was already published to GitHub Releases.

**The size benefit is not realised yet.** A safety branch, `pre-history-rewrite-2026-07-27`,
still points at the pre-rewrite history on the remote, which keeps every old binary
reachable:

| Clone | Size |
|---|---|
| `git clone` (default, fetches all branches) | **704 MB** |
| `git clone --single-branch --branch main` | **12 MB** |
| Local `.git` after rewrite | 161 MB |

Once you are satisfied nothing was lost, delete the safety branch and the default clone
drops to roughly the 12 MB figure:

```bash
git push origin --delete pre-history-rewrite-2026-07-27
```

Until then it is doing its job — it is the recovery path if anything turns out to be
missing. A local `git bundle` of the original history was also taken during the run, but it
lives in a temporary directory and should be assumed gone; **the branch is the durable
backup.**

---

## Regression suite

`tests/` now exists, closing the gap the TODO noted, and
`.github/workflows/checks.yml` runs it on Windows and macOS.

```bash
QT_QPA_PLATFORM=offscreen python3 tests/test_text_integrity.py
QT_QPA_PLATFORM=offscreen python3 tests/test_cursor_layout.py
```

Plain scripts, not pytest, so CI needs nothing beyond `requirements.txt`. Both were
confirmed to **fail on the pre-fix code** with exactly the six expected failures and pass
on the fixed code, so they are genuinely guarding the fixes rather than passing vacuously.
The cursor sweep is sized to run in about a second under the offscreen plugin.

---

## Known limitations left open

- **Bottom-line snapping is approximate for mixed-script documents.**
  `_apply_viewport_margins()` computes its "no partial line at the bottom" snap from the
  *first* block's height, but block heights differ across scripts — measured 17 px for
  ASCII against 16 px for Tamil in the same document. A partial line can therefore peek at
  the bottom. It is cosmetic; the cursor sweep covers exactly these documents and found no
  positional disagreement. Fixing it properly means recomputing against the actual
  last-visible line on every scroll, which is the layout surgery **B2** warns against
  attempting without a reason. Left alone on purpose.
- **`_native_zoom_active` has no timeout.** It is set on a pinch and cleared only by
  `EndNativeGesture`. If that event were ever dropped, Ctrl+wheel zoom would stay dead for
  the rest of the session. Low likelihood, but it is a stuck state rather than a degraded
  one.
- **Module split, single-process windows, Large Document Mode** — still deferred, unchanged.

---

## Still needs a person

These cannot be automated on this machine and remain genuinely unverified:

1. **Pinch-to-zoom on a real trackpad** (A1) — smoothness, no double-apply against the
   wheel path, ordinary two-finger scrolling unaffected.
2. **Wheel accumulation feel** (A5) — the arithmetic is proven, the feel is not.
3. **Tamil/English keyboard switching** (A12) — double-⌃ Control, quick-switch, Anjal
   English option.
4. **`.md` file associations** (A7) — needs `Neight.app` in `/Applications` plus Finder.
   Not attempted automatically: a build is already installed and registered under the same
   bundle identifier, and driving Launch Services would have altered the real install.
5. **Markdown preview interactively** (A6) — `⌘⇧M` firing on a Mac keyboard, divider drag
   persistence, live theme switching.

---

## Commits

| | |
|---|---|
| `af9cae9` | macOS: keep settings out of the app bundle (C1) |
| `c7bb766` | Add Pygments so codehilite actually highlights code (C3) |
| `bea8f93` | Preset keys fall back to the current value, not a literal (C5) |
| `be08576` | Fix macOS status bar Tamil font and app bundle version (B4, B1) |
| `b820406` | Merge C1 / C3 / C5 |
| `b778ce6` | Stop tracking release binaries in git; point downloads at Releases (C4) |
| `79a8bc0` | Stop rewriting the user's characters on save |
| `b13d370` | Add a committed regression suite and run it in CI |

Dependencies were also upgraded and pinned at the start of the run: PySide6 / shiboken6
6.11.1, PyInstaller 6.21.0, Pillow 12.3.0, plus `python-pptx==1.0.2`, which `make_slides.py`
imports directly but was missing from `requirements-dev.txt`.
