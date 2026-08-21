# 2026-08-21 — Windows caught up to 2026.081, and the download shrank by 26%

**State at close:** `main` @ `5f7a8ec`, working tree clean, `VERSION` =
`2026.081` — deliberately *unchanged*, see below. Windows and macOS now serve
the same version from `dist-latest`. `dist\Neight.msix` is built at
`2026.81.0.0` and **waiting to be uploaded to Partner Center** — the one task
this session did not finish.

Date: 2026-08-21
Context: a short Windows session picking up
[`2026-08-20`](2026-08-20-store-distribution-and-status-bar-work.md), which
closed asking for exactly this. Three commits, `3323e01` to `5f7a8ec`.

---

## Do this first

**Upload `dist\Neight.msix` to Partner Center** → Neight → Packages. It is built,
verified and sitting in `dist\`. Nothing else blocks it. Check first that no
package at or above **2026.81.0.0** is already there — the live listing was
submitted at 2026.79.0.0, and MSIX versions must strictly increase.

Do not sign it locally. Microsoft re-signs on publish.

---

## The repository had diverged, and the interesting part was the local side

This clone was 2 commits ahead and 12 behind. The 12 behind were the two Mac
sessions and were straightforward to take. The 2 ahead were not:

- `8c7f59c` "Bump version to 2026.079" — **dropped**, superseded by 2026.081.
- `27841fa` "Fill in MSIX Store identity values from Partner Center" — **kept**,
  cherry-picked onto `origin/main` as `999ae5f`.

That second commit is the whole story behind open item #1 in the 2026-08-20
note. That note recorded `packaging/msix_identity.json` as still `REPLACE_ME`
and asked for the values to be fetched from Partner Center again. **They were
never missing.** They had been filled in on 2026-08-10 on this machine and
simply never pushed. The Mac session could not have known — from `origin/main`
the file genuinely did read `REPLACE_ME`.

Worth generalising: a session note describes what the *remote* looked like.
When a machine has unpushed work, the note will confidently describe something
as missing that exists locally. Check `git log origin/main..main` before acting
on an open item.

**Open item #1 from 2026-08-20 is resolved.** `build_msix.ps1` runs from a clean
clone again.

## The Windows download was stale *and* bloated — both now fixed

The `Neight.exe` on `dist-latest` was byte-identical to the local 2026-08-10
build (both hashed to `3dc3bdc4…`). Since 2026-08-20 the website and `README.md`
link that file **directly**, so every Windows visitor for three weeks got a
2026.079 binary: no selection counts, no perf work, and — the part that actually
mattered for the App Store — the update checker still in it.

Rebuilt at 2026.081. But the size question turned out to be the more useful
finding.

### 68.2 MB → 50.4 MB, and nothing was misconfigured

The 2026-08-20 note attributed the bloat to "development-environment bloat" and
expected a clean build around 57 MB. Both halves need correcting:

- The clean build is **50.4 MB** (52,836,543 bytes), not ~57 MB. The 57 MB
  figure in `CHANGELOG` 2026.076 is stale — the app has changed since.
- The cause is not a polluted or unusual environment. `.venv` held exactly
  `requirements.txt` + `requirements-dev.txt`, which is what `DEVELOPER.md`
  tells you to install for development. **`pillow` and `python-pptx` are
  declared dev dependencies**, and `python-pptx` pulls `lxml` and `xlsxwriter`
  behind it. PyInstaller's hooks find all four and package them, though Neight
  imports none of them.

So this is not a mistake anyone made once — it is the default outcome of
building in the environment the docs tell you to create. It will recur on any
machine unless the build step is deliberately separated.

`DEVELOPER.md` previously warned against this in prose for Windows while giving
the explicit clean-environment commands only for macOS. It now gives them for
Windows too, with the measured cost stated.

The MSIX inherits the fix: **67.9 MB → 50.1 MB**.

### `buildme.bat --no-bump`

`buildme.bat` bumps `VERSION` as its first step, which would have made this
rebuild 2026.082 against macOS's 2026.081. Both artifacts sit side by side on
`dist-latest` and are linked from the same page, so a user comparing the two
downloads would see different version numbers for what is the same source.

`--no-bump` skips the bump and builds the committed version. It also leaves
`neight.py` unmodified, so the tree stays clean and `build_msix.ps1` — which
refuses to run dirty — follows directly with no commit in between. Both code
paths echo the version actually being built.

Use it for catch-up builds only. An ordinary Windows build that introduces
changes should still bump.

## The test suite passes 954 checks on Windows, not 934

The 2026-08-20 note says to expect **934**. On Windows it is **954**, 0 failed:

| Script | Checks |
|---|---|
| `test_startup_settings.py` | 3 |
| `test_text_integrity.py` | 67 |
| `test_cursor_layout.py` | 818 |
| `test_input_gestures.py` | 25 |
| `test_selection_counts.py` | 41 |

The difference is `test_cursor_layout.py`, which is font- and platform-sensitive
and enumerates more cases here. Not a regression — but do not treat 934 as the
cross-platform figure, or a Windows run will look wrong when it is fine.

`f33ca7f`'s settings stub was verified working: the run reported
`startup made 1 write(s)` against the temporary store, and the maintainer's real
`settings.json` was untouched.

## Issues #1 and #4 are closed

Both were resolved by the 2026-08-20 work and had simply not been closed.
**#4** (mac download 404) — links now come from `dist-latest`, verified 200, and
the daily `Download links check` workflow guards them. **#1** (SmartScreen) —
the Store listing is live and Microsoft re-signs, so the recommended install
path no longer triggers it; the direct `.exe` still does, by design, and the
README now scopes those instructions to that download only.

---

## What is still open

1. **The MSIX upload**, above.
2. **Apple may object a second time**, to **Help → Neight on GitHub** pointing
   users at an outside download of the same app. Carried forward unchanged from
   2026-08-20. **Agreed fallback: drop that menu item.** Nothing depends on it
   and the About dialog already links to the GitHub README. Do **not** re-add
   update *checking* as a fix.
3. **The bundle ID change breaks settings migration.** macOS treats a changed
   `CFBundleIdentifier` as a different app, so anyone moving from a
   `com.venkatarangan.neight` build to a `com.murasu.neight` one loses their
   settings — the Application Support path differs. Still needs a callout in the
   release notes when the Mac App Store build ships. Carried forward from
   2026-08-20 and **still recorded nowhere else**.
4. **`CHANGELOG` 2026.076's 57 MB figure is stale** now that a clean build is
   50.4 MB. Left alone deliberately — it was accurate when written, and the
   changelog is a historical record.

## What to avoid

Everything in [`CLAUDE.md`](../CLAUDE.md) still applies, in particular never
calling `_apply_solveli_preset()` or `_apply_engineer_preset()` during
verification.

One addition from this session: **`buildme.bat` force-pushes to `dist-latest` as
its last step**, so *any* local build immediately becomes the public download on
both platforms' links. There is no staging step and no confirmation prompt. Do
not run `buildme.bat` to "just try something" — the publish is not optional and
not reversible except by building again. The macOS artifact is untouched by a
Windows build (verified: `Neight-mac-arm64-unsigned.app.zip` still at blob
`b97f019` after this session's force-push), but the Windows one is replaced
outright.

## Verified this session

- 954 checks, 0 failed, before building.
- `dist\Neight.exe` = 52,836,543 bytes; the blob on `dist-latest` matches it
  exactly (`a1a6805…`), and is no longer the stale `3dc3bdc4…`.
- Both `dist-latest` download URLs return HTTP 200; the mac artifact survived
  the force-push.
- The built `.exe` launches and stays up.
- No `_UpdateCheckWorker`, `Check for Updates`, `update_check_on_launch` or
  `QThread` remains in `neight.py`; `Help → Neight on GitHub` is present.
- `AppxManifest.xml` carries the real identity, `Version="2026.81.0.0"`.

## Where to look for current state

| For | Read |
|---|---|
| Conventions that are easy to get wrong | [`../CLAUDE.md`](../CLAUDE.md) |
| What changed in each build | [`../CHANGELOG.md`](../CHANGELOG.md) |
| How to build, release, and the `dist-latest` model | [`../DEVELOPER.md`](../DEVELOPER.md) |
| What the regression suite guards | [`../tests/README.md`](../tests/README.md) |
| Open Qt-level bugs and validation runs | [`../knownbugs/`](../knownbugs/) |
