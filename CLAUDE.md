# Working on Neight

Conventions that are easy to get wrong here. For *current* state, read the
newest file in [`session-notes/`](session-notes/) first — that is the handoff
record, written for someone starting cold on another machine.

## The shape of the project

Neight is a Qt (PySide6) text editor for writing in Tamil and English. Almost
all of it is one file, **`neight.py`, ~9,000 lines** — expect to grep for a
symbol rather than browse. There is no package structure and no framework.

## Constructing a `Notepad` writes to real user settings

This is the trap that has actually caused damage. `Notepad` persists preferences
as a side effect of ordinary operation, and the preset methods
(`_apply_solveli_preset`, `_apply_engineer_preset`) write font, spacing, margins
and status bar visibility straight to the user's real `settings.json`.

**Never call a `_apply_*_preset` method as part of verification** — it is a
persisted, user-visible change, not a read-only probe.

Before building a `Notepad` in any script, point settings somewhere disposable:

```python
store = pathlib.Path(tempfile.mkdtemp()) / "settings.json"
neight.SettingsManager._determine_active_path = lambda self: store
```

`tests/_harness.py` already does this for every harness-based test. Ad-hoc
scripts are not covered and must do it themselves.

If settings do get polluted: they merge at key level, so **deleting** the
affected keys is a better repair than writing guessed defaults — a still-running
window re-seeds them from its own in-memory originals on its next save.

## Tests are plain scripts, not pytest

Deliberately, so CI needs nothing beyond `requirements.txt`. Run them directly:

```bash
QT_QPA_PLATFORM=offscreen python3 tests/test_selection_counts.py
```

Each exits non-zero on failure and prints failures as GitHub Actions
annotations. `.github/workflows/checks.yml` runs them one by one — a new test
file must be registered there and in [`tests/README.md`](tests/README.md).
See that file for what each one guards.

## Tamil is the point, so verify text handling against Tamil

Optimisations that look safe on ASCII often are not:

- Python's `\w` **excludes Tamil vowel signs** (Unicode category `Mc`/`Mn`), so
  regex tokenising splits `இது` into `இத`.
- Qt returns paragraph breaks as `\n` from `toPlainText()` but **U+2029** from
  `selectedText()`. Use the existing `_get_selected_text` helper, which
  normalises.

When changing counting, tokenising or classification, diff the output against
the previous implementation over a mixed Tamil/English corpus before trusting a
speedup.

## Distribution

- **Stable installs go through the stores** — Microsoft Store now, Mac App Store
  pending approval. These are the *only* stable channels.
- **Direct downloads come from the `dist-latest` branch**, which every build
  republishes by amending its single commit and force-pushing. It is what the
  website and `README.md` link to, so **any local build immediately becomes the
  public download**. Both artifacts there are unsigned.
- **There are no GitHub Releases.** They were deleted once the stores took over;
  the version tags were kept. Do not reintroduce a release step — the two
  channels above are the whole distribution story, and `release_macos.sh` /
  `release_windows.ps1` were removed with the releases.
- `buildme_mac_app.sh` and `buildme.bat` increment `VERSION` as their first step
  and publish to `dist-latest` as their last. Expect a dirty tree after a build.
  `buildme.bat --no-bump` skips the increment, for a Windows build catching up
  to a version macOS already set — the tree then stays clean.
- **Build releases from an environment holding only `requirements.txt` and
  `requirements-build.txt`.** PyInstaller's hooks bundle any optional package
  they can import, even ones Neight never imports — `pillow` and `python-pptx`
  once cost 18 MB of dead weight in the `.exe`. Both are out of
  `requirements-dev.txt` now (`pillow` lives in `requirements-design.txt`), so
  the rule is a second line of defence rather than the only one. It still
  applies: the next optional package added will behave the same way.
- **macOS release builds need a python.org interpreter, not Homebrew's.** The
  interpreter sets the bundle's macOS floor; Homebrew's is compiled for whatever
  macOS is running it, which shipped a build only macOS 26 could run (2026.082).

`DEVELOPER.md` has the full build and distribution detail.

## Windows file associations come from the package, not the registry

`.txt`, `.md` and `.markdown` are declared in
`packaging/AppxManifest.xml.template`. That is the only mechanism the shell
honours for a packaged app, and it is what puts Neight in Explorer's **Open
With** menu on a Store install. The unpackaged `.exe` has no association at all.

Do not reintroduce registry writes to `HKCU\Software\Classes`. Neight used to do
this and it broke on the move to the Store: the writes do not survive, and the
open command would name a `WindowsApps` path containing the version number,
which disappears at the next update. `_win_repair_orphaned_associations()`
exists to clean up what that left behind.

**No application can make itself the default handler on Windows** — the
`UserChoice` value has been hash-protected since Windows 8. Appearing in Open
With is the most any app may do. Do not accept a "fix" that claims otherwise.

The behaviour only exists once the package is installed, so a source checkout
and a bare `Neight.exe` both exercise the *unpackaged* path and cannot catch a
broken manifest. See `tests/README.md` for the manual procedure.

## Committing

- `CHANGELOG.md` entries are platform-tagged **[Windows]** / **[macOS]** /
  **[Both]** and say *why*, not just what.
- Session notes are point-in-time records. A later session **supersedes** an
  earlier one by saying what changed and linking back — it does not edit the
  older note.
- Pre-commit hooks check BOMs, line endings, and Tamil spelling.
