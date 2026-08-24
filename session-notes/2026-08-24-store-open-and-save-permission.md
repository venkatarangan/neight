# 2026-08-24 — Two sandbox holes the 2026.086 fix left open

**State at close:** `main` @ the commit carrying this note, `VERSION` =
`2026.086` (the next build bumps it), tree dirty only if a build has been run.
The two sandbox fixes are covered by `tests/test_sandbox_qt_io.py` and are
**unverified in a signed build** — as ever, nothing local is sandboxed. The
cross-instance document lock added later the same day (see the last section) is
covered by `tests/test_document_lock.py` and *is* verifiable locally, since it
is not sandbox-specific.

Date: 2026-08-24
Context: extends [`2026-08-23-qt-file-engine-fix.md`](2026-08-23-qt-file-engine-fix.md),
which established that Qt 6.11's security-scoped file engine owns the Powerbox
grant. Nothing in that note is superseded. Both bugs here are places its rule
was not applied.

---

## What the user reported, from the live Store build

1. Export a text file to PDF, click **Open** in the confirmation dialog, and
   macOS says *The application "Neight" does not have permission to open
   "சொல்வெளி ஆப் ஸ்டோர்.pdf"*. The PDF itself was written correctly.
2. A file was open and saved once successfully; a later save of the same file
   failed on permissions. Along with it, an explicit ask: **a failed auto-save
   must not lose the user's work silently.**

The question behind (2) was "does the sandbox permission time out?". It does
not — sandbox extensions have no timer. But this build does not rely on the
extension: Qt dissolves it into a bookmark and **re-resolves that bookmark on
every open**. So a write fails whenever the lookup key is wrong or the bookmark
no longer resolves, which is timing-dependent in ways elapsed time does not
explain.

## The rule reaches further than the two I/O calls

The 2026-08-23 fix routed reads and writes through `QFile` keyed on the exact
path string. Two consequences of that rule were missed.

### The key has to be *kept*, not just used once

`_open_file_path` computes `qt_path` — the exact string, with a comment
explaining that `Path()` collapses `//` and `./` and rewrites `~`, "precisely
the kind of mismatch that would miss the bookmark lookup" — and then stored
`current_path = str(path_obj)`, the normalised form. Every later write used
that. Demonstrated against the shipped code:

```
opened with:     '/…/tmpvlwf7dkf//keyed.txt'
saved keyed on:  '/…/tmpvlwf7dkf/keyed.txt'
```

A file that opens fine and can then never be saved. The same normalised value
was persisted as `last_opened_file`, so the reopen on the next launch inherited
it.

Fixed by keeping the grant's own spelling in `_grant_path` beside
`current_path` — which keeps its meaning, since every display, `Path()` call
and settings write wants the normalised form. `_io_path()` is the single place
that chooses between them, and only the sandboxed branch consults it.

**This does not explain the reported case.** For the user's symptom — first
save fine, later save denied — the key would have been wrong from the very
first save. It is a real defect with the same signature, fixed on its own
merits; the reported one is still open (below).

### Handing a path to another process needs the access *live*

`QDesktopServices.openUrl` does not go through a file engine at all. It asks
LaunchServices, which checks whether **this** process may read the file before
handing it to another app. Qt is holding the grant dormant as a bookmark, so
there is no live access and macOS refuses — and `openUrl` returns `True`
anyway, so the existing `if not opened:` branch could never fire. The alert the
user saw was macOS's, not Neight's.

`_sandbox_open_externally` opens the file through `QFile` first. That does two
jobs: it makes Qt resolve the bookmark and *start* the scoped access, and a
failed open is a reliable signal that no grant exists — in which case `openUrl`
is never called and Neight reports the problem itself. The handle is registered
**before** the call and released on a 10-second timer, not in a `finally`: Qt
may dispatch the open asynchronously, and stopping access on return would race
the permission check.

The `Path(save_path).resolve()` the URL was built from is gone; it broke the
exact-path rule outright.

Other `openUrl` call sites were checked and left alone — the project page is an
`https:` URL, and the Debug Info rows and the recovery folder are container
paths the app always has access to.

## A failed auto-save is now loud

Independent of root cause, and the part that matters most. `_on_autosave_failure`
restored the dirty flag, flashed *"Auto-save failed"* for three seconds, and let
the timer keep firing — which is how someone keeps typing for an hour into a
file that is no longer being written.

Now, in order: a copy of the **current** document text (not the worker's stale
snapshot) is written to `unsaved-<stem>-<timestamp>.<ext>` in the app data
folder — inside the container when sandboxed, so that write needs no grant and
cannot be denied; auto-save stops rather than clearing the dirty flag on every
tick; and a dialog names the file, the copy, and the fact that the changes are
not saved. On a sandbox denial it offers **Save As…**, the only thing that
mints a fresh grant — the save-side match for the message `_open_file_path` has
always shown on the read side. A denied *manual* save now says the same instead
of reporting the errno.

`_write_failure_copy` deliberately does not reuse `_recovery_write`: that one is
asynchronous, keeps one file per window session, and is deleted by
`_clear_recovery_file` on the next successful save. This copy has to exist
*before* the dialog that names it, and has to survive as evidence.

## Sandboxed saves now record how they went

`NEIGHT_SANDBOX_DIAG` cannot answer a user's report — it is opt-in by
environment variable, and Store users launch through LaunchServices where no
such variable exists. Each sandboxed write appends one `SANDBOX SAVE:` line to
the always-on auto-save log, already reachable from **Help › Debug Info**:
which door the write took (`qfile` / `python-fallback` / `denied`), whether it
was keyed on the grant or on `current_path`, which thread wrote, and how many
writes that grant had already served.

That last number is the one to watch. It is what would distinguish a grant that
was never right from one exhausted or evicted after N writes.

## Tests

`tests/test_sandbox_qt_io.py` gains three sections (registered already, so no
change to `checks.yml`): the grant key surviving an open into the next save;
`_sandbox_open_externally`'s exact path, its live handle during `openUrl`, and
its refusal to call `openUrl` without a grant; and a failed auto-save leaving a
copy on disk, the document modified, and auto-save stopped. Tamil filenames
throughout — the reported failure was on one. 43 checks, and the full suite
passes offscreen under a fresh `.venv` on PySide6 6.11.1.

The unsandboxed paths were driven end to end separately — both PDF exports,
`openUrl` receiving the plain path with no handle retained, manual save and an
auto-save tick — to confirm nothing off the sandbox moved.

## Later the same day: "could another instance have caused it?"

The user asked whether a second Neight instance opening the same file could
explain the permission failure. Chasing it turned up one plausible-but-unproven
cause and one certain bug.

### Every window is a separate process

`new_window` shells out with `subprocess.Popen`, and `NeightApplication` keeps a
single `_main_window` that Finder's "Open With" *reuses* rather than opening a
second window in-process. So a second instance was the only way to have one file
open twice — and nothing guarded against it.

### The permission theory: plausible, still unproven

Every instance shares one container and therefore one
`SecurityScopedBookmarks.plist`. The shipped QtCore binary's own log strings
give the shape: it loads the store (`Loaded existing bookmarks for`), looks up
`based on incoming fileName`, and on a miss says `No bookmark found. Falling
back to QFSFileEngine.` — which inside the sandbox is exactly the `EPERM` path.
Qt does that read-modify-write with **no cross-process lock**, the very hazard
`SettingsManager.lock()` exists to answer for `settings.json`.

What cannot be settled here: whether the losing instance re-reads the plist
mid-session. If Qt loads it once per process and keeps the map in memory, a
second instance costs the *next launch* its grants rather than the current
session's saves. So this is not claimed as the root cause — it is made
**testable**: `_log_sandbox_save` now records whether the writing instance owns
the document, and `_write_autosave_log` stamps every line with the PID. A
denied save in a non-owning instance, beside a successful one in the owner, is
the evidence. Nothing else available here can produce it.

### The certain bug, and its fix

Two instances on one file destroyed each other's work. Demonstrated against the
shipped code: window A saves an afternoon's writing, window B's *background*
autosave lands a stale snapshot, and A's work is gone — no error, no prompt,
nothing in the file to say it happened. There is no `QFileSystemWatcher` and no
mtime check anywhere in Neight, so neither window can notice.

A document is now owned by one instance, via `QLockFile` — the same mechanism
`SettingsManager` already uses. The lock lives under `_get_app_data_dir()/locks`
(inside the container when sandboxed: always writable, shared by every
instance), keyed on a hash of the **normalised** path. That last choice reads as
a contradiction of the rule beside it and is deliberate: Qt's bookmark must be
keyed on the exact string the panel returned, but two instances that reached one
file by differently spelled paths still have to collide here.

The non-owner keeps everything except the background write: the file opens, stays
fully editable, says so in its title, warns once on open, and every autosave tick
goes to `_recovery_write()` instead — machinery that already existed for exactly
this shape of problem and until now only ran for never-saved documents. A manual
save is still allowed and logged; the person is present and was told.

`setStaleLockTime(0)`, because a document can sit open for a working day.
QLockFile still reclaims a lock whose owning process is gone, which is the
reclamation actually wanted.

New `tests/test_document_lock.py` (26 checks, registered in `checks.yml` and
`tests/README.md`). It contends with a second `QLockFile` rather than a spawned
process: Qt refuses a second lock even within one process — verified before the
test was written — so the cheaper form exercises the same refusal.

One thing the change exposed: `tests/_harness.py` redirected settings but not
`Path.home()`, so taking a lock on open would have left files in the real
`~/Documents/Neight` of whoever ran the suite. The harness and
`test_sandbox_qt_io.py` now redirect home too.

## Later again: a sandbox compliance audit, and a wrong finding

Asked to check whether the day's changes touched Windows, and whether every
file-handling pathway complies with the sandbox.

### Windows

Three changes reach it, all deliberate and tagged `[Both]`: the document lock
(New Window spawns a process there too, so the cross-instance overwrite was
identical), the loud auto-save failure, and the PID in the log. The
`_grant_path` / `_io_path` work is inert on Windows — verified by exercising the
non-sandbox branch, which is the branch Windows always takes: `_grant_path`
equals `current_path`, `_io_path()` passes through, and `last_opened_file` is
byte-identical to before. The PDF "Open" button is behaviourally identical off
the sandbox; the only changed line there is the dropped `Path.resolve()`, a
no-op on an absolute path from `getSaveFileName`.

One incidental regression was found and fixed: `_report_save_failure` treated
every `PermissionError` as the sandbox withdrawing a grant and dropped the
errno, which on Windows — where a read-only file or one open in another program
raises exactly that — said *less* than the bare "Could not save file" it
replaced.

**Not run on Windows.** No machine here, CI is ubuntu-only. Outstanding.

### The audit came back clean

Native panels everywhere (`QFileDialog` statics, no `DontUseNativeDialog`
anywhere, so Powerbox is engaged); user reads and writes through Qt on the exact
path; `QPrinter.setOutputFileName` writing through QFile; settings
short-circuiting to Application Support on macOS so the bundle `.write_test`
probe is Windows/Linux-only; recovery, presets, logs and locks all inside the
container; preview and help links through `setOpenExternalLinks`, which Qt
routes to NSWorkspace; no drag-and-drop handlers to audit at all.

### A wrong finding, recorded because it was wrong

It was claimed here that **"Search with Google" and Sorkuvai lookup were broken
in the Store build**, because `webbrowser.open` reaches
`os.popen("/usr/bin/osascript", "w")`, which execs `/bin/sh`. **That was wrong.**
The user tested both in the Store build: they work.

The error was inferring a general rule from the comment then sitting in
`_view_recovery_folder` — "the sandbox does not let a process exec a binary
outside its own bundle" — and applying it without checking. The App Sandbox
permits fork/exec; children simply inherit the sandbox. And on the http branch
CPython emits `open location "<url>"`, StandardAdditions resolving to
LaunchServices opening a *web* URL: no Apple Event to a named application, no
file grant, no entitlement. The entitlement-hungry branch is the `else`, for
non-web URLs or a named browser, which neither call site reaches.

That comment has been corrected in place rather than deleted, since it was read
as a rule and applied once already. Two consequences worth carrying forward:

- **Do not treat "sandboxed apps cannot exec" as a rule.** It is not one.
- **`new_window`'s `subprocess.Popen` therefore very likely works in the Store
  build**, which makes the two-instance theory for the save failure *more*
  plausible, not less, and makes the document lock load-bearing on macOS rather
  than only on Windows. Added as step 11 of the signer's manual pass, because a
  "no" there would kill the theory outright.

A separate question — whether `_validate_url`'s HEAD request can work without
`com.apple.security.network.client` in `Neight.entitlements` — was raised and
**closed by the user without change**. `_validate_url` and PRIVACY.md item 4
stay as they are.

## A test build, and a build script that lied about it

Built 2026.087 locally so the changes could be tried by hand. `buildme_mac_app.sh`
has no flag for this: it bumps `VERSION` first and force-pushes `dist-latest`
last, so running it *is* publishing. The way through is a throwaway clone with
`origin` removed -- the publish step is best-effort and skips cleanly with "No
'origin' remote configured", leaving the real tree clean and the public download
untouched.

Doing that exposed a defect in both build scripts. The closing banner --
"This build is now the public macOS download ... it went live the moment it was
published above" -- printed **unconditionally**, three lines below the warning
saying the publish had failed. `buildme.bat` had the identical bug and already
had a `PUBLISH_RESULT` variable it was not consulting. Both banners are now
keyed on whether the publish actually happened.

Worth stating the asymmetry the fix protects: of the two ways to be wrong,
telling someone a private build is public wastes a little worry; telling them a
public build is private does not. The old text could do the second.

**What that build can and cannot verify.** It is signed ad-hoc and deliberately
*without* `packaging/Neight.entitlements` -- the script says why: sandboxing a
direct-download build that has no provisioning profile would only break it. So
`_macos_is_sandboxed()` is False in it and **neither sandbox fix is reachable**.
The document lock, the auto-save failure dialog and ordinary regressions are
all testable; the PDF "Open" fix and the grant-key fix still need the signer.

## Still open

**The reported intermittent save failure has no identified root cause.** What
is fixed is a defect with the same signature, plus the certain cross-instance
data loss above; what is added is a guarantee the user does not lose work when
it happens and a log that says why. Committing to a root-cause fix without a
signed reproduction is how 2026.082 and 2026.083 were spent, and that is not
repeated here.

Candidates, none decidable from this machine:

- a second instance clobbering the shared `SecurityScopedBookmarks.plist` —
  now instrumented, see above;
- the file replaced on disk by another process (a sync client, another editor's
  atomic save), leaving Qt's bookmark pointing at a dead inode;
- the file moved or renamed;
- eviction from Qt's `SecurityScopedBookmarks.plist`;
- leaked `startAccessingSecurityScopedResource` calls from the auto-save worker
  thread exhausting a per-process limit. The comment in `_autosave` asserting
  that worker-thread redemption "works the same as on the UI thread" is an
  assumption that has never been verified.

`packaging/HANDOVER-MAC-APP-STORE.md` now asks the signer for the PDF **Open**
click (step 7) and for repeated saves across several minutes (step 9), and for
the auto-save log alongside the diagnostics log.

If the `QFile` probe succeeds but LaunchServices still refuses, the user is
covered — Neight's own message, not a system alert — and the next step would be
resolving Qt's bookmark directly. Deliberately not attempted: it means
reintroducing the objc bridge removed on 2026-08-23.
