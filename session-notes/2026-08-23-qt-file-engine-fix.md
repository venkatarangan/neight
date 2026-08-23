# 2026-08-23 — Qt owns the sandbox grant; file I/O now goes through Qt

**State at close:** `main` @ the commit carrying this note, `VERSION` =
`2026.084` (spent as a diagnostic — the next build must be 2026.085), tree
dirty only if the build has not been run yet. The fix for the Store build's
file-open/save failure is committed but **unverified in a signed build**; the
decision was to submit directly without another diagnostic round.

Date: 2026-08-23
Context: supersedes [`2026-08-22-sandbox-file-open-and-save-prompt.md`](2026-08-22-sandbox-file-open-and-save-prompt.md)
— the security-scoped-bookmark mechanism that note introduced is **removed**
by this session, for the reasons below. Also supersedes the diagnostic-run
request recorded in [`packaging/SIGNER-DIAGNOSTIC-RUN.md`](../packaging/SIGNER-DIAGNOSTIC-RUN.md),
which was answered today.

---

## What the signer's diagnostic run established

The signer ran 2026.084 (signed Developer ID, correct entitlements, two runs,
Terminal and LaunchServices) and sent back
`sandbox-diagnostics.log` plus an analysis. The decisive pair of facts, from
the same second on the same path:

- Neight's log: `grant: NO panel access` — Python's `open()` denied
  immediately after the Open panel returned, on every file, in both runs; our
  `bookmarkDataWithOptions:` returned nil every time.
- The container: `SecurityScopedBookmarks.plist`, written **by QtCore**, had
  just gained a valid 780-byte scoped bookmark for that exact path.

So Powerbox granted access, and Qt took it. Verified locally against the
bundle's own binaries: `strings` on
`dist/Neight.app/.../QtCore.framework/Versions/A/QtCore` shows
`SecurityScopedFileEngineHandler`, log category
`qt.core.io.security-scoped-fileengine`, and the message "Application sandbox
is active. Registering security-scoped file engine." Qt 6.11 installs a
`QAbstractFileEngineHandler` in sandboxed processes that consumes the Powerbox
grant at panel-close, stores it as a bookmark in its own plist, and re-opens
it transparently — **but only for I/O through Qt's file classes**. Python's
`open()`/`pathlib` bypass file engines entirely, which is why every
Python-level read was denied and why our own minting always failed: by the
time it ran, there was no live grant left to mint from.

Two claims in our documents were disproven by the same run:

- "Powerbox never vends a file grant to an unprovisioned app" — false. A plain
  Developer ID or Apple Development signature is enough; only ad-hoc
  signatures are refused at the panel. **Sandbox bugs are locally reproducible
  with any Apple developer identity.** Muthu holds an
  `Apple Development: Muthu Nedumaran (GQ3UG4GVPW)` identity that could be
  exported if local reproduction is ever wanted here; no identity is installed
  on this machine today (`security find-identity -p codesigning`: zero).
- The `LSMinimumSystemVersion = 12.0` mystery on the live listing — solved. The
  signer's script was overwriting our 15.0 (and applying `--options runtime`);
  both fixed on their side.

## The fix

Inside the sandbox, user-file I/O goes through Qt, so the grant Qt already
holds is the one used:

- `_sandbox_read_bytes(path)` — `QFile` read, raising
  `PermissionError`/`OSError` with Qt's `errorString()`.
- `_sandbox_write_text(path, text, should_commit=None)` — `QSaveFile` with
  `setDirectWriteFallback(True)`: the Save panel grants the chosen file, not
  its directory, so the write-temp-beside-target strategy (ours *and*
  QSaveFile's default) can be denied; the fallback writes the target in
  place. `should_commit` is checked before writing as well as before
  `commit()`, because under the fallback `cancelWriting()` cannot undo bytes
  already written.
- `_open_file_path`, `_write_to_path` and the autosave worker branch on
  `_macos_is_sandboxed()`; existence/size checks use `QFileInfo` on that
  branch. **The path is passed exactly as the dialog returned it** — Qt keys
  its bookmark lookup on the incoming fileName, so canonicalising first (which
  the old wrapper did) would miss the stored grant.
- Everywhere else — Windows, Linux, unsandboxed macOS — file I/O is
  byte-for-byte the code it was, including `_atomic_write_text`'s fsync
  durability. Windows never reaches any of the new code.

`_macos_is_sandboxed()` now asks the OS via
`sandbox_check(getpid(), NULL, 0)` from `libsystem_sandbox.dylib`, cached,
with the old `APP_SANDBOX_CONTAINER_ID` check as fallback. The variable is set
under a Terminal launch but **absent under LaunchServices** (double-click —
how every Store user launches), so keying off it alone disabled the machinery
for exactly the people it existed for. `expanduser("~")` is not a valid probe
either; the sandbox redirects HOME into the container.

## What was removed

The entire ctypes bookmark layer from 2026.082: the objc bridge,
`macos_create_bookmark`, `_MacosScopedAccess`, `sandbox_access`,
`remember_sandbox_access`, `sandbox_bookmark_for` and the
`sandbox-bookmarks.json` store (~430 lines). It could never work for
panel-opened files — see above — and Qt's own store now provides the
cross-launch persistence it was for, which keeps "continue where you left
off" working in the Store build.

Kept: the `NEIGHT_SANDBOX_DIAG=1` diagnostic mode, re-pointed at the Qt I/O
path. A future signed run still narrates itself into the same log.

**Accepted limitation:** files delivered by Finder "Open With" arrive with a
process-wide grant rather than through Qt's dialog hook, so whether Qt
bookmarks them for a later relaunch is unverified; "continue where you left
off" may not survive a relaunch for such a file. The launch-time reopen
already fails silently (`notify_errors=False`), so the degradation is a
no-op, not an error. Revisit only if a user actually reports it.

## Entitlements

Unchanged, deliberately. The two `files.bookmarks.*` keys are still required —
the consumer is now Qt's engine rather than our code, but it is doing the same
minting and needs the same permission. `packaging/Neight.entitlements` stays
the source of truth.

## Tests

New `tests/test_sandbox_qt_io.py` (registered in `checks.yml` and
`tests/README.md`): byte-parity of the Qt helpers against the Python path over
a mixed Tamil/English corpus (BOM, CRLF, empty), the `should_commit`
withdrawal contract, error surfacing, and a window-level open/save with the
sandbox gate forced on. `test_unsaved_prompt.py`'s section 5 was rewritten —
it exercised the removed helpers; it now pins detection to False in an
ordinary run. Full suite passes under both `.venv` and `.venv-build`,
offscreen.

## Decisions taken this session

- **Remove the bookmark machinery entirely** rather than keep it as a
  fallback (user's call).
- **Submit directly** — no further diagnostic round trip with the signer
  (user's call). The handover doc
  ([`packaging/HANDOVER-MAC-APP-STORE.md`](../packaging/HANDOVER-MAC-APP-STORE.md),
  rewritten for 2026.085) still *asks* the signer to run the five-step manual
  test with their own locally signed build before uploading, since their run
  showed that costs them minutes, not a review cycle.

## Still to do

1. Run `PYTHON_BIN="$PWD/.venv-build/bin/python" ./buildme_mac_app.sh` — bumps
   to 2026.085, republishes `dist-latest` (the live public download; the
   current one there is 2026.083 without this fix).
2. Fill the SHA-256 into `packaging/HANDOVER-MAC-APP-STORE.md` (marked with a
   placeholder) and send it with the artifact and `Neight.entitlements`.
3. After a signed 2026.085 ships, update the "Store build is broken" warnings
   in `CLAUDE.md` and `packaging/MAC-APP-STORE-SIGNING.md`.
