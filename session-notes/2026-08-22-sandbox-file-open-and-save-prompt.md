# 2026-08-22 — The Mac App Store build could not open files; fixed with security-scoped bookmarks

**State at close:** `main` @ the commit carrying this note, working tree clean,
`VERSION` = `2026.082`, and `dist-latest` already serving a 2026.082 macOS
build. **That published build is the one thing here that is not finished** — it
was built with a Homebrew Python and therefore honestly declares it needs
macOS 26. See the runbook below, which is why this session ends where it does.

Date: 2026-08-22
Context: continues [`2026-08-21`](2026-08-21-windows-catchup-and-clean-rebuild.md).
Started from a bug report — File > Open failing in the Store build — and ended
with the fix committed and a build that needs redoing on a different
interpreter.

---

## Runbook: rebuild on a python.org Python

This is the reason the session stopped here. Everything below the runbook is the
record of what changed and why; this part is the work still to do.

**Why.** 2026.082 as published can only run on macOS 26. Nothing in Neight or in
Qt requires that — all 58 binaries forcing the floor are CPython itself:

```
26.0   58 binaries   <- 52 in lib-dynload, 5 support dylibs, 1 Python.framework
15.0    9 binaries   <- PySide6's own bindings (QtCore/QtGui/QtWidgets, libpyside6)
13.0   39 binaries   <- Qt frameworks
11.0    1 binary
```

Homebrew compiles Python for whatever macOS is running it. python.org's
installer targets macOS 11. Swapping the interpreter drops the floor from 26.0
to **15.0** — the limit PySide6 6.11 sets — with no source change. Apple Silicon
only either way: `target_arch='arm64'` in the spec, and `buildme_mac_app.sh`
refuses to run on an Intel host. python.org ships a universal2 build; PyInstaller
thins it to arm64, which the 2026.082 build already proved works.

**Steps.**

1. Install python.org Python (needs `sudo`, so run it yourself):

   ```bash
   curl -LO https://www.python.org/ftp/python/3.14.7/python-3.14.7-macos11.pkg
   sudo installer -pkg python-3.14.7-macos11.pkg -target /
   ```

   Confirm it landed and check its floor — this number is the whole point:

   ```bash
   /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -VV
   otool -l /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
     | awk '/LC_BUILD_VERSION/{f=1} f&&/minos/{print;exit}'
   ```

   Expect `minos 11.0` or lower. If it says 26.0, the wrong interpreter is on
   `PATH` and the rebuild will achieve nothing.

2. Clone, and build the clean environment **explicitly against that
   interpreter** — `python3 -m venv` alone will pick up whatever is first on
   `PATH`:

   ```bash
   git clone https://github.com/venkatarangan/neight.git
   cd neight
   /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m venv .venv-build
   .venv-build/bin/python -m pip install --upgrade pip
   .venv-build/bin/python -m pip install -r requirements.txt -r requirements-build.txt
   ```

3. Run the suite before building. Same Python minor, different build of CPython
   — this is the check on that:

   ```bash
   for t in tests/test_*.py; do QT_QPA_PLATFORM=offscreen .venv-build/bin/python "$t" || break; done
   ```

4. Build:

   ```bash
   PYTHON_BIN="$PWD/.venv-build/bin/python" ./buildme_mac_app.sh
   ```

   It bumps to **2026.083**, which is correct: 2026.082 is already published with
   a different floor, and reusing the number would make two different builds
   indistinguishable.

5. **Read the floor line the script prints.** It says both numbers:

   ```
   Declared: 15.0   Actually required by the binaries: <N>
   ```

   Success is `15.0` on both, with no WARNING block. If it still warns, the
   interpreter from step 1 was not the one used in step 2.

6. Add a `2026.083` entry to `CHANGELOG.md` — one **[macOS]** line, that the
   published build now runs on macOS 15 and later rather than 26 — and commit
   the version bump. `buildme_mac_app.sh` leaves the tree dirty by design.

**Note:** every run of `buildme_mac_app.sh` force-pushes to `dist-latest`, which
*is* the public download. Running it replaces what people download, immediately.

## Then, and separately

**Send [`packaging/Neight.entitlements`](../packaging/Neight.entitlements) to
whoever signs the Store build**, and have them sign with
`codesign --entitlements`. The file-open fix in this session **does nothing
without it** — the new `com.apple.security.files.bookmarks.app-scope` key is what
makes `NSURL.bookmarkDataWithOptions:` return anything but nil.
[`packaging/MAC-APP-STORE-SIGNING.md`](../packaging/MAC-APP-STORE-SIGNING.md)
has the procedure and the outstanding asks, including the one worth most: a
locally signed test build, so a fix can be tested in minutes instead of a review
cycle.

---

## The bug: File > Open failed everywhere, for everyone, on the Store build

Reported as a OneDrive problem. It was not. By the end it was failing for files
on the Desktop, in Downloads, in Dropbox and in OneDrive, on at least two Macs,
with `PermissionError: [Errno 1] Operation not permitted`.

### What was ruled out, with evidence

- **The Open panel is genuinely native.** `log stream` showed
  `com.apple.appkit.xpc.openAndSavePanelService` running with
  `responsible=com.murasu.neight`. Qt's non-native dialog was never in play —
  the only `DontUseNativeDialog` in the codebase is on a `QFontDialog`.
- **No path rewriting exists** between the dialog returning and the read.
- **The shipped entitlements were correct as far as they went.**
  `codesign -d --entitlements :-` on `/Applications/Neight.app` showed
  `app-sandbox` + `files.user-selected.read-write`, which is what `NSOpenPanel`
  needs. The `_MASReceipt/receipt` and the `Apple Mac OS Application Signing`
  authority confirmed it was the real Store build.
- **TCC was never in the loop.** The denial was a plain App Sandbox
  `deny(1) file-read-data`.

### What it actually was

An `fs_usage` trace from a second machine settled it. Within 6 ms, on one
thread, for one path:

```
open  (RW_____________)  /Users/.../sample.txt   SUCCESS      <- CoreFoundation
close
        writes SecurityScopedBookmarks.plist                  <- AppKit
open  (RW_____________)  same                    SUCCESS
        writes SecurityScopedBookmarks.plist
stat64                   same                    SUCCESS      <- Path.stat()
open  [ 1] (R_________X___) same                 EPERM        <- CPython open()
```

The grant exists while AppKit does its own bookkeeping and is gone by the time
Python reads the bytes. `stat()` still succeeds in that window because the
sandbox treats `file-read-metadata` and `file-read-data` as separate
permissions — which is exactly why the failure looked like a bad path rather
than a lost permission, and why it took this long to find.

**A note on the handover documents.** Two claims that were passed along turned
out to be wrong, and both sent the investigation sideways for a while. Neither
document is in this repository -- they lived in gitignored scratch space -- so
they are summarised here rather than linked:

- The **OneDrive handover note** recorded "no sandbox deny
  line for Neight's own file access at all" and built a TCC hypothesis on that
  absence. Re-running the same command produced the deny line immediately. Its
  `log stream` predicate also used `CONTAINS "Neight"`, which is case-sensitive
  and misses `com.murasu.neight`; use `CONTAINS[c]`.
- The **signer-side trace analysis** correctly read the trace but then inferred an
  unbalanced `stopAccessingSecurityScopedResource()` in Neight, and recommended
  removing it. **There was no such call.** Neight had no bookmark code, no
  pyobjc, and `libqcocoa.dylib` contains no security-scoped symbols at all —
  the bookmark writes in the trace are AppKit's own. All three of that
  document's recommendations targeted code that does not exist.

## The fix

`neight.py` gained a macOS sandbox layer, written with `ctypes` against
Foundation rather than pyobjc — matching what the Carbon and Launch Services
helpers above it already do, and keeping pyobjc out of `requirements.txt` and
out of the bundle.

- `remember_sandbox_access(path)` mints a **security-scoped bookmark** the
  instant the Open panel returns, **before anything else in the app runs**.
  `open_file()` calls it ahead of `_post_file_dialog()`, which crosses into
  Carbon to resync the keyboard layout — nothing now runs in that gap.
- `sandbox_access(path)` is a context manager that redeems the bookmark around
  every read and write. `_open_file_path`, `_write_to_path` and the autosave
  worker all run inside one.
- It yields the **resolved** path, not the path as typed. The grant attaches to
  macOS's canonical URL, which for a FileProvider-backed OneDrive or Dropbox
  file is somewhere else.
- `stopAccessingSecurityScopedResource` is called **only** when the matching
  start returned YES. Apple documents the unbalanced call as undefined
  behaviour and it tears down the grant.
- Bookmarks persist to
  `~/Library/Application Support/Neight/sandbox-bookmarks.json` (the container's
  copy, inside the sandbox), LRU-capped at 200. This is what makes **Reopen last
  file on launch** and autosave-to-a-previously-opened-file work at all.
- Finder's **Open With** hand-off is recorded the same way, in
  `NeightApplication.event()`, before any prompt can intervene.

Everything degrades to a plain `open()`: off macOS, outside the sandbox, or on
any failure of the bridge, the behaviour is exactly what it was before.

**This needs `com.apple.security.files.bookmarks.app-scope`.** Without it
`bookmarkDataWithOptions:` returns nil and none of the above does anything.

## `packaging/Neight.entitlements` now exists

It did not before. The signing and submission step runs on another machine, so
what Neight was actually permitted to do could not be read from this repository
at all — which is why the permission bug could not be attributed for so long.

It holds `app-sandbox`, `files.user-selected.read-write`, and both bookmark
entitlements. It deliberately holds **no** `temporary-exception.files.*`: a
blanket home-directory exception does make the symptom go away, because the read
stops needing a scoped grant, but it asks App Review for standing access to the
user's home directory to run a text editor.

Two traps found the hard way:

- **`entitlements_file` in the spec must stay `None`.** PyInstaller applies it
  whether or not `codesign_identity` is set, so naming it there stamps
  `app-sandbox` onto the *direct-download* build, which has no provisioning
  profile to make a sandbox survivable.
- **A double hyphen inside an XML comment breaks it.** `plutil -lint` accepts
  the file; `codesign` reports only `AMFIUnserializeXML: syntax error near line
  N`. This is the same mistake as `a36b9a6` in the MSIX manifest. The
  entitlements file is now comment-free, and `buildme_mac_app.sh` validates it
  with both `plutil` and `xmllint` before doing any work.

## The bundle only runs on macOS 26, and now says so

2026.081 declared `LSMinimumSystemVersion = 12.0` while containing binaries built
for macOS 26. On anything older it would install and then fail to launch.

The cause is the build interpreter. Homebrew's Python is compiled for whatever
macOS is running it:

```
$ otool -l /opt/homebrew/.../python3.14 | grep minos
    minos 26.0
```

PySide6 6.11's own bindings (`QtCore.abi3.so`, `QtWidgets.abi3.so`,
`libpyside6`) are built for **15.0**, so 15.0 is the lowest reachable floor
whatever else changes. The spec now declares 15.0 as the intent, and
`buildme_mac_app.sh` measures every Mach-O in the finished bundle and raises the
plist to the truth, loudly, when the toolchain needs more. This build was raised
to **26.0**.

**To actually ship a lower floor, build with a python.org Python** — their
installer builds target an old deployment target. Nothing in the code needs to
change. The runbook at the top of this note is that rebuild, step by step.

## The second fix: no more "save changes?" on an untouched document

Launching Neight and going straight to File > Open asked whether to save the
empty document it had just opened with. `_maybe_save_changes()` was reading the
flag correctly; the flag was wrong. Applying saved preferences at startup calls
`doc.setDocumentMargin()` (via `CodeEditor.setFont` → `_apply_viewport_margins`)
and restyles blocks, and Qt counts each as a content change.

Cleared at the end of `Notepad.__init__`, after any initial file load — a file
load clears the flag itself, so this only settles what setup left behind.
`CodeEditor.__init__` also clears it, since installing the spacing-aware
document layout dirties a brand-new editor.

Separately, `_maybe_save_changes()` now skips the prompt for an **untitled**
document with no text, whatever the flag says: the only save on offer would
write an empty file. A document with a path is untouched by this — emptying a
file is a real edit.

`tests/test_unsaved_prompt.py` guards both, plus the inertness of the sandbox
helpers off-sandbox. It types through a `QTextCursor`: `setPlainText()` resets
the undo stack and clears the modified flag, so a test written with it would
pass against a completely broken gate. Registered in
`.github/workflows/checks.yml` and `tests/README.md`.

## What was deliberately not changed

- **`argv_emulation=True`** in the spec. It is redundant — `NeightApplication`
  already handles `QFileOpenEvent` including the pre-startup buffer — and it is
  a plausible cause of the separate "Open With sometimes never arrives" symptom
  seen at one point. Turning it off is an untested behaviour change that has
  nothing to do with the permission bug. Left alone on purpose.
- **A pyobjc-based bookmark helper** was drafted and not used. It needed pyobjc
  as a new dependency, and it solved cross-launch persistence rather than the
  immediate-read failure that was actually happening. The ctypes layer covers
  both without the dependency.
- **`release_macos.sh` was not run.** The GitHub release is the version
  history, not a download channel, and 2026.082 is superseded by the rebuild in
  the runbook above before it is worth tagging anything.

## Verification

- All six test scripts pass under `QT_QPA_PLATFORM=offscreen`, run against the
  clean `.venv-build` environment as well as the dev one.
- The built bundle is `Mach-O thin (arm64)`, ad-hoc signed, **carries no
  entitlements** (correct for the direct download), and declares 26.0.
- No binary in the bundle links against `/opt/homebrew` — the startup sandbox
  deny seen on `/opt/homebrew/Cellar/openssl@3/...` in 2026.081 is not
  reproducible here.
- `dist/Neight.app/Contents/MacOS/Neight` starts and stays up.

**Not verified, and cannot be from here:** the actual fix. It only does anything
inside a sandboxed, entitled, Store-signed build. Confirming it needs either a
locally signed test build using the real entitlements, or a submission. Ask the
signer for the former — [`packaging/MAC-APP-STORE-SIGNING.md`](../packaging/MAC-APP-STORE-SIGNING.md)
covers it — because
otherwise every iteration costs a review cycle.
