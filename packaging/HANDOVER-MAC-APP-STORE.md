# Neight 2026.083 — handover for Mac App Store signing and submission

**For:** whoever signs and submits Neight to the Mac App Store.
**From:** the Neight repository, <https://github.com/venkatarangan/neight>.
**Date:** 2026-08-22.

You have been sent an **unsigned** `Neight.app` bundle. This document is
everything needed to sign it, submit it, and confirm afterwards that the right
thing shipped. It is self-contained — you do not need to read the rest of the
repository.

If you read only one section, read
[The one entitlement that matters](#the-one-entitlement-that-matters). The
previous Store release could not open a single file, and that key is the fix.

---

## What you are signing

| | |
|---|---|
| **Version** | 2026.083 |
| **Bundle identifier** | `com.murasu.neight` |
| **Architecture** | Apple Silicon (arm64) only — deliberately no Intel or universal slice |
| **Minimum macOS** | 15.0 (Sequoia) |
| **Artifact** | `Neight-mac-arm64-unsigned.app.zip`, 41 MB |
| **SHA-256** | `54cc0edc41e18db028aeb802df22cebcb81dabab37384057df81170a8bba6d34` |

Download it directly if you would rather not use the file you were sent:

```
https://raw.githubusercontent.com/venkatarangan/neight/dist-latest/dist/Neight-mac-arm64-unsigned.app.zip
```

Verify before you start — if this hash does not match, stop and ask, because the
`dist-latest` branch is force-pushed on every build and may have moved on:

```bash
shasum -a 256 Neight-mac-arm64-unsigned.app.zip
ditto -x -k Neight-mac-arm64-unsigned.app.zip .
```

The bundle currently carries an **ad-hoc** signature and **no entitlements**.
That is correct for the direct download it also serves as. Your signing replaces
that signature entirely.

---

## The one entitlement that matters

**Sign with `packaging/Neight.entitlements`, included alongside this document.**

```bash
codesign --force \
         --sign "3rd Party Mac Developer Application: <NAME> (<TEAMID>)" \
         --entitlements Neight.entitlements \
         Neight.app
```

Its four keys, and why each is there:

| Key | Why |
|---|---|
| `com.apple.security.app-sandbox` | Required for the Store. |
| `com.apple.security.files.user-selected.read-write` | Read and write the files the user picks in the Open and Save panels. |
| `com.apple.security.files.bookmarks.app-scope` | **Mint and redeem security-scoped bookmarks. Nothing works without this.** |
| `com.apple.security.files.bookmarks.document-scope` | Bookmarks tied to a document rather than to the app. |

### Why `app-scope` is not optional

The Store release before this one **could not open any file at all** — Desktop,
Downloads, Dropbox, OneDrive, anywhere — failing with *Operation not permitted*
for every user.

The cause: macOS grants access when the user picks a file in the Open panel, but
that grant was gone a few milliseconds later when Python actually read the
bytes. (A `stat()` on the path still succeeded in that window, because the
sandbox treats reading a file's *metadata* and reading its *contents* as
separate permissions — which is why it looked for a long time like a bad path
rather than a lost permission.)

Neight now mints a **security-scoped bookmark** the instant the panel returns
and redeems it around every read and write. That call is
`NSURL.bookmarkDataWithOptions:`, and **without
`com.apple.security.files.bookmarks.app-scope` it returns nil** — silently. The
app would then behave exactly as the broken release did, and the fix would have
cost a review cycle to discover.

So: if the entitlements file is not passed to `codesign`, this submission is
pointless. That is the single highest-risk step in this handover.

### What is deliberately absent

No `com.apple.security.temporary-exception.files.*` of any kind. A blanket
home-directory exception does make the symptom disappear — the read stops
needing a scoped grant — but it asks App Review to grant a text editor standing
access to the user's entire home directory. Please do not add one to get a
build through.

---

## Rules for handling the bundle

- **Do not edit anything inside the bundle**, `Info.plist` included. Every key
  is set at build time from a version-controlled spec. If a shipped bundle turns
  out to carry a key this repository never sets, something in the signing chain
  added it, and that needs explaining rather than accepting. This has happened
  before (see the question about 2026.081 below).
- **Do not use `--deep`.** Apple deprecated it, and it signs nested code with
  the *outer* bundle's options — wrong for anything carrying entitlements.
  `codesign` walks the bundle correctly without it.
- **`--options runtime` (hardened runtime) is not needed.** That is for
  notarised direct distribution, not the Store.
- **Do not re-zip with `zip`.** Use `ditto -c -k --sequesterRsrc --keepParent`,
  which preserves the symlinks and resource forks a `.app` depends on.

---

## Verifying before you submit

```bash
# 1. The entitlements actually made it in -- this is the check that matters.
codesign -d --entitlements :- Neight.app

# 2. The signature is valid and covers nested code.
codesign --verify --strict --verbose=2 Neight.app

# 3. Identity and architecture.
codesign -dvv Neight.app 2>&1 | grep -E 'Authority|TeamIdentifier|Format'
```

Expected: step 1 lists all four keys above, `app-scope` among them. `Format`
reads `app bundle with Mach-O thin (arm64)`.

A genuine Store install, once delivered back through Apple, shows
`Apple Mac OS Application Signing` as the authority, has
`Contents/_MASReceipt/receipt`, and has **no** `embedded.provisionprofile` —
Apple strips it when re-signing.

---

## Testing that the fix works

The file-open fix **cannot be tested in an unsigned build**. It only does
anything inside a sandboxed, entitled, signed one — which is why the request
below is worth more than everything else in this document combined.

Once you have a signed build, on a Mac that is not the build machine:

1. Launch Neight.
2. **File > Open**, and open a `.txt` file on the Desktop. It must open and show
   its contents. Previously this failed with *Operation not permitted*.
3. Open a file inside OneDrive or Dropbox — those go through a different macOS
   mechanism and are worth checking separately.
4. Edit it, **File > Save**. The save must succeed.
5. Quit and relaunch. If **Reopen last file on launch** is enabled, the same
   file must come back — that path depends on the bookmark surviving a restart,
   which is the other half of the fix.

If any step fails, capture this and send it back — it names the exact denial:

```bash
log stream --predicate 'eventMessage CONTAINS[c] "com.murasu.neight"' --info
```

Note `CONTAINS[c]`. The case-sensitive form misses `com.murasu.neight` entirely,
and an earlier investigation lost time concluding from its silence that there
was no denial at all.

---

## What would help most, coming back

In order of value:

1. **A locally signed test build** — same entitlements, same commands as a real
   submission, sent back rather than uploaded. Sandbox behaviour cannot be
   reproduced from an unsigned build, so without this every hypothesis costs a
   full App Store review cycle to test. With it, minutes. This is the single
   most useful thing.
2. **The signing commands verbatim** — every `codesign` invocation with all
   flags, in order; whether nested code is signed inside-out or only the outer
   `.app`.
3. **Anything you modify in the bundle before signing.** 2026.081 shipped with
   `LSMinimumSystemVersion = 12.0` in its `Info.plist` while the spec that built
   it never set that key at all — so something in the chain was editing the
   bundle. Still unexplained, and worth settling.
4. **Which artifact and version you submitted**, plus your macOS and Xcode
   versions.

---

## Already ruled out — please don't re-investigate

Time was spent on each of these; all are settled:

- The delivered entitlements were correct **as far as they went** — the previous
  release genuinely had `app-sandbox` and `files.user-selected.read-write`. What
  was missing was the bookmarks key.
- The app really does invoke the **native** Open panel:
  `com.apple.appkit.xpc.openAndSavePanelService` runs with
  `responsible=com.murasu.neight`. Qt's non-native dialog was never involved.
- There is **no path rewriting** between the panel returning and the read.
- The denial is a kernel **App Sandbox `deny(1) file-read-data`**, not TCC.
  Privacy settings are not the problem.
- An earlier analysis inferred an unbalanced
  `stopAccessingSecurityScopedResource()` in Neight and recommended removing it.
  **No such call existed** — the app had no bookmark code at the time. The
  bookmark activity visible in that trace was AppKit's own.

---

## Context you may want

- **This version's other change.** 2026.083 differs from 2026.082 only in the
  interpreter that built it. 2026.082 could be installed only on macOS 26,
  because Homebrew's Python is compiled for whatever macOS is running it and 57
  of the bundle's binaries were CPython's own. Rebuilt with a python.org
  interpreter, the floor drops to 15.0 — the limit PySide6 6.11 sets. No source
  changed.
- **The app makes no network calls on its own.** It never checks for updates or
  contacts a server unless the user clicks something. Worth knowing if App
  Review asks.
- **Neight is a Tamil and English text editor**, PySide6 (Qt 6) on Python 3.14,
  single-window, document-based. It declares plain-text and Markdown document
  types so it appears in Finder's **Open With**.
- **Full reference:** `packaging/MAC-APP-STORE-SIGNING.md` in the repository,
  which this document condenses.

Questions are welcome and cheaper than a rejected submission.
