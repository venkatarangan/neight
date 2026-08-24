# Mac App Store signing

Signing and submission for the macOS build happen on **someone else's machine**.
This repository produces an unsigned bundle; another person signs it with an
Apple Developer identity and uploads it. That split is why the sandbox was
impossible to reason about from the source for so long, and this file exists to
close the gap.

**Neight is live and current on the Mac App Store**: [`id6800348235`](https://apps.apple.com/app/neight/id6800348235?mt=12), published under
Muthu Nedumaran's account. **2026.086**, signed and live as of 2026-08-24, is
the first build carrying the complete sandboxed file I/O fix: reads and writes
now route through Qt (see the 2026-08-23 session notes), fixing both the
file-open failure that 2026.083/2026.084's bookmark-based attempt never solved,
and the separate save failure caused by `QSaveFile` being unable to open a file
inside the sandbox at all. The earlier `LSMinimumSystemVersion = 12.0` /
macOS-26-binaries mismatch is also resolved — the signer's script was
overwriting the declared 15.0, fixed on their side.

Note also that the repository stamps `CFBundleShortVersionString` with Neight's
own version, yet the listing reads `1.0` — so something in the signing chain
changes it. That is an open question, not a settled fact.

> **Asking for a diagnostic run instead of a submission?**
> [`SIGNER-DIAGNOSTIC-RUN.md`](SIGNER-DIAGNOSTIC-RUN.md) is the template — it
> was sent for 2026.084 and answered on 2026-08-23, and that run found the root
> cause. One claim in it is now known to be wrong: Powerbox **does** vend file
> grants to an app with no provisioning profile, as long as it carries a real
> Apple signature (Developer ID or Apple Development). A local identity is
> therefore enough to reproduce sandbox behaviour here; only ad-hoc signatures
> are denied at the panel. The diagnostic mode (`NEIGHT_SANDBOX_DIAG=1`)
> remains in every build, off by default.

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
| `com.apple.security.files.bookmarks.app-scope` | **Mint and redeem security-scoped bookmarks.** Qt's file engine needs this — see below. |
| `com.apple.security.files.bookmarks.document-scope` | Bookmarks tied to a document rather than to the app. |

`app-scope` is not optional, but the consumer is not Neight's own code: since
the Qt I/O fix, **Qt's security-scoped file engine** is what mints a bookmark
from every Open/Save panel grant, stores it in
`SecurityScopedBookmarks.plist` inside the container, and redeems it on later
access — including after a relaunch, which is what keeps "continue where you
left off" working. Without the entitlement `bookmarkDataWithOptions:` returns
nil and access dies with the panel.

Deliberately **absent**: any `com.apple.security.temporary-exception.files.*`
entitlement. A blanket home-directory exception does make the file-open failure
go away, because the read stops needing a scoped grant — but it asks App Review
for standing access to the user's home directory to run a text editor.

## Never edit the bundle by hand

Everything the app needs is set by `Neight.macos.spec` at build time, including
`LSMinimumSystemVersion`, which `buildme_mac_app.sh` then corrects to the value
the binaries actually require. If a shipped bundle carries an `Info.plist` key
this repository never sets, something in the signing chain added it and that
needs explaining, not accepting. This has happened once and is settled: the
`LSMinimumSystemVersion = 12.0` on the live listing was the signer's script
overwriting the declared 15.0 — fixed on their side on 2026-08-23, along with a
stray `--options runtime` that a Store build does not need.

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

Kept here because it will be needed again. Updated after the 2026-08-23
diagnostic round, which resolved most of the original list:

1. ~~A locally signed test build~~ — **done** (2026.084, 2026-08-23). Better
   still, that run established that a plain Developer ID or Apple Development
   signature with no provisioning profile is enough for Powerbox to vend
   grants, so any Apple developer identity reproduces sandbox behaviour
   locally. The standing ask, if local reproduction is ever wanted here: an
   export of the `Apple Development: Muthu Nedumaran (GQ3UG4GVPW)` identity,
   which Muthu already holds.
2. **The signing commands verbatim** — answered for 2026.084: nested code
   signed inside-out, no `--deep`, nothing edited by hand,
   `codesign --verify --strict` passing. Keep asking whenever the procedure
   changes.
3. ~~What they modify in the bundle before signing~~ — **settled**: their
   script overwrote `LSMinimumSystemVersion` (source of the 12.0 on the live
   listing) and applied `--options runtime`; both fixed on their side.
4. **Which artifact and version they submitted**, plus their macOS and Xcode
   versions — still worth recording with every submission.

Ruled out already, so nobody repeats it: the delivered entitlements were correct
as far as they went; the app really does invoke the native panel
(`com.apple.appkit.xpc.openAndSavePanelService` runs with
`responsible=com.murasu.neight`); the app-side code is a plain
`QFileDialog.getOpenFileName()` with no options and no path rewriting; and the
denial is a kernel App Sandbox `deny(1) file-read-data`, not TCC.
