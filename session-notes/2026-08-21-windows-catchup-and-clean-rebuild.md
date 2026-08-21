# 2026-08-21 — Windows caught up to 2026.081, the download shrank 26%, and file associations were fixed

**State at close:** `main` @ `a36b9a6`, working tree clean, `VERSION` =
`2026.081` — deliberately *unchanged*, see below. Windows and macOS now serve
the same version from `dist-latest`. `dist\Neight.msix` is built at
`2026.81.0.0`, verified against a real local install, and **waiting to be
uploaded to Partner Center** — the one task this session did not finish.

**A dev-registered copy of that package is deliberately left installed** on the
Windows machine so the maintainer can test it before uploading. See "The test
install left behind" for what it is and how to undo it.

Date: 2026-08-21
Context: a Windows session picking up
[`2026-08-20`](2026-08-20-store-distribution-and-status-bar-work.md), which
closed asking for the catch-up build. The file-association work came out of a
bug report raised during the session. Five commits, `3323e01` to `a36b9a6`.

---

## Do this first

**Upload `dist\Neight.msix` to Partner Center** → Neight → Packages. It is built,
verified and sitting in `dist\`. Nothing else blocks it. Check first that no
package at or above **2026.81.0.0** is already there — the live listing was
submitted at 2026.79.0.0, and MSIX versions must strictly increase.

Do not sign it locally. Microsoft re-signs on publish.

**Before uploading, be clear about what this package contains.** It is not the
same software as the macOS build published under 2026.081 — see "Two trees, one
version number" below. Uploading is still the right move; just do not read the
2026.081 changelog as describing both platforms.

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

## File associations were broken by the move to the Store

Reported during the session: opening `.txt` and `.md` with Neight had stopped
working on Windows. It had, and the cause was structural rather than a slip.

**Help → Debug Info** offered two checkboxes that registered Neight by writing
`HKCU\Software\Classes` directly. That is a legitimate mechanism for an ordinary
`.exe` and the wrong one for a packaged app. Three things were wrong at once:

1. **The MSIX manifest declared no file type associations at all.** For a
   packaged app the manifest is the only mechanism the shell honours, so the
   Store build could never appear as a handler no matter what the checkbox did.
2. **The registry state left behind was half-written.** `.txt\OpenWithProgids`
   named `Neight.txt`, but `Software\Classes\Neight.txt` — the ProgID holding
   the open command — did not exist. A dead entry in the Open With menu.
3. **A successful write could not have survived anyway.** Under MSIX
   `sys.executable` is
   `C:\Program Files\WindowsApps\LittleFeetServicesPvtLtd.neight_2026.79.0.0_x64__…\Neight.exe`.
   That path contains the version and disappears at the next Store update.

Microsoft's own Notepad registers as `AppX4ztfk9wxr86nxmzzq47px0nh0e58b8fw` with
a `DelegateExecute` handler — an `AppX<hash>` ProgID the platform generates
*from the manifest*. That is the shape a correct packaged registration takes,
and an app does not write it for itself.

### What was done

The manifest now declares `.txt`, `.md` and `.markdown`. The checkboxes are gone
on **all** Windows builds, replaced by text that explains where the association
comes from, plus the existing Default apps button and a link to Microsoft's
instructions. Opening Debug Info also repairs dangling entries — but only
dangling ones; a *complete* registration from an older direct `.exe` build still
works and was chosen deliberately, so it is left alone.

**This removes a capability from direct-download users.** The checkboxes were
the only thing that registered the unpackaged `.exe`, so it can no longer appear
in Open With at all. That was a deliberate call, not an oversight.

### Two traps worth remembering

**The app-model APIs are exported without a trailing `W`.** `GetCurrentPackageFullNameW`
does not exist; the name is `GetCurrentPackageFullName`. The first version of
`_win_appmodel_string` asked for the `W` form, got `AttributeError`, swallowed it
in the `except`, and would have made **every** build report itself as unpackaged —
leaving the entire Store branch permanently dead while looking like it worked.
The two functions also report absence differently: `GetCurrentPackageFullName`
answers `APPMODEL_ERROR_NO_PACKAGE` (15700), `GetCurrentApplicationUserModelId`
answers `APPMODEL_ERROR_NO_APPLICATION` (15703). Treating only 15700 as
"unpackaged" is a live trap.

**A double hyphen is illegal inside an XML comment.** The first manifest comment
contained one, and `makeappx` rejected the package with only "the package
manifest is not valid" — no line, no column. `build_msix.ps1` now parses the
staged manifest before packing so the next occurrence names the actual error.

### How it was verified

The manifest half is proven end-to-end. The package was registered locally
(Developer Mode) and all three extensions opened in the packaged app —
`assoc-test.txt`, `assoc-test.md` and `assoc-test.markdown` each appeared as a
window title. `tasklist /apps` confirmed every process carried package identity.
The generated ProgIDs are textbook: `ContractId = Windows.File`,
`PackageRelativeExecutable = Neight.exe`, `DesktopAppXActivateOptions = 0x20`
(the Desktop Bridge flag meaning "pass the file as a command-line argument"),
and the correct AUMID `LittleFeetServicesPvtLtd.neight_rs07675pfr2ay!Neight`.

**One thing is *not* verified: `_win_is_packaged()` returning `True` inside the
real package.** Several approaches failed —
`Invoke-CommandInDesktopPackage` runs an external `.exe` without granting it
package identity, and a probe added as a second `Application` in the manifest hit
schema and deployment errors that were not worth chasing further. What is known:
the export names are right, the unpackaged branch returns `""` correctly from
both sentinels, and the running packaged process demonstrably *has* identity, so
the API will return a value. What is unproven is the success-path parsing.

**If it is wrong, the damage is cosmetic**: Open With still works, because that
is manifest-driven and independent of this code. Debug Info would wrongly say
"direct download", and the Default apps button would open the generic page
instead of Neight's own entry. Worth one look at Debug Info on the installed
package before assuming it is fine.

## The test install left behind

`Get-AppxPackage LittleFeetServicesPvtLtd.neight` reports **2026.81.0.0**,
`SignatureKind: None`, installed from `C:\DevTemp\neight\dist\msix_staging` —
a dev registration, not a Store install. It replaced the Store copy that was
there (2026.79.0.0, `SignatureKind: Store`).

To go back to the Store build: uninstall from Settings → Apps, then reinstall
from [the listing](https://apps.microsoft.com/detail/9pj70ndp41lv).

Two things about a dev registration worth knowing:

- **It runs out of the build folder.** Rebuilding into `dist\msix_staging`
  changes the installed app underneath itself, and `Add-AppxPackage -Register`
  fails with `0x80073D02` while any instance is running. Close Neight first.
- **The app writes `settings.json` next to its own exe**, so running it puts one
  in the staging folder. That cannot leak into a shipped package —
  `build_msix.ps1` deletes and recreates the staging directory on every run
  (`build_msix.ps1:123-127`) — and the built `Neight.msix` was checked and
  contains only the six assets, `Neight.exe` and the manifest.

## Two trees, one version number

`VERSION` was held at 2026.081 for the catch-up build, when the source was
identical to what macOS shipped. It stayed at 2026.081 through the association
work, when it no longer was. That was raised and confirmed as a deliberate
choice, but it leaves a real discrepancy:

**The Windows 2026.081 build contains code that no macOS 2026.081 build has.**
The `CHANGELOG` entry for it says so explicitly and is tagged **[Windows]**, and
the Store package will carry `2026.81.0.0`. A future reader diffing a
user-reported version against source should know that 2026.081 does not identify
a single tree. Bumping is the better default for anything that changes code.

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
5. **`_win_is_packaged()` is unproven inside a real package**, as described
   above. One look at **Help → Debug Info** on the installed test package
   settles it: it should say the copy is installed from the **Microsoft Store**,
   not that it is a direct download.
6. **The Windows machine has a dev-registered package installed, not the Store
   build.** Reinstall from the Store listing once testing is done.
7. **Developer Mode was enabled on the Windows machine** to allow the local
   install. Turn it off in Settings → System → For developers if it is not
   wanted permanently.
8. **Windows file associations have no automated coverage**, and by their nature
   cannot have much — the behaviour only exists once the package is installed.
   `tests/README.md` now records the manual procedure.

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

- 954 checks, 0 failed — run before the catch-up build, and again after the
  association change.
- `dist\Neight.exe` = 52,840,995 bytes (50.4 MB); the blob on `dist-latest`
  matches it exactly (`790ac11…`) and is no longer the stale `3dc3bdc4…`.
- Both `dist-latest` download URLs return HTTP 200; the mac artifact is
  untouched at `b97f019…` after three Windows force-pushes.
- The built `.exe` launches and stays up.
- No `_UpdateCheckWorker`, `Check for Updates`, `update_check_on_launch` or
  `QThread` remains in `neight.py`; `Help → Neight on GitHub` is present.
- `AppxManifest.xml` carries the real identity, `Version="2026.81.0.0"`, and
  both `FileTypeAssociation` blocks.
- `Neight.msix` = 52,578,768 bytes (50.1 MB), containing only the six assets,
  `Neight.exe` and the manifest — no stray files.
- **The associations work end-to-end on a real install**: `.txt`, `.md` and
  `.markdown` each opened in the packaged Neight, every process carrying package
  identity.
- The orphan repair removed the three genuinely dangling entries on this machine
  and left a deliberately seeded *complete* registration untouched.
- Debug Info constructs with no checkboxes, the help link, and the correct
  unpackaged wording when run from source.
- macOS is untouched: no `darwin`, `_macos_`, `CFBundle` or `LSSet` line appears
  in the diff, `Neight.macos.spec` is unmodified, and CI's
  `Import and construct (macos-latest)` job passes.
- **A fresh `git clone` of `main` builds everything, verified by doing it.**
  Into an empty directory: `py -m venv .venv`, install
  `requirements.txt` + `requirements-build.txt`, then

  | Step | Result |
  |---|---|
  | Five test scripts | 954 passed, 0 failed |
  | `pyinstaller packaging\Neight.windows.spec` | `Neight.exe`, 52,840,351 bytes |
  | `build_msix.ps1` | `Neight.msix` at `2026.81.0.0`, 50.1 MB |

  The MSIX step is the one that mattered: it is exactly what the 2026-08-20 note
  recorded as impossible from a clean clone, and it now works because
  `msix_identity.json` carries the real Partner Center values.

  The `.exe` from a fresh clone is 644 bytes smaller than the published one and
  hashes differently. That is expected — PyInstaller embeds absolute paths and
  timestamps, so builds are not byte-reproducible. Matching to within 644 bytes
  is what confirms the same dependency set; do not chase an identical hash.

  Note the deliberate omission: this used `pyinstaller` directly rather than
  `buildme.bat`, because `buildme.bat` force-pushes to `dist-latest` as its last
  step and would have replaced the public download with a throwaway test build.

## Where to look for current state

| For | Read |
|---|---|
| Conventions that are easy to get wrong | [`../CLAUDE.md`](../CLAUDE.md) |
| What changed in each build | [`../CHANGELOG.md`](../CHANGELOG.md) |
| How to build, release, and the `dist-latest` model | [`../DEVELOPER.md`](../DEVELOPER.md) |
| What the regression suite guards | [`../tests/README.md`](../tests/README.md) |
| Open Qt-level bugs and validation runs | [`../knownbugs/`](../knownbugs/) |
