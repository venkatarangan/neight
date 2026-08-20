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
  pending approval.
- **Direct downloads come from the `dist-latest` branch**, which every build
  republishes by amending its single commit and force-pushing. It is what the
  website and `README.md` link to, so **any local build immediately becomes the
  public download**. Both artifacts there are unsigned.
- **GitHub Releases is the version history**, not a download channel.
- `buildme_mac_app.sh` and `buildme.bat` increment `VERSION` as their first step
  and publish to `dist-latest` as their last. Expect a dirty tree after a build.

`DEVELOPER.md` has the full build and release detail.

## Committing

- `CHANGELOG.md` entries are platform-tagged **[Windows]** / **[macOS]** /
  **[Both]** and say *why*, not just what.
- Session notes are point-in-time records. A later session **supersedes** an
  earlier one by saying what changed and linking back — it does not edit the
  older note.
- Pre-commit hooks check BOMs, line endings, and Tamil spelling.
