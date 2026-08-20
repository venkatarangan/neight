# 2026-08-20 — Update checker removed, selection counts added, downloads moved to `dist-latest`

**State at close:** `main` @ `b35a8a7`, working tree clean, `VERSION` =
`2026.081`. macOS was rebuilt at the end of the session, so `dist-latest`
carries a current mac artifact. **Windows was not rebuilt and is the first
thing to do on that machine** — see "Do this first on Windows" below.

Date: 2026-08-20
Context: a long Mac session, nine commits from `552d6ab` to `b35a8a7`. Written
for whoever picks this up next, most likely on the Windows machine.

---

## Do this first on Windows

1. **Run `buildme.bat`.** The `Neight.exe` currently on `dist-latest` is from
   **2026-07-29** — it predates this whole session — and is **68.2 MB against
   the release build's 57 MB**. That gap is the development-environment bloat
   that `CHANGELOG` 2026.076 records as fixed for *releases* by building from a
   clean, runtime-only environment; `dist-latest` gets whatever `buildme.bat`
   produced wherever it ran. Since this session the website and `README.md`
   serve that file directly, so Windows users are being handed a stale, bloated
   binary until this is rerun.
2. Before that, create the venv per `DEVELOPER.md` and run the test suite
   (`tests/README.md`) to confirm the checkout is sound. Expect **934 checks,
   0 failed** across the five scripts.

---

## What changed this session, and why

### The update checker is gone entirely (`ef823a7`)

**Mac App Store review rejected the build over it.** Update-checking machinery
outside the App Store is a standard objection, and it had become redundant
anyway — the Windows build ships through the Microsoft Store and macOS is
headed for the Mac App Store, both of which update automatically.

Removed: `_UpdateCheckWorker`, `_parse_version`, the silent GitHub check fired
5 s after `showEvent`, the **●** badge on the Help menu, the
**Settings → Check for Updates on Launch** toggle, and the manual check dialog.
`QThread` went with it (it was imported solely for that worker); `urllib` and
`json` stayed, still used by URL validation and settings I/O.

**Help → Neight on GitHub** replaced both menu items — a plain
`QDesktopServices.openUrl` to the project page. The app makes no request itself.

Consequence worth knowing: **Neight now makes no automatic network connections
at all.** `PRIVACY.md` was rewritten around that stronger claim. Verified by
running the app 20 s past the old 5 s mark with no network socket open.

The `update_check_on_launch` settings key is no longer read or written. Settings
merge at key level, so existing `settings.json` files and saved presets keep the
orphan key; it is ignored.

### Status bar counts the selection (`9c734a0`)

Select text and the word/sentence/char counters read `Words: 42 of 1240` —
selection and total together, so the two cannot be confused. Reading time
relabels itself `Read (sel):` instead, because a duration reads badly as a ratio.

Two design points that are easy to undo by accident:

- **Appearance is debounced 250 ms; disappearance is not.** Deferring the
  appearance keeps drags and abandoned double-clicks off the status bar.
  Deferring the disappearance would leave numbers describing a selection that no
  longer exists, which reads as a bug. Clearing is free — it re-renders finished
  numbers.
- **Selection text goes through `_get_selected_text`**, which normalises Qt's
  U+2029 paragraph separators to `\n`. Counting `selectedText()` raw drifts from
  `toPlainText()` on any multi-paragraph document — silently, and only for people
  who write in paragraphs. `tests/test_selection_counts.py` pins this by
  asserting Select All reproduces the document counts exactly.

The wider `N of Total` label reservation applies **only while a selection is
live**. Reserving it always cost ~230 px of status bar at rest, pushing the
smallest usable window from 928 px to 1159 px with every counter on — enough to
clip the keyboard-layout label on a half-screen window.

### Performance work (`f8e541b`, `b3c0bad`, `8591fd7`)

A status refresh on a 730 KB mixed Tamil/English document went **126 ms → 64 ms**,
and is free when the text has not changed. Three parts:

- The count cache was holding the document's full token list (~6.7 MB) and
  reclassifying it on every repaint (41 ms). It now caches finished values only.
- `_is_word_char` asked Unicode for a category once per *character*; now once per
  *distinct* character. Verified identical over 6,024 cases including Tamil
  combining marks.
- Word-script classification is memoised, **capped at 4 MB**. On reaching the cap
  it stops inserting but keeps serving what it holds ("freeze"), which measured
  faster than clearing and refilling. Bounded by entry count as well as bytes,
  because the byte counter is a non-atomic `+=` and would silently stop binding
  if counting ever moved off the main thread.

**Two optimisations were measured and rejected — do not retry them casually:**

- A **regex tokeniser** is 4.2× faster but Python's `\w` excludes Tamil vowel
  signs (category `Mc`/`Mn`), so `இது` tokenises as `இத` and `தமிழ்` as
  `தம` + `ழ`. It would inflate Tamil word counts in a Tamil-first editor.
- A **`re.finditer` sentence counter** looked good at 8.7 → 4.0 ms until diffed
  against the current one over 3,015 cases: **2,678 mismatched**.

### Direct downloads moved to `dist-latest` (`6426da4`, `b35a8a7`)

Stable installs now go through the stores — Microsoft Store live, Mac App Store
pending. GitHub Releases became the version history rather than a download
channel, and the website, `README.md` and `ADVANCED.md` point at the two
`dist-latest` artifacts, which every build republishes.

**The macOS direct download is now unsigned.** It previously linked the signed,
notarized `v2026.077` build and promised "no right-click-open, no Gatekeeper
prompt". The install steps now cover the one-time **right-click → Open**. Signed
builds are no longer offered as a direct download; the acknowledgement for the
contributed Apple Developer signature stays, reworded to past tense.

`release-assets-check.yml` was verifying Release assets that no longer back any
download button. It now HEADs the two `dist-latest` URLs, so a renamed branch or
a silently failed publish is caught instead of surfacing as a user-facing 404.

The website's "What's new" card claimed every build is posted as a tagged
release. Both halves stopped being true; it now points at `CHANGELOG.md`, which
is the live record.

---

## What is still open

1. **`packaging/msix_identity.json` is still `REPLACE_ME`** on all three Partner
   Center identity fields, *even though the Store listing is live*. `build_msix.ps1`
   refuses to run in that state, so **the MSIX is not currently reproducible from
   a clean clone**. The values are not secret — they ship inside every installed
   copy — and come from Partner Center → Product identity. This supersedes the
   2026-08-04 note below.
2. **Apple may object a second time.** The rejection was over update-checking,
   now removed. But Apple has also been known to object to App Store builds that
   point users at an outside download of the same app — which is what
   **Help → Neight on GitHub** does. **Agreed fallback: drop that menu item.**
   Nothing depends on it, and the About dialog already links to the GitHub
   README. Do **not** re-add any form of update *checking* as a fix.
3. **The bundle ID change breaks settings migration, and this is recorded
   nowhere else.** macOS treats a changed `CFBundleIdentifier` as a different
   app, so users moving from a `com.venkatarangan.neight` build to a
   `com.murasu.neight` one will **not** have their settings carried over — the
   Application Support path differs. This needs a callout in the release notes
   when the Mac App Store build ships.
4. **Issues #1 and #4 look resolved but are open.** #4 (mac download 404) — links
   verified 200. #1 (SmartScreen) — addressed by the Store listing.
5. **No session note exists for 2026-08-11.** From the commits, that session
   pointed the website's Windows CTA at the Microsoft Store (`2e237e3`) and
   changed the macOS bundle identifier to `com.murasu.neight` (`a2ff573`) for the
   well-wisher's App Store Connect account. Treat that as a summary of the
   commits, not a record of the session.

---

## What to avoid

**Never call `_apply_solveli_preset()` or `_apply_engineer_preset()` as part of
verification.** They persist to the real settings file. In this session a
verification script applied Writer Mode against the installed app and silently
overwrote the maintainer's font, line spacing, margins and counter visibility.
It surfaced only as a confusing `test_cursor_layout` failure —
`status bar line for block 0 reads ''` — on code that was fine.

More generally, **constructing a `Notepad` persists preferences as a side effect
of ordinary operation.** `tests/_harness.py` now stubs
`SettingsManager._determine_active_path` for every harness-based test
(`f33ca7f`), which also fixed a pre-existing problem: `test_cursor_layout` had
been running against whatever settings the previous run left behind, and went
from 539 checks to **798** once isolated. Ad-hoc scripts are **not** covered —
stub it explicitly in each one:

```python
store = pathlib.Path(tempfile.mkdtemp()) / "settings.json"
neight.SettingsManager._determine_active_path = lambda self: store
```

Recovery note, if it happens anyway: settings merge at key level, so *deleting*
a polluted key is a better repair than writing a guessed default — a still-running
window re-seeds it from its own in-memory original on next save. That is how the
maintainer's real font and spacing came back intact.

---

## Superseded

[`2026-08-04-msix-store-packaging-pending-verification.md`](2026-08-04-msix-store-packaging-pending-verification.md)
opens with the MSIX work "blocked … waiting on Microsoft's identity
verification". **That is resolved** — the Store listing is live at
`apps.microsoft.com/detail/9pj70ndp41lv`. Its step-by-step account of the MSIX
pipeline is still accurate and worth reading; only the blocked status has
changed. Per the convention in [`README.md`](README.md), that note is left frozen
rather than edited.

## Where to look for current state

| For | Read |
|---|---|
| What changed in each build | [`../CHANGELOG.md`](../CHANGELOG.md) |
| How to build, release, and the `dist-latest` model | [`../DEVELOPER.md`](../DEVELOPER.md) |
| What the regression suite guards | [`../tests/README.md`](../tests/README.md) |
| Open Qt-level bugs and validation runs | [`../knownbugs/`](../knownbugs/) |
