# Neight 2026.087 — handover for the Mac App Store update

**For:** whoever signs and submits Neight to the Mac App Store.
**From:** the Neight repository, <https://github.com/venkatarangan/neight>.
**Date:** 2026-08-24.

**2026.086 is live on the Store and its file I/O works** — thank you for
signing it. This is the follow-up submission, a **normal one**, not a
diagnostic: sign it as you did before and upload it. This document is
self-contained — you do not need the rest of the repository.

## What is new in 2026.087

Two things the 2026.086 fix left undone, both found by a user on the live
Store build, and one bug that has nothing to do with the sandbox:

1. **Exporting to PDF worked, but clicking Open in the confirmation dialog
   was refused** by macOS — "Neight does not have permission to open …" — for
   a file Neight had just written. `QDesktopServices.openUrl` does not go
   through a file engine at all: it asks LaunchServices, which checks the
   calling process's own access, and Qt holds the grant dormant as a bookmark.
   The file is now opened through `QFile` first, which wakes the grant, and
   the handle is held open across the call.

2. **A file that opened could then fail to save.** The open path used the
   exact path string the panel returned, then stored the normalised form,
   which every later save used — so Qt's bookmark lookup missed. The grant's
   own spelling is now kept and used for writes.

3. **Two Neight windows on one file destroyed each other's work.** Every
   window is a separate process and both auto-saved to the same path with no
   coordination. A document is now owned by one window; the second still opens
   and edits it, says so, and keeps its typing in a recovery copy instead of
   overwriting. This one is not macOS-specific.

A failed auto-save now also stops, keeps a copy, and says so in a dialog
rather than a three-second status message.

**Step 7 and steps 9–11 of the test below are the new ones** — everything else
is the pass you already know.

## Background: what your diagnostic run found

Your log proved that the Open panel *was* granting access, and that Qt was
converting the grant into a bookmark in its own store at the same instant
Neight's Python-level read was denied. The inference you flagged was right:
Qt 6.11 registers its own security-scoped file engine inside the sandbox, and
that engine — not the app's code — owns the grant from the moment the panel
closes. Access exists, but only for I/O that goes through Qt's file classes.

So the fix was on our side and was exactly your first "where to look next"
suggestion: **Neight now reads and writes user files through Qt** whenever it
runs sandboxed. The bookmark machinery you watched fail in 2026.084 is deleted
— Qt's own store does that job, including across relaunches. The
launch-dependent sandbox detection you flagged is also fixed
(`sandbox_check()` instead of the environment variable).

### Why the first attempt still could not save

Reads went through `QFile` and worked. Writes went through `QSaveFile`, and
`QSaveFile` cannot work inside the App Sandbox at all. Reading Qt 6.11.1's
`qsavefile.cpp`, two things compound:

- It writes to a temp file **beside** the target, created through a
  `QTemporaryFileEngine` it constructs *directly* — bypassing
  `QAbstractFileEngine::create()`, so the security-scoped engine never sees
  it. The panel grants the chosen *file*, not its *directory*, so creating
  that sibling is denied.
- `setDirectWriteFallback(true)` is the documented escape hatch, and it *does*
  go through the engine — but Qt guards it on `errno == EACCES`. Sandbox
  denials return **`EPERM`**. The fallback never fires, `open()` returns
  false, and the user sees "Could not save file".

This build writes with `QFile` opened `WriteOnly|Truncate` on the final path —
which is precisely what `QSaveFile`'s own `openDirectly()` would have done had
Qt's errno check let it run. Same door the working read path uses.

One consequence worth knowing if a user ever reports it: **the sandboxed save
is not atomic.** It cannot be — the sandbox forbids the write-temp-then-rename
pattern. A crash during a save can leave the file truncated. Outside the
sandbox (the direct download, Windows) saving is unchanged and still atomic.

Both of your corrections to our documents were taken: local reproduction with
a plain Developer ID / Development signature is now recorded as possible, and
your `LSMinimumSystemVersion` finding is noted as resolved on your side.

### Other sandbox fixes in the same build

While tracing the save path we swept every other place Neight touches the
filesystem. Settings were already correct. These were not:

- **Recovery copies and mode presets** were written to `~/Documents/Neight`.
  Inside the sandbox that is the *container's* Documents — the writes
  succeeded, but into a folder no user can find and that is deleted with the
  app. Sandboxed, they now go to Application Support, and every dialog that
  names the folder shows the resolved path.
- **PDF export** worked but never checked, so a denied write still showed a
  success dialog. It now verifies the file was produced.
- **"View Recovery Folder"** shelled out to `/usr/bin/open`, which a sandboxed
  process may not exec. It now uses NSWorkspace via Qt.
- **"Open .md files with Neight"** called Launch Services to set the default
  handler, which the sandbox forbids. That button is now disabled in the Store
  build, with a note pointing at Finder's Get Info → Change All instead.
- **The Open and Save panels** started in `~`, which sandboxed is the
  container root — an unrecognisable folder where a saved file effectively
  vanishes. They now start in the user's real Documents.

## What is live right now

Unchanged since 2026-08-22, for
[`id6800348235`](https://apps.apple.com/app/neight/id6800348235?mt=12): the
listing shows version **1.0**, minimum **macOS 12.0**, and that build cannot
open any file. This submission replaces it.

There is still one open question worth answering at upload time: the Store
says version **1.0**, but the bundle stamps `CFBundleShortVersionString` with
Neight's own version. If App Store Connect (or your process) maps it to `1.0`,
just tell us what mapping you use, so a bug report naming a Store version can
be traced to a build.

---

## What you are signing

| | |
|---|---|
| **Version** | 2026.087 |
| **Bundle identifier** | `com.murasu.neight` |
| **Architecture** | Apple Silicon (arm64) only — deliberately no Intel or universal slice |
| **Minimum macOS** | 15.0 (Sequoia) |
| **Artifact** | `Neight-mac-arm64-unsigned.app.zip` |
| **SHA-256** | `5d16a56f0c97f7cef3ceee05970e6d37a900a949a4af2e3fc89063593ea5bb3f` |

> The SHA-256 above is from the actual 2026.087 artifact, taken at build
> time. Any hash carried over from an earlier build is wrong by definition —
> `buildme_mac_app.sh` produces a new artifact every run.

Verify before you start — the `dist-latest` branch is force-pushed on every
build and may have moved on:

```bash
shasum -a 256 Neight-mac-arm64-unsigned.app.zip
ditto -x -k Neight-mac-arm64-unsigned.app.zip .
```

The bundle carries an **ad-hoc** signature and **no entitlements**. That is
correct for the direct download it also serves as. Your signing replaces that
signature entirely.

---

## Entitlements: same file, one shifted reason

**Sign with `Neight.entitlements`, included alongside this document** — the
same file and the same four keys as the 2026.084 test build:

| Key | Why |
|---|---|
| `com.apple.security.app-sandbox` | Required for the Store. |
| `com.apple.security.files.user-selected.read-write` | Read and write the files the user picks in the Open and Save panels. |
| `com.apple.security.files.bookmarks.app-scope` | **Qt's file engine mints and redeems security-scoped bookmarks with this.** It is what makes access survive a relaunch. |
| `com.apple.security.files.bookmarks.document-scope` | Bookmarks tied to a document rather than to the app. |

The bookmarks keys used to be justified by Neight's own bookmark code; that
code is gone, but the keys stay — they are now what lets *Qt's* engine (the
one your run caught writing `SecurityScopedBookmarks.plist`) do the same
minting legitimately. Switching the write path from `QSaveFile` to `QFile`
does not change this: both go through the same engine.

Still deliberately absent, unchanged: any
`com.apple.security.temporary-exception.files.*`. Please do not add one to get
a build through.

Your identity choice is yours: the 2026.084 run showed a Developer ID
signature engages the sandbox and Powerbox correctly, and the Store submission
uses your usual `3rd Party Mac Developer Application` / Apple Distribution
identity as before.

---

## Rules for handling the bundle

Unchanged, and your 2026.084 run already followed all of them:

- **Do not edit anything inside the bundle**, `Info.plist` included — and with
  your script's `LSMinimumSystemVersion` overwrite fixed, nothing should touch
  it now. The bundle declares 15.0; it should still say 15.0 when submitted.
- **Do not use `--deep`.** Sign nested code inside-out, as you did.
- **`--options runtime` is not needed** for a Store build, per your own note.
- **Do not re-zip with `zip`.** Use `ditto -c -k --sequesterRsrc --keepParent`.

## Verifying before you submit

```bash
# 1. The entitlements actually made it in -- the check that matters most.
codesign -d --entitlements :- Neight.app

# 2. The signature is valid and covers nested code.
codesign --verify --strict --verbose=2 Neight.app

# 3. Identity and architecture.
codesign -dvv Neight.app 2>&1 | grep -E 'Authority|TeamIdentifier|Format'

# 4. The floor was not overwritten.
/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' Neight.app/Contents/Info.plist
```

Expected: all four entitlement keys; `Format` reads
`app bundle with Mach-O thin (arm64)`; step 4 prints `15.0`.

---

## Please test before uploading

Unlike 2026.083, this fix *can* be tested by you in minutes, with a locally
signed build (Developer ID is fine for the test — your 2026.084 procedure
exactly). On any Mac:

1. Launch Neight **by double-clicking it in Finder** — not from Terminal. The
   two launch paths behaved differently in the bug you found, and Finder is
   how every user launches.
2. **File > Open** a `.txt` on the Desktop. It must open. This worked in your
   last run and must keep working.
3. Open a file inside Dropbox / iCloud Drive / OneDrive.
4. Edit and **File > Save**. **This is the step that failed for you last
   time** — it is the one this build exists to fix.
5. **File > Save As** to a new name, in a different folder. The Save panel
   should open somewhere recognisable, not inside a `Library/Containers` path.
6. Leave the window open and edited for one auto-save interval (Settings >
   Auto-save; set it to the shortest option to avoid waiting). The status bar
   must say "Auto-saved", not "Auto-save failed".
7. **File > Export to PDF**. The PDF must actually appear where you put it,
   **and clicking Open in the confirmation dialog must open it in Preview.**
   That click is what failed in 2026.086, with a macOS alert saying Neight
   does not have permission to open the file it had just written.
8. Quit, relaunch from Finder. With **Continue where you left off** enabled,
   the file must come back — that is Qt's bookmark store surviving a restart —
   and **saving it again must still work**.
9. Keep one file open and save it **several times over several minutes**, with
   auto-save running between the saves. A user reported a save that worked
   once and then failed on permissions later in the same session; if that
   happens here, the auto-save log (below) now records how each write went.
10. Open **one file in two windows** (File > New Window, then open the same
    file in it). The second window must say the file is already open, must
    show "(open in another window)" in its title, and must **not** auto-save.
    Save from the first window and let the second one's auto-save tick pass:
    the first window's text must survive. Then save by hand from the second —
    that is still allowed, and is expected to win.

    This step is also the one that tests whether a second instance is what
    broke the save in step 9. All instances share one container and therefore
    one `SecurityScopedBookmarks.plist`, which Qt writes with no cross-process
    lock. If saving from the second window makes the *first* window's next save
    fail, the log will now show it: every line carries its process ID, and each
    sandboxed write records `lock=held` or `lock=not-held`.

11. **File > New Window.** Does a second window open at all in the signed
    build — with its own Dock presence and menu bar — and can it open a file
    through its own panel? New Window spawns a *separate process*
    (`subprocess.Popen` on the bundle's own binary), and whether that works
    under the Store sandbox has never been confirmed. Step 10 depends on it,
    and so does the leading theory for the step 9 failure: if a second instance
    cannot start, two instances cannot be what broke the save.

If any step fails, run once with `NEIGHT_SANDBOX_DIAG=1` as you did for
2026.084 and send the log — same location:

```
~/Library/Containers/com.murasu.neight/Data/Library/Application Support/Neight/sandbox-diagnostics.log
```

It now narrates the Qt read/write path instead of the bookmark path, and names
the stage that failed (open / write / flush / close) with Qt's own error
string — so one log should be enough to place any remaining problem exactly.

For step 9 send the **auto-save log** as well, from the same folder. Every
sandboxed write now appends a `SANDBOX SAVE:` line to it whether or not
diagnostics are on, naming which door the write took (`qfile` = Qt's bookmark
resolved, `python-fallback` = it did not but a process-wide grant covered the
file, `denied` = neither), which thread wrote, and how many writes that grant
had already served.

If all eleven steps pass, upload.

---

## Context you may want

- **The functional changes since the live 2026.086** are the three listed at
  the top, plus the louder auto-save failure. Nothing else changed behaviour.
  The macOS 15.0 floor work is carried forward.
- **Not yet exercised on Windows.** Neight ships on the Microsoft Store too,
  and the document-ownership change affects both platforms; it has been run on
  macOS and Linux only. Irrelevant to your signing, noted for completeness.
- **The app makes no network calls on its own.** It never checks for updates
  or contacts a server unless the user clicks something. Worth knowing if App
  Review asks.
- **Neight is a Tamil and English text editor**, PySide6 (Qt 6) on Python
  3.14, single-window, document-based. It declares plain-text and Markdown
  document types so it appears in Finder's **Open With**.
- **Version numbering.** `YYYY.NNN` — `2026.087` is the 87th build of 2026,
  not a semantic version.
- **Full reference:** `packaging/MAC-APP-STORE-SIGNING.md` in the repository,
  which this document condenses. The live listing is at
  <https://apps.apple.com/app/neight/id6800348235?mt=12>.

Questions are welcome and cheaper than a rejected submission — and the
diagnostic round trip you did is what made this a one-line-of-reasoning fix
instead of another guess. Thank you.
