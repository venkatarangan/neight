# 2026-08-23 (later) — QSaveFile cannot work in the sandbox; the whole file sweep

**State at close:** `main` @ the commit carrying this note, `VERSION` still
`2026.084` — **the build has not been run yet**, so the next one is 2026.085.
Full suite green under `.venv` and `.venv-build`, offscreen. Like the fix
before it, this is **unverified in a signed build**; the decision was again to
submit rather than spend another diagnostic round trip.

Date: 2026-08-23
Context: supersedes [`2026-08-23-qt-file-engine-fix.md`](2026-08-23-qt-file-engine-fix.md)
of the same day. That note's diagnosis was right and its read path works — the
signer confirmed opening files now succeeds. Its **write** path did not, for a
reason that note could not have known without reading Qt's source.

---

## Why the first fix could open but not save

The signer reported back: files open, files do not save. The cause is in Qt,
not in Neight and not in the entitlements.

`_sandbox_write_text` used `QSaveFile`. From Qt 6.11.1's `qsavefile.cpp`,
`QSaveFile::open()` cannot succeed inside an App Sandbox:

```cpp
d->fileEngine.reset(new QTemporaryFileEngine(&d->finalFileName, ...));  // constructed DIRECTLY
if (!d->fileEngine->open(mode | QIODevice::Unbuffered)) {
    QFileDevice::FileError err = d->fileEngine->error();
#ifdef Q_OS_UNIX
    if (d->directWriteFallback && err == QFileDevice::OpenError && errno == EACCES) {
        if (openDirectly())        // openDirectly() DOES use QAbstractFileEngine::create()
            return true;
```

1. The temp file is a **sibling** of the target. The Powerbox grant covers the
   chosen *file*, not its *directory*, so creating it is denied. And
   `QTemporaryFileEngine` is constructed directly, bypassing
   `QAbstractFileEngine::create()` — so the security-scoped engine is never
   consulted and could not have redirected it anyway.
2. `setDirectWriteFallback(true)` *does* go through the engine, via
   `openDirectly()`. But Qt guards it on **`errno == EACCES`**, and macOS
   sandbox denials return **`EPERM`** — errno 1, the same value the signer's
   own log showed for Python's `open()`. The fallback never fires.

`QFile` has neither problem: `QFilePrivate::engine()` goes through
`QAbstractFileEngine::create(fileName)`, which iterates registered handlers.
That is exactly why the read path works.

**The fix:** sandboxed writes open the final path with
`QFile` + `WriteOnly|Truncate` — literally what `QSaveFile`'s own
`openDirectly()` would have done. A plain Python `open()` retry sits behind it
as a second chance for the Finder "Open With" case, whose grant is
process-wide and needs no bookmark.

**Accepted, and unavoidable:** the sandboxed save is **not atomic**. The
sandbox forbids write-temp-then-rename, so a crash mid-save can truncate the
file. `should_commit` is therefore consulted once, immediately before the
destructive open — after that there is nothing left to withdraw.
`_atomic_write_text` is untouched and still fsyncs before an atomic rename
everywhere else.

## The rest of the sweep

Every filesystem pathway was checked, not just the reported one.

**Already correct, left alone:** `settings.json` (`_determine_active_path`
returns Application Support on darwin *before* the `.write_test` probe can
touch the app bundle), the `QLockFile` beside it, the dated autosave log, and
the New Window `subprocess.Popen` (a sandboxed process may exec its own
bundle's binary).

**Fixed:**

- **Recovery copies and mode presets** wrote to `~/Documents/Neight`. Inside
  the sandbox that is the container's Documents — writes *succeeded*, which is
  why this never showed up as an error, but into a folder no user can find and
  that macOS deletes with the app. So the preset docstring's "survives app
  deletion" was false in the Store build. `_get_user_documents_dir` is now
  `_get_app_data_dir` and returns Application Support when sandboxed, adopting
  anything an earlier build left in the container's Documents. Dialogs show
  the resolved path. Off the sandbox nothing moved.
- **PDF export** works — `QPrinter` opens through `QFile`, so the grant does
  apply — but nothing checked, so a denied export showed a success dialog over
  a file that was never written. `_verify_pdf_written` now gates both.
- **`_view_recovery_folder`** shelled out to `/usr/bin/open`; a sandboxed
  process may not exec a binary outside its bundle. Now `QDesktopServices`
  (NSWorkspace), falling back to naming the path.
- **`_macos_set_default_handler`** returns False when sandboxed — writing the
  Launch Services handler database is forbidden — and the button is disabled
  with a note pointing at Finder's Get Info → Change All. Reading the current
  handler is still permitted, so the dialog still reports what it cannot
  change.
- **Panel start directory.** `default_directory` was seeded from
  `Path.home()`, the container root when sandboxed. Sandboxed it now comes
  from the user's real Documents, found via `pwd.getpwuid(os.getuid())` —
  the passwd database is not redirected, unlike `HOME`. A container path is
  also never persisted back into settings, including a stale one written by an
  earlier build. Windows, Linux and the direct download keep `Path.home()`.
- **`_open_file_path` passed a `Path()`-normalised string to Qt** while both
  write sites passed the raw one, contradicting its own comment. Qt keys its
  bookmark on the incoming fileName, so the read — the one that must match —
  was the inconsistent one. Now raw, for any absolute path.

## Tests

`tests/test_sandbox_qt_io.py` grew from 16 to 26 assertions: the background
autosave worker's sandbox branch (pumping the event loop, since the worker
reports through a queued signal), a raising `should_commit`, writing over a
directory, the `_get_app_data_dir` split, the panel start directory, and a
path-identity check that would catch any future normalisation creeping back
in. It redirects `Path.home()` first — `_get_app_data_dir` creates what it
returns and a test must not leave folders in the real home. Same rule as
`CLAUDE.md`'s settings warning, one level out.

## Still to do

1. Run `PYTHON_BIN="$PWD/.venv-build/bin/python" ./buildme_mac_app.sh` — bumps
   to 2026.085 and republishes `dist-latest`, the live public download.
2. Fill the real SHA-256 into `packaging/HANDOVER-MAC-APP-STORE.md`, which now
   carries an explicit `FILL IN AFTER THE BUILD` marker, and send it with the
   artifact and `Neight.entitlements`.
3. After a signed 2026.085 ships, update the "Store build is broken" warnings
   in `CLAUDE.md` and `packaging/MAC-APP-STORE-SIGNING.md`.

If a signed 2026.085 *still* cannot save, `NEIGHT_SANDBOX_DIAG=1` now names the
failing stage — open, write, flush or close — with Qt's own `errorString()`.
One log should place it exactly.
