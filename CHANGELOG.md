# Changelog

Notable changes to Neight. Newest first.

Platform tags mark where a fix applies: **[Windows]**, **[macOS]**, **[Both]**.
Anything untagged is cross-platform.

---

## 2026.079 — 2026-08-20

Neight is now available from the Microsoft Store, and the macOS build is being
prepared for the Mac App Store — which is what forced the update checker's
removal. Also adds selection-aware counts to the status bar.

### Added

- **The status bar counts your selection.** Select any passage and the word,
  sentence and character counters switch to it, shown as `Words: 42 of 1240` —
  the selection and the document total side by side, so the two can never be
  confused at a glance. Reading time relabels itself **Read (sel):**, since a
  duration reads badly as a ratio. Your **View → Status Bar** preferences still
  decide what appears: a counter you have hidden stays hidden and is never
  computed, so in Writer Mode a selection shows only `Words: 42 of 1240`.

  The counters appear a moment after a selection settles, so dragging or a
  double-click you immediately abandon never makes them flicker — but they
  revert *instantly* when the selection is cleared, since numbers describing a
  selection that no longer exists would be worse than none. Selecting the whole
  document reuses the counts already on screen instead of recounting.

### Performance

- **The status bar counters got noticeably cheaper on large documents.**
  Measured on a 730 KB mixed Tamil/English file with every counter enabled, a
  status refresh went from **126 ms to 98 ms**, and a refresh where the text
  had not changed from 126 ms to **effectively free** — the document is no
  longer recounted unless its revision or the visible counters actually moved.
  Repainting the counters (which happens whenever a selection appears or is
  cleared) went from **41 ms to 0 ms**.
- **Tokenising is about 1.5x faster.** **[Both]** The word splitter asked
  Unicode for a character's category once per character of the document; it now
  asks once per *distinct* character, which on real text is a few dozen lookups
  instead of hundreds of thousands. Output is unchanged — verified identical
  across 6,024 cases including Tamil combining marks, connectors and mixed
  scripts. The Word Index Overlay uses the same splitter and gets the same
  speedup.
- **Fixed a memory regression in the new selection counts.** The count cache
  was holding the document's full token list — about 6.7 MB on that same
  730 KB file, for as long as the window stayed open. It now caches only
  finished values, and the reading-time estimate is computed once per count
  rather than re-derived on every repaint.

### Infrastructure

- **Neight is on the Microsoft Store.** **[Windows]** The Store is now the
  recommended Windows install: Microsoft re-signs every Store package, so the
  SmartScreen warning that the direct `.exe` triggers never appears. The
  `.exe` on GitHub Releases stays available as a second, non-Store channel for
  anyone who prefers it. The website's Windows call-to-action already pointed
  at the Store listing; `README.md` now leads with it too.
- **The macOS bundle identifier changed to `com.murasu.neight`.** **[macOS]**
  Was `com.venkatarangan.neight`. Changed in
  `packaging/Neight.macos.spec` so the app can be submitted through the
  well-wisher's Apple Developer account for the upcoming Mac App Store
  release — the same account that already contributes the Developer ID
  signature for the notarized direct-download build.
- **README and website now lead with the store install paths.** **[Both]**
  Direct downloads from GitHub Releases are relabelled as a separate channel
  rather than the default, and the SmartScreen instructions are scoped to the
  direct `.exe` only.

### Removed

- **The update checker is gone.** **[Both]** Mac App Store review rejected the
  build over the "Check for Updates" feature, and it had become redundant
  anyway — Store installs update themselves on both platforms. Removed
  entirely: the silent GitHub check five seconds after launch, the background
  threads, the **●** badge on the Help menu, the **Settings → Check for
  Updates on Launch** toggle, and the **Help → Check for Updates…** dialog.
  **Help → Neight Releases on GitHub** replaces them — a plain link that opens
  the releases page in your browser, for anyone running a direct download. The
  app makes no request itself.
- **Neight now makes no automatic network connections at all.** **[Both]** The
  launch update check was the only one. Every remaining network use happens
  because you clicked something: a Markdown link, a Google or Sorkuvai lookup,
  **Validate URL**, or the new releases link. `PRIVACY.md` has been rewritten
  to say so.

  The `update_check_on_launch` key is no longer read or written. Existing
  `settings.json` files and saved Writer/Techie presets may still contain it;
  it is ignored and harmless.

---

## 2026.078 — 2026-08-03

Windows-only release. No application code changed — this exists because the
`v2026.077` release below could not be extended to hold a Windows build.

### Infrastructure

- **The Windows executable had to ship as its own version.** **[Windows]**
  This repo has GitHub's immutable-releases setting enabled. `v2026.077`'s tag
  had drifted behind `HEAD` by the time the Windows build ran, and both moving
  the tag and uploading `Neight.exe` directly to the existing `v2026.077`
  release were rejected by GitHub once a release is published, its tag and
  asset list are frozen. `VERSION` was bumped to `2026.078` and released
  separately instead; it is now the **Latest** release. Immutability has since
  been turned off for future releases, but not retroactively — `v2026.077`
  stays macOS-only forever.
- **Website and README macOS links now pin to `v2026.077` explicitly.**
  **[Both]** With "Latest" now Windows-only, the `releases/latest/download/…`
  link (added below, in `2026.077`) stopped resolving to a macOS asset. The
  Windows link keeps using `releases/latest/download`; the macOS link is a
  manual pin that must be updated by hand whenever a newer signed macOS build
  ships in a different release tag. `release-assets-check.yml` was updated to
  match — Windows checked against Latest, macOS checked against the pinned tag.

---

## 2026.077 — 2026-08-03

Signed, notarized macOS release. No application code changed.

### Infrastructure

- **First signed and notarized macOS build published as a release.**
  **[macOS]** Developer ID signature and notarization contributed by Muthu
  Nedumaran; verified with `codesign`, `spctl`, and `xcrun stapler validate`
  before upload.
- **Fixed the broken macOS download link on the website and README.**
  **[Both]** Both had pointed at the `v2026.073` release asset, which no
  longer exists (404). Switched to `releases/latest/download/…`, matching the
  pattern the Windows link already used.
- **Added a CI check that the Latest release has both platform assets.**
  **[Both]** `release-assets-check.yml` runs daily, on demand, and
  best-effort on publish; it flags a Latest release missing either platform's
  asset instead of a user hitting a 404. (`v2026.078` above is the reason this
  check exists — the split it warns about happened almost immediately.)
- **Fixed `release_macos.sh`'s version extraction.** **[macOS]** A
  single-quoted regex nested inside an outer single-quoted bash string broke
  the version read, failing before any release could run. Replaced with a
  plain `sed` extraction.

---

## 2026.076 — 2026-07-29

Corrects the Windows release provenance and makes release builds reproducible.

### Fixed

- **The Documents folder was spelled two different ways.** **[Both]** Saved
  presets were written to `~/Documents/neight` while recovery copies used
  `~/Documents/Neight`. On macOS and Windows the filesystem is case-insensitive
  by default, so those were the same directory and the split was invisible — but
  on a case-sensitive filesystem they were two separate folders. Both now use
  `Neight`, from a single constant so they cannot drift apart again. Where the
  old lowercase folder really is separate, presets found in it are copied
  across once, never moved, and an existing preset is never overwritten.

### Infrastructure

- **The Windows executable is built from a clean, runtime-only environment.**
  **[Windows]** The `v2026.074` executable was built in a development
  environment and accidentally bundled unrelated packages including NumPy,
  OpenBLAS, process utilities, YAML and character-detection libraries. The
  `2026.076` executable contains only Neight's runtime dependencies and
  PyInstaller support files.
- **Release scripts now require a clean working tree and read `VERSION` from
  committed source.** **[Windows] [macOS]** This prevents a release tag from
  describing an uncommitted build while pointing at older source, which is what
  happened to `v2026.074`.
- **Release scripts explicitly create and push a verified tag before creating
  an immutable GitHub Release, and Windows now stops on every failed `gh`
  command.** The first correction attempted to reuse deleted `v2026.075`, but
  GitHub permanently reserves tag names used by immutable releases. The failed
  command was reported correctly after this fix. The Windows script also probes
  for an existing remote tag without treating an expected missing tag as a
  PowerShell error. The release advanced to `v2026.076`.
- **The version incrementer now preserves existing line endings and uses
  console-safe output on Windows.** It previously updated the version and then
  reported failure because the legacy Windows console could not print a Unicode
  checkmark; its normal text write also converted the source working copy to
  CRLF.

---

## 2026.073 — 2026-07-29

Build tooling only — no application code changed, so nothing here affects the
running app.

### Infrastructure

- **`buildme_mac_app.sh` and `buildme.bat` now publish the freshly built,
  unsigned artifact to a `dist-latest` branch on every successful build.** An
  external code-signing workflow fetches the unsigned build over a plain
  `raw.githubusercontent.com` URL, which only serves a file actually committed
  to *some* branch — `dist/` itself stays gitignored on `main`, on purpose
  (see 2026.070 below). Each publish amends the branch's one existing commit
  and force-pushes rather than adding a new one, so it never accumulates old
  binaries: always exactly one commit, always just the current Mac and Windows
  artifacts. Either script can run independently, on its own machine, without
  clobbering what the other already published. Best-effort — a publish
  failure is reported but does not fail the build. Full detail in
  [`DEVELOPER.md`](DEVELOPER.md#the-dist-latest-branch).

---

## 2026.072 — 2026-07-29

Refines the BOM-less UTF-16/32 detection added in 2026.070, and fixes a
platform gap in the test suite that was hiding a class of failure on Windows.

### Fixed

- **BOM-less UTF-16/32 detection tightened.** **[Both]** The heuristic added
  in 2026.070 — skip a decode that leaves NUL bytes between characters, prefer
  a wide encoding instead — could itself misclassify a genuine UTF-8 file that
  happens to contain a real NUL. A new check confirms the NULs actually fall
  in a consistent lane (every other byte for UTF-16, every fourth for UTF-32)
  before accepting that decode, so a UTF-8 file with a stray NUL is no longer
  at risk of being reinterpreted as wide text.

### Infrastructure

- **The text-integrity test suite now checks the platform's actual newline,
  not an assumed `\n`.** **[Windows]** The "opening and re-saving an
  already-correct file must not touch a byte" fixtures were built against a
  bare LF, which is not what "already correct" means on Windows — Neight
  normalises to CRLF there. The fixtures now build against
  `Notepad.NATIVE_NEWLINE`, so the suite exercises what it claims to on both
  platforms rather than only ever proving the Windows path with Unix newlines.

---

## 2026.071 — 2026-07-29

Trackpad zoom and click handling. Six defects, all in event bookkeeping rather
than layout. Full detail in
[`knownbugs/TRACKPAD-ZOOM-AND-CLICK-FIXES.md`](knownbugs/TRACKPAD-ZOOM-AND-CLICK-FIXES.md).

### Fixed

- **Triple-click-to-search was inverted.** **[Both]** The feature never fired on
  a real triple click, and *did* fire on ordinary clicks used to move the caret
  around a long document — selecting a word you had not selected and opening a
  browser. Qt delivers the second click of a double click as
  `MouseButtonDblClick`, not `MouseButtonPress`, so the old press-counting
  handler could only ever reach two. It also had no distance test, so with
  macOS's 500 ms double-click interval any three quick clicks, however far
  apart, were stitched together; typing in between did not reset it either.
  Now built on Qt's own model — the third click must fall within the drag slop
  of a genuine double click, and typing, scrolling or focus loss ends the
  sequence.
- **Clicking no longer disturbs Qt's selection state.** **[Both]** The old
  handler returned early without calling `super().mousePressEvent()`, so
  `QWidgetTextControl` never saw the press.
- **Reversing wheel-zoom direction was damped.** **[Both]** After zooming in,
  the first several notches of zoom-out only paid off banked travel — five
  notches down against three up. Both directions now cost the same.
- **Trackpads were zoomed on the mouse-wheel scale.** **[macOS]** The
  pixel-precise path only ran when `angleDelta` was exactly zero, which on macOS
  it never is. `pixelDelta` now takes precedence when present.
- **Zoom accumulation had no gesture boundary.** **[Both]** A partial step banked
  in one gesture ate the start of the next, possibly minutes later. A 250 ms
  quiet gap now ends a gesture.
- **Pinch-to-zoom was roughly three times too fast.** **[macOS]** An ordinary
  pinch moved the font 14 points and a fast one 18 — from a 12 pt document, the
  size limit in a single gesture. Now about five points, with a per-event cap so
  one outsized delta cannot jump several.
- **A dropped `EndNativeGesture` disabled Ctrl+wheel zoom for the session.**
  **[macOS]** A pinch idle for half a second is now treated as finished.

### Verified, not changed

Cursor hit testing was measured before anything was touched and is correct — no
layout code was changed. Every block painted in the viewport was located by its
own painted geometry and clicked at its centre: clean across 30 configurations
of wrap, line spacing and scroll offset, on both the offscreen plugin and real
Cocoa, with 0 of 248 ASCII caret positions mis-mapped. The only mismatches are
inside Tamil grapheme clusters, which is correct Unicode snapping.

### Added

- `tests/test_input_gestures.py` — 25 checks covering wheel and pinch
  accumulation and the triple-click rules. Nine fail on the pre-fix code.

### Infrastructure

- **`buildme_mac_app.sh`'s clean step now removes both PyInstaller outputs.**
  It previously removed `dist/Neight.app` but not `dist/Neight` — the COLLECT
  directory the spec also writes — and PyInstaller refuses to reuse a
  non-empty output directory, so every rebuild after the first failed outright
  with "the output directory is not empty."

---

## 2026.070 — 2026-07-27

The first run of the project on real Apple hardware, plus a large Windows-side
correctness pass. Detail in
[`knownbugs/MACOS-VALIDATION-RESULTS.md`](knownbugs/MACOS-VALIDATION-RESULTS.md).

### Fixed — text integrity

These two silently altered your files and are the most important entries here.

- **Every save destroyed no-break spaces.** **[Both]** `QTextDocument.toPlainText()`
  substitutes ASCII lookalikes for a few characters, so U+00A0 came back as an
  ordinary space. All three disk-write paths and three whole-document transforms
  read the document that way, so opening a file containing NBSP — common in
  anything pasted from a web page — and saving it replaced every one,
  permanently and with no indication.
- **BOM-less UTF-16 / UTF-32 files opened as garbage.** **[Both]** ASCII encoded
  as UTF-16 decodes perfectly well as UTF-8, leaving a NUL between every
  character, so the file opened looking like `H e l l o`.
- **A UTF-8 BOM no longer survives as a stray U+FEFF first character.** **[Both]**
- **UTF-32 is now tested before UTF-16**, which otherwise decoded it into
  garbage. **[Both]**
- Encoding, BOM and newline are detected on open and any conversion is announced
  in the status bar and shown in Debug Info. Neight normalises on save to UTF-8
  without BOM and the platform newline — previously silent. **[Both]**

### Fixed — settings

- **A second window came up with the default font instead of the assigned one.**
  **[Both]** Applying settings synchronised checkable menu actions without
  blocking their signals, so every launch transiently rewrote `settings.json`
  with Qt's default font. With one window a later save repaired it; with two
  processes, whichever read during that window lost the font. Measured before:
  one startup rewrote the font family and dropped the size from 14 to 9. After:
  startup writes nothing.
- **Settings no longer live inside the app bundle.** **[macOS]** They were
  written beside the executable, which on macOS is *inside* `Neight.app` — so
  every update destroyed them. They now live in
  `~/Library/Application Support/Neight/settings.json`, migrated once from the
  bundle or `~/.config/Neight`, copying and never deleting. Windows keeps its
  portable, next-to-the-executable behaviour.
- **Windows that no longer clobber each other.** **[Both]** A lock file around
  the read-modify-write plus key-level merging, so a window writes only what it
  changed and cannot revert another window's font or margins. Unknown keys are
  preserved.
- **Saved presets no longer reset settings they predate.** **[Both]** Seventeen
  preset-loadable keys now fall back to the current in-memory value rather than
  a hardcoded literal.
- Settings write failures are surfaced once and in Debug Info instead of the
  store being silently relocated. **[Both]**

### Fixed — saving

- One durable atomic-write helper for every path: unique temp, write, flush,
  fsync, `os.replace`. Manual save previously skipped flush and fsync, making it
  *less* durable than autosave, and shared a temp name with the autosave worker.
  **[Both]**
- **Save As is transactional** — document identity commits only after a
  successful write. **[Both]**
- A hung save worker can no longer overwrite newer content: save generations are
  checked immediately before the rename. **[Both]**

### Fixed — macOS specifics

- **The built app reported version `0.0.0`.** The macOS PyInstaller spec set
  neither `CFBundleShortVersionString` nor `CFBundleVersion`, so every release
  would have shipped claiming to be version zero — which also breaks update
  comparison. The spec now reads `VERSION` out of `neight.py` at build time.
- **The status bar rendered all text in a Tamil font.** Tamil Sangam MN was set
  as the sole family, so `Words: 0`, `Ln 1` and `Col 1` used its Latin glyphs
  instead of the system UI font. Now a fallback stack, so only Tamil runs pick up
  the Tamil face.
- **Slow trackpad zoom did nothing.** `int(delta / 120)` with a `pixelDelta`
  fallback gated on `delta == 0` meant a small non-zero `angleDelta` — normal
  smooth-trackpad output — produced no zoom *and* was still accepted, so
  Ctrl+trackpad neither zoomed nor scrolled.

### Fixed — Markdown and rendering

- **Code blocks were never highlighted.** **[Both]** `codehilite` had been
  requested all along but Pygments was never installed or bundled, so the
  extension was a silent no-op in both preview and exported PDFs. Pygments is now
  a pinned runtime dependency and its style definitions are injected into the
  generated CSS, following the light/dark branch so code is never rendered
  dark-on-dark.
- **Export Markdown to PDF flattened lists.** **[Both]** An ordered list
  immediately followed by a bulleted one was merged into a single `<ol>`. Fixed
  by adding `sane_lists`.
- Task list markers now render as check boxes in every list shape. **[Both]**

### Added

- **Split-view Markdown preview** (`Ctrl+Shift+M` / `⌘⇧M`) with an adjustable
  divider that is remembered, live 300 ms debounced rendering, and an on-demand
  mode above 200,000 characters so a large document cannot stall the UI. One
  renderer now serves both preview and PDF export, so the two cannot drift.
  **[Both]**
- **`.md` and `.markdown` file associations.** **[Both]** Windows registers them
  under their own ProgID so Explorer shows "Markdown Document"; because Windows
  has hash-protected the default-handler choice since Windows 8, the dialog says
  so plainly and links to the Default Apps page rather than pretending to
  succeed. macOS can set the handler via Launch Services, and Debug Info offers
  to switch it.
- **macOS pinch-to-zoom**, with wheel suppression so one gesture cannot zoom
  twice.
- A committed regression suite in `tests/`, run in CI on Windows and macOS.

### Infrastructure

- **CI had never been green.** On Windows the startup font guard was an inline
  heredoc, which PowerShell — the default shell on that runner — cannot parse, so
  that half of the matrix had failed before running a single check since the
  workflow was written. On macOS the guard wrote to a path that stopped being the
  settings store, so it passed while testing nothing. Both fixed; all four jobs
  pass.
- **Release binaries removed from Git.** `dist/` and `stable/` held 127 MB of
  committed binaries, 2.68 GB across history. Downloads now point at
  `releases/latest/download/`. Nothing was lost — every binary was already
  published to GitHub Releases.
- Dependencies pinned and upgraded: PySide6 / shiboken6 6.11.1, PyInstaller
  6.21.0, Pillow 12.3.0, plus a missing `python-pptx` pin. Both platforms are now
  on the same Qt version.

---

## Known limitations

Carried forward, with reasons, in
[`knownbugs/MACOS-VALIDATION-RESULTS.md`](knownbugs/MACOS-VALIDATION-RESULTS.md):

- **Pinch-zoom calibration** has never been checked against a real trackpad. The
  arithmetic is test-covered and the magnitude is sane; the feel is not verified.
- **Bottom-line snapping is approximate for mixed-script documents** — block
  heights differ between scripts, so a partial line can peek at the bottom. It is
  cosmetic and no positional disagreement was found.
- **Tamil text navigation in Qt** has a segmentation quirk for some consonant +
  pulli + consonant combinations. This is Qt-level, not specific to Neight.
- **Drag and drop from Finder** is not implemented. **[macOS]**
- **Tamil/English keyboard switching** and **`.md` associations** still need
  manual verification on real hardware. **[macOS]**
