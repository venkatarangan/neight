# 2026-08-23 (evening) — Windows handoff: today's fix is macOS-only, verified

**State at close:** `main` @ `9cefd8d`, pushed to `origin/main`, working tree
clean. `VERSION` = `2026.086`. `origin/dist-latest` was force-pushed today at
19:17:48 IST with a freshly rebuilt macOS artifact — **the Windows `Neight.exe`
in that same push was carried forward unchanged**, still whatever build was
last there (see "Open item" below).

Date: 2026-08-23
Context: continues
[`2026-08-23-sandbox-save-sweep.md`](2026-08-23-sandbox-save-sweep.md), which
fixed the Mac App Store build's inability to save files and swept every
sandbox-adjacent file pathway. That work — and this note — was all done on
macOS and had never reached GitHub until today; this note exists because the
next session picks it up on Windows, per this repository's own convention
(`DEVELOPER.md`: *"if you are picking this repository up on Windows for the
first time in a while, read its opening section before running `git pull`"*).

---

## The short version

**Nothing in today's changes touches Windows behaviour.** Every fix was scoped
to `sys.platform == "darwin"` and, more specifically, to the sandboxed subset of
that (`_macos_is_sandboxed()`). This was verified directly, not assumed: a
line-by-line diff of every `sys.platform == "win32"` (and `!= "win32"`)
branch in `neight.py` between `HEAD~1` and `HEAD` shows **zero textual
changes** — every Windows branch shifted by line number only, from insertions
elsewhere in the file. The one function both platforms share,
`_view_recovery_folder`, has an untouched `elif sys.platform == "win32":`
branch; only its macOS branch changed (from `subprocess.run(["open", ...])` to
`QDesktopServices.openUrl`, because the sandbox forbids the former).

So there is nothing to *fix* on Windows here. The ask was to double-check, and
that is what the section below is for.

## What to verify on Windows

1. **`git pull`** on `main` — you should land on `9cefd8d`, `VERSION` =
   `2026.086`, working tree clean.

2. **Run the regression suite.** Same commands as always
   (`tests/README.md`), now including the new one:
   ```powershell
   $env:QT_QPA_PLATFORM = "offscreen"
   python tests/test_startup_settings.py
   python tests/test_text_integrity.py
   python tests/test_cursor_layout.py
   python tests/test_input_gestures.py
   python tests/test_selection_counts.py
   python tests/test_unsaved_prompt.py
   python tests/test_sandbox_qt_io.py
   ```
   `test_sandbox_qt_io.py` is new. It is **not** gated to macOS — it forces
   `_macos_is_sandboxed()` to `True` and exercises the Qt (`QFile`) read/write
   helpers directly regardless of host OS, on the theory that `QFile` behaves
   the same everywhere and the sandbox-specific part is only the *decision* to
   use it. It should pass on Windows exactly as it does on macOS; if it does
   not, that is new information this session did not have.

3. **GitHub Actions already ran both matrix legs** (`windows-latest` and
   `macos-latest`) on the push to `main` — check the run for `9cefd8d` at
   <https://github.com/venkatarangan/neight/actions>. A green `windows-latest`
   leg is the more authoritative version of step 2, on a machine this session
   never touched.

4. **Nothing about Windows file associations, MSIX packaging, or the registry
   repair logic (`_win_repair_orphaned_associations`) was read, let alone
   changed.** No action needed there; mentioned only so it's clear this was
   checked, not skipped.

## Open item: `dist-latest`'s Windows artifact is stale, not broken

Today's push to `dist-latest` (`58f6c97`, same timestamp as the source push)
carried the **existing** `dist/Neight.exe` forward untouched — the macOS build
script only rebuilds the macOS side. That `.exe` predates today's `VERSION`
bump to `2026.086` and reports whatever version it was last built at (the
[2026-08-21 session](2026-08-21-windows-catchup-and-clean-rebuild.md) built
`2026.081`; there may have been later Windows builds since — check
`Neight.exe`'s own **Help → Debug Info → About** on a real run if unsure).

This is **not a bug** — nothing in `Neight.exe` needs to change, since none of
today's fix touches Windows code paths. It is only a version-string mismatch
between the two files sitting side by side in `dist-latest`. If you want the
two artifacts to report the same version, rebuild and republish from Windows:

```powershell
.\buildme.bat --no-bump
```

`--no-bump` is the right flag here — `VERSION` is already `2026.086` from the
macOS build, and a plain `buildme.bat` would bump it again past what macOS set,
per `CLAUDE.md`. This is optional and cosmetic; do it only if a mismatched
version string between the two `dist-latest` artifacts would confuse whoever
downloads the Windows build next.

## Also unrelated to Windows, for context only

`packaging/HANDOVER-MAC-APP-STORE.md` was rewritten for the save fix and needs
a real SHA-256 filled in before it goes to Muthu Nedumaran (the Mac App Store
signer) — that artifact and that step are macOS-only and untouched by anything
here.
