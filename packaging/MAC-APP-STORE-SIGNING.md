# Mac App Store signing

Signing and submission for the macOS build happen on **someone else's machine**.
This repository produces an unsigned bundle; another person signs it with an
Apple Developer identity and uploads it. That split is why the sandbox was
impossible to reason about from the source for so long, and this file exists to
close the gap.

> **Handing a build over?** Send
> [`HANDOVER-MAC-APP-STORE.md`](HANDOVER-MAC-APP-STORE.md) and
> [`Neight.entitlements`](Neight.entitlements) with it. That document is the
> self-contained version of this one, written for someone who does not have the
> repository, and it carries the current version's artifact hash. This file is
> the internal reference behind it — keep them in step.

## What this repository provides

[`Neight.entitlements`](Neight.entitlements) is the source of truth for the
sandbox entitlements. Sign with it:

```bash
codesign --force --sign "3rd Party Mac Developer Application: <NAME> (<TEAMID>)" \
         --entitlements packaging/Neight.entitlements \
         Neight.app
```

It declares four keys:

| Key | Why |
|---|---|
| `com.apple.security.app-sandbox` | Required for the Store. |
| `com.apple.security.files.user-selected.read-write` | Read and write files the user picks in the Open and Save panels. |
| `com.apple.security.files.bookmarks.app-scope` | **Mint and redeem security-scoped bookmarks.** Neight does not work without this — see below. |
| `com.apple.security.files.bookmarks.document-scope` | Bookmarks tied to a document rather than to the app. |

`app-scope` is not optional. Without it `NSURL.bookmarkDataWithOptions:` returns
nil, and the entire mechanism Neight uses to keep access to a file the user
picked does nothing at all. This was added in 2026.082, and 2026.083 is the
first build that can actually be installed widely enough to prove it — 2026.082
required macOS 26.

Deliberately **absent**: any `com.apple.security.temporary-exception.files.*`
entitlement. A blanket home-directory exception does make the file-open failure
go away, because the read stops needing a scoped grant — but it asks App Review
for standing access to the user's home directory to run a text editor.

## Never edit the bundle by hand

Everything the app needs is set by `Neight.macos.spec` at build time, including
`LSMinimumSystemVersion`, which `buildme_mac_app.sh` then corrects to the value
the binaries actually require. If a shipped bundle carries an `Info.plist` key
this repository never sets, something in the signing chain added it and that
needs explaining, not accepting.

`--deep` is deprecated by Apple and signs nested code with the *outer* bundle's
options, which is wrong for anything carrying entitlements. Do not use it.
`codesign` walks the bundle correctly without it. Hardened runtime
(`--options runtime`) is for notarised direct distribution and is not needed for
the Store.

## Verifying a signed bundle

The only thing that counts is what the delivered binary carries:

```bash
codesign -d --entitlements :- /Applications/Neight.app
codesign --verify --strict --verbose=2 /Applications/Neight.app
codesign -dvv /Applications/Neight.app | grep -E 'Authority|TeamIdentifier|Format'
```

A genuine Store install shows `Apple Mac OS Application Signing` as the
authority, has `Contents/_MASReceipt/receipt`, and has **no**
`embedded.provisionprofile` — Apple strips it when re-signing for delivery.
`Format` must read `app bundle with Mach-O thin (arm64)`; Neight is Apple
Silicon only by design.

## What to ask the signer for

Kept here because it will be needed again. As of 2026.083 these are still
outstanding, in order of value:

1. **A locally signed test build**, using the same entitlements and the same
   commands as a submission, sent back rather than uploaded. This is worth more
   than everything else combined: the sandbox behaviour cannot be reproduced
   from an unsigned build, so without it every hypothesis costs a full App Store
   review cycle to test. With it, minutes.
2. **The signing commands verbatim** — every `codesign` invocation with all
   flags, in order; whether `--deep` or `--options runtime` are used; whether
   nested code is signed inside-out or only the outer `.app`.
3. **What they modify in the bundle before signing.** 2026.081 shipped with
   `LSMinimumSystemVersion = 12.0` in its `Info.plist` while the spec that built
   it never set that key, so something in the chain was editing the bundle.
   Worth settling.
4. **Which artifact and version they submitted**, plus their macOS and Xcode
   versions.

Ruled out already, so nobody repeats it: the delivered entitlements were correct
as far as they went; the app really does invoke the native panel
(`com.apple.appkit.xpc.openAndSavePanelService` runs with
`responsible=com.murasu.neight`); the app-side code is a plain
`QFileDialog.getOpenFileName()` with no options and no path rewriting; and the
denial is a kernel App Sandbox `deny(1) file-read-data`, not TCC.
