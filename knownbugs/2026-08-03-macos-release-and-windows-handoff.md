# macOS 2026.077 release done — read this before touching Windows release

Date: 2026-08-03
Context: Mac session signed and shipped v2026.077. This is the handoff for
whoever (Claude or the maintainer) runs the Windows build/release next.

## What happened on the Mac side

1. `buildme_mac_app.sh` had already been run earlier (bumped `VERSION` to
   `2026.077`, produced `dist/Neight.app` ad-hoc signed + `dist/Neight-mac-arm64-unsigned.app.zip`).
2. The maintainer signed and notarized that build externally (Developer ID:
   Muthu Nedumaran, F7UG2X3VU8) and handed back `dist/2026-08-03.zip`, which
   contained `Neight-mac-arm64-signed.zip` (a zip-inside-a-zip).
3. I verified before shipping anything:
   - `codesign -dvv` → `Authority=Developer ID Application: Muthu Nedumaran`,
     `Notarization Ticket=stapled`.
   - `spctl -a -vv --type execute` → `accepted`, `source=Notarized Developer ID`.
   - `xcrun stapler validate` → passed.
   - `Info.plist` `CFBundleShortVersionString` → `2026.077`, matching the
     committed `VERSION` in `neight.py`.
4. Committed the version bump (`eab3327`, `VERSION = "2026.077"`) and pushed
   to `main`.
5. Copied the verified zip to `stable/Neight-mac-arm64-signed.zip` (this
   overwrote a **stale** zip that had been sitting there since Jul 29 —
   double-check `stable/` isn't holding old bytes before you trust it blindly
   next time; it's gitignored so nothing about it is enforced by git).
6. Ran `./release_macos.sh`. It created tag `v2026.077` and a **new** GitHub
   Release "Neight 2026.077" containing only the signed mac zip.
   → https://github.com/venkatarangan/neight/releases/tag/v2026.077
   → It is now the "Latest" release, superseding `v2026.065` (which was the
     previous Latest — there's a gap; `v2026.073`/`.075`/`.076` tags exist
     from earlier sessions but were never fully released or had assets
     removed — not something this session touched or needs to fix).

## Important: a stale Windows exe was sitting in dist/ — I did NOT release it

`dist/Neight.exe` (53,239,402 bytes) was present going into this session. Its
sha256 is byte-identical to what's published on the `dist-latest` branch, i.e.
it's the unsigned-build-handoff artifact from an **earlier, already-superseded**
build — not something built for 2026.077. `release_macos.sh` auto-uploads
`dist/Neight.exe` to whatever release it's creating if the file happens to
exist, with no version check. Left in place, it would have been silently
attached to the v2026.077 release under the wrong version.

I moved it aside rather than deleting it:
`dist/Neight.exe.stale-2026.076-pre-077`

You can ignore/delete that file — it'll be replaced by a fresh Windows build
anyway.

## The real gotcha for the Windows run: version-bump collision

Both `buildme_mac_app.sh` and `buildme.bat` **unconditionally** call
`increment_version.py` before building — there's no "build without bumping"
mode. `release_macos.sh` / `release_windows.ps1` both read `VERSION` from
whatever is currently **committed** and target `v<that VERSION>` as the
release tag, uploading to an existing release if the tag already exists.

`main` right now has `VERSION = "2026.077"` committed (the mac release tag).
If you just run `buildme.bat` as usual on Windows, it will bump this to
`2026.078`, and `release_windows.ps1` will create a **brand-new, separate**
`v2026.078` release containing only the Windows exe — `stable/` is
gitignored, so the Windows machine won't have today's mac zip locally, and it
will just skip the "upload mac artifact" step. You'd end up with two
half-populated releases (`v2026.077` mac-only, `v2026.078` Windows-only)
instead of one release with both platforms — this is exactly the kind of
split that happened in earlier sessions (see `v2026.073`'s 404'd mac asset).

You have two options — **pick one with the maintainer, don't just guess**:

- **Option A — land Windows in the same v2026.077 release:** `git pull` to
  get the committed `2026.077`, build the Windows executable **without**
  letting the version bump (e.g. run PyInstaller directly against
  `packaging/`'s Windows spec instead of `buildme.bat`, or run `buildme.bat`
  and then `git checkout -- neight.py` to discard its version bump before
  committing/releasing). Then run `release_windows.ps1` — since `v2026.077`
  already exists as a release, it will just upload `Neight.exe` into it.
  Result: one release, both platforms, no version confusion.

- **Option B — let Windows advance to its own version:** run `buildme.bat`
  normally (bumps to `2026.078`), commit/push that bump, run
  `release_windows.ps1` (creates `v2026.078`, Windows-only). Then separately
  copy today's already-verified `stable/Neight-mac-arm64-signed.zip` onto the
  Windows machine (or just re-run `gh release upload v2026.078 <path-to-mac-zip>`
  from anywhere authenticated) so `v2026.078` ends up with both assets too,
  and treat `v2026.077` as a mac-only intermediate release.

I'd lean towards **Option A** since it keeps one release per shipped version
instead of the fragmented history this repo already has, but it's the
maintainer's call.

## Website macOS download link was also broken — now fixed, plus a CI guard

Separately, `https://neight.app/#install-mac` turned out to be broken: both
`docs/index.html` and `README.md` hardcoded the macOS download link to
`releases/download/v2026.073/Neight-mac-arm64-signed.zip` — the exact release
whose asset went missing (see the "gap" note above). That 404 was already a
known open item from the July session notes and had never been fixed.

Fixed in `602fc84`: both links now use
`releases/latest/download/Neight-mac-arm64-signed.zip`, the same pattern the
Windows link already used. This makes the link self-updating — it always
resolves to whatever the current "Latest" release is, so it doesn't need a
manual edit on every version bump.

That said, the link is only as good as the release it points at: it 404s for
a platform whenever the Latest release is missing that platform's asset —
which is exactly the situation right now (`v2026.077` is macOS-only). To
catch that automatically, `f087d09` added
`.github/workflows/release-assets-check.yml`: it checks the Latest release
for both `Neight.exe` and `Neight-mac-arm64-signed.zip`, running daily, on
`workflow_dispatch`, and best-effort on `release: published`. It fails loudly
(GitHub notifies on workflow failure) with a message naming exactly which
asset is missing and which script to run to fix it.

**This check is currently red** — expected, since `v2026.077` has no Windows
exe yet. It'll go green as soon as `release_windows.ps1` (Option A above)
attaches `Neight.exe` to the release Windows lands in. If it's still red
after the Windows release, that's a real signal something didn't attach
correctly — check it:
https://github.com/venkatarangan/neight/actions/workflows/release-assets-check.yml

## Current repo state (as of this commit)

- `main` @ `f087d09`, `VERSION = "2026.077"`, pushed, tag `v2026.077` exists.
- GitHub Release `v2026.077` = Latest, asset: `Neight-mac-arm64-signed.zip`
  only (47,449,521 bytes, notarized). Windows asset still missing — see above.
- `stable/Neight-mac-arm64-signed.zip` locally = today's verified 2026.077
  build (gitignored, this Mac only).
- `dist/Neight.exe.stale-2026.076-pre-077` = old unreleased Windows build,
  safe to delete.
- `dist/2026-08-03.zip`, `dist/Neight-mac-arm64-unsigned.app.zip`,
  `dist/Neight.app`, `dist/Neight` — leftover build artifacts from this
  session, all gitignored, safe to clean up whenever.
- `docs/index.html` and `README.md` macOS download links fixed to track
  Latest instead of the dead `v2026.073` tag.
- `.github/workflows/release-assets-check.yml` added — daily + on-demand +
  release-publish check that both platform assets exist on the Latest
  release.
