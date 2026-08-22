# 2026-08-22 (second session) — 2026.083 rebuilt on a python.org Python; handover package ready for the signer

**State at close:** `main` @ the commit carrying this note, pushed, working tree
clean apart from the gitignored `dist/`. `VERSION` = `2026.083`. `dist-latest`
serves a macOS build that declares **and needs** macOS 15.0. The handover
package for the signer is assembled and published.

Date: 2026-08-22
Context: **supersedes the runbook** in
[`2026-08-22-sandbox-file-open-and-save-prompt.md`](2026-08-22-sandbox-file-open-and-save-prompt.md).
That note ended with "rebuild on a python.org Python" as the outstanding work.
That rebuild is done, and this note records the result. Everything else in the
earlier note — the security-scoped bookmark investigation and fix, the
unsaved-prompt fix — still stands and is not repeated here.

---

## What is still outstanding

Exactly one thing, and it is not on this machine:

**The signed Store submission.** Send the friend who signs:

- `dist/handover-2026.083/` — assembled locally, holding the bundle zip,
  `HANDOVER-MAC-APP-STORE.md`, and `Neight.entitlements`; **or** point them at
  `dist-latest`, which now carries all three at raw URLs.

The file-open fix from the previous session is **still unverified** and can only
be verified in a signed, sandboxed build. Nothing further can be learned about
it here. The most valuable thing to ask for remains a locally signed test build
— see the asks list in `packaging/MAC-APP-STORE-SIGNING.md`.

**`release_macos.sh` cannot run yet.** It requires
`stable/Neight-mac-arm64-signed.zip`, which only exists once the signing has
happened. The GitHub release for 2026.083 therefore waits on the same person.
That is the expected order, not an oversight.

## The rebuild

The floor moved exactly as predicted, with no source change:

| | 2026.082 (Homebrew Python) | 2026.083 (python.org Python) |
|---|---|---|
| CPython binaries | 58 @ **26.0** | 57 @ **11.0** |
| PySide6 bindings | 9 @ 15.0 | 9 @ **15.0** |
| Qt frameworks | 39 @ 13.0 | 39 @ 13.0 |
| Declared floor | 26.0 (raised by the build script, honestly) | **15.0, and true** |

The build script's floor check printed `Declared: 15.0   Actually required by
the binaries: 15.0` with no WARNING block, which is the success condition the
previous note specified. 15.0 is the floor PySide6 6.11 sets and is as low as
this app goes without changing Qt.

The interpreter was already installed when this session started
(`/Library/Frameworks/Python.framework/Versions/3.14`, `minos 10.15`), and
`.venv` had already been rebuilt on it. Only `.venv-build` and the build itself
remained.

### Verification

- All six test scripts pass under `QT_QPA_PLATFORM=offscreen` against
  `.venv-build` — **950 checks**, 0 failures.
- Bundle is `Mach-O thin (arm64)`, ad-hoc signed, **carries no entitlements**
  (correct for the direct download), declares `15.0`, `com.murasu.neight`.
- No binary links against `/opt/homebrew`; no `PIL`/`pptx` anywhere in the
  bundle.
- Open and save round-trip verified against a mixed Tamil/English file through
  `_open_file_path` and `_write_to_path`, with `SettingsManager` pointed at a
  temporary store so real user settings were untouched.
- The published zip's SHA-256 was re-downloaded from `dist-latest` and matches
  the local build **and** the hash written into the handover document:
  `54cc0edc41e18db028aeb802df22cebcb81dabab37384057df81170a8bba6d34`.

**Not verified, and not verifiable from here:** the sandbox file-open fix
itself. Unchanged from the previous session.

A GUI smoke launch was done (the app ran and quit cleanly with a Tamil file
passed in argv) but could not be inspected visually: this terminal has neither
Screen Recording nor Accessibility permission, so `screencapture` and
`System Events` both fail. The offscreen round-trip above is what actually
carries the evidence. Worth granting those permissions if visual checks are
wanted in future sessions.

## The handover package

`packaging/HANDOVER-MAC-APP-STORE.md` is new: a **self-contained** document for
someone who does not have the repository, condensing
`MAC-APP-STORE-SIGNING.md`. It leads with the entitlement that would otherwise
silently waste a review cycle — without
`com.apple.security.files.bookmarks.app-scope`,
`NSURL.bookmarkDataWithOptions:` returns nil and the app behaves exactly like
the broken release — and carries this version's artifact hash so the signer can
confirm what they received.

It also names the traps that cost time before: `--deep`, hand-editing the
bundle, re-zipping with `zip` instead of `ditto`, and the case-sensitive
`log stream` predicate that made an earlier investigation conclude there was no
sandbox denial at all.

`MAC-APP-STORE-SIGNING.md` stays as the internal reference and now points at it.
**Keep the two in step** — in particular the artifact hash, which changes on
every build.

`dist-latest` now holds `HANDOVER-MAC-APP-STORE.md` and `Neight.entitlements`
alongside the two binaries. The build scripts' publish step only ever replaces
its own artifact, so these persist across future builds — but the **hash inside
the document goes stale the moment another macOS build runs**. Refresh it when
handing over a new version.

## Documentation caught up with reality

Two drifts, both user-facing:

- **README and the website said macOS 12 Monterey.** No build has ever been able
  to honour that. Now macOS 15 Sequoia, in `README.md` and
  `docs/index.html`.
- **`DEVELOPER.md` said Python 3.12** and did not say that the build interpreter
  is the single most consequential choice in a macOS build. The macOS build
  steps now name the interpreter by absolute path, because `python3 -m venv`
  takes whatever is first on `PATH` — on a developer Mac, usually Homebrew's,
  which is precisely how 2026.082 happened. `docs/architecture.html` says
  Python 3.14. CI moved 3.12 → 3.14 to match what ships.

## `pillow` and `python-pptx` are out of the development requirements

Neight imports neither, but PyInstaller's hooks bundle whatever they can import,
and these two once put 18 MB of dead weight into a `Neight.exe` that was the
public Windows download for three weeks.

- **`python-pptx` removed outright.** The `make_slides.py` it existed for is not
  in this repository at all.
- **`pillow` moved to a new `requirements-design.txt`**, installed ad hoc when
  regenerating icons. Three scripts in `design/` genuinely use it, so it could
  not simply be deleted.

An ordinary development environment can therefore no longer produce a bloated
build by accident. **The clean-build-environment rule in `CLAUDE.md` still
applies** — it is now a second line of defence rather than the only one, and the
next optional package added anywhere will behave exactly the same way.

## Not done, deliberately

- **`release_macos.sh`** — blocked on the signed artifact, as above.
- **`argv_emulation=True`** in the spec, still untouched. Same reasoning as the
  previous session: redundant, plausibly implicated in a separate "Open With
  sometimes never arrives" symptom, and changing it is an untested behaviour
  change unrelated to anything in this session.
- **The Windows build** was not rebuilt. Nothing here touches it; `Neight.exe`
  on `dist-latest` is still the 2026.081-era clean build, and the
  `requirements-dev.txt` change does not alter an already-built binary.
