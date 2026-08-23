# Neight 2026.084 — diagnostic run results

> **Redacted for the public repository:** the signer's local macOS account
> name has been replaced with `[signer]` throughout (it appeared only in
> sample file paths — `/Users/[signer]/Dropbox/…`, `/Users/[signer]/Desktop/…`
> — and carries no other information). Everything else, including the
> analysis, the log excerpts, and the signer's own name where it appears in
> signing-identity strings, is unchanged from what was received on
> 2026-08-23.

**Date:** 2026-08-23, 18:20 (+08)
**Machine:** macOS 26.5.2, Apple silicon
**Build tested:** 2026.084, SHA-256 `fa6fb9a9…a9bb6` — matches the hash in your document
**Attachment:** `sandbox-diagnostics-2026.084.txt`

---

## Summary

The diagnostic run worked exactly as you designed it, and it found something
neither of us expected.

**Powerbox is vending the grant. Qt is absorbing it before Neight can use it.**

At the same second Neight's `open()` was denied on a file, QtCore successfully
minted a security-scoped bookmark for that same file and wrote it to its own
plist inside Neight's container. Access existed. It just never reached your code.

This is upstream of the whole bookmark mechanism. The machinery added in
2026.082/083/084 cannot work as written, because it begins from an access that
Qt has already taken.

The `grant:` line you flagged as the alarming outcome is the one that fired.

---

## What was run

Signed locally, as requested, with the entitlements file that shipped with the
build:

```
codesign --force --timestamp=none --entitlements Neight.entitlements \
         -s "Developer ID Application: Muthu Nedumaran (F7UG2X3VU8)" Neight.app
```

Nested code (dylibs, .so, frameworks) signed first, inside-out, no `--deep`,
nothing edited by hand inside the bundle. `codesign --verify --strict` passes and
the bundle satisfies its designated requirement.

`codesign -d --entitlements -` confirms all four keys on the signed bundle:

```
com.apple.security.app-sandbox                      => true
com.apple.security.files.user-selected.read-write   => true
com.apple.security.files.bookmarks.app-scope        => true
com.apple.security.files.bookmarks.document-scope   => true
```

Note this is a **Developer ID** identity, not `3rd Party Mac Developer
Application` — see "Two corrections to your document" below, because this turns
out to matter to you.

Two runs, both opening the files through **File › Open**:

| Run | Launch method | `APP_SANDBOX_CONTAINER_ID` | Files opened |
|---|---|---|---|
| 18:17 | Terminal, direct exec | present (set by the OS) | Dropbox ×2, Desktop ×1 |
| 18:20 | LaunchServices (`open`), var forced on | forced | Desktop, Dropbox |

Both runs failed identically. Both logged `sandboxed=True`.

---

## The decisive evidence

The log says the Open panel granted nothing:

```
18:20:20.635  grant: NO panel access for /Users/[signer]/Dropbox/sample.txt (PermissionError(1, 'Operation not permitted'))
18:20:20.636  mint: FAILED for /Users/[signer]/Dropbox/sample.txt — bookmarkDataWithOptions returned nil (NSCocoaErrorDomain/256: The file "sample.txt" couldn't be opened.)
18:20:20.636  access: no scoped grant attempted for /Users/[signer]/Dropbox/sample.txt (sandboxed=True, bookmark=MISSING)
18:20:20.637  read: DENIED on /Users/[signer]/Dropbox/sample.txt
```

But in the same container:

```
~/Library/Containers/com.murasu.neight/Data/Library/Application Support/SecurityScopedBookmarks.plist
  modified 18:20:20
  "/Users/[signer]/Desktop/dt_sample.txt"  => 784 bytes, magic 'book'
  "/Users/[signer]/Dropbox/sample.txt"     => 780 bytes, magic 'book'
```

Written at **18:20:20** — the same second as the denial above, keyed by the exact
paths that were denied. That file is written by QtCore (established by an
exhaustive `strings` sweep over every binary in the bundle; QtCore is the sole
writer of that string).

So a security-scoped bookmark for that file was created successfully, from a live
access, at that instant — by Qt, not by Neight.

**The inference** (flagged as inference, not measurement): `QFileDialog` on macOS
consumes the Powerbox grant, converts it to a bookmark in its own store, and does
not leave a live process-wide grant behind. Neight then reads with Python's
`open()` / `read_bytes()`, which knows nothing about Qt's bookmark store, and gets
EPERM. `bookmarkDataWithOptions:` fails with NSCocoaErrorDomain 256 for the same
reason — by the time it runs there is no live access to mint from.

The measurements are certain; that mechanism is the reading that fits them. You
own this code and are better placed than I am to confirm it.

---

## Two faults, and their ranking

| # | Fault | Impact |
|---|---|---|
| 1 | Qt absorbs the Powerbox grant; Python `open()` is denied | **The actual bug.** Blocks file opening regardless of anything else |
| 2 | `_macos_is_sandboxed()` keys off `APP_SANDBOX_CONTAINER_ID` | Real, but secondary |

On fault 2 — the variable's presence depends on how the app is launched:

| Launch | `APP_SANDBOX_CONTAINER_ID` | `_macos_is_sandboxed()` |
|---|---|---|
| Terminal, direct exec | present | `True` |
| LaunchServices / double-click | **absent** | `False` |

Your docstring says "Set by the OS for every sandboxed process." That holds for
the Terminal case but not for a double-click — which is how every App Store user
will launch Neight. Under LaunchServices the whole mechanism silently disables
itself at its first line.

Worth fixing (`sandbox_check(getpid(), NULL, 0)` from
`libsystem_sandbox.dylib` is the supported probe; note `expanduser("~")` is not a
valid test, since the sandbox redirects the container while leaving `HOME`
unmodified). But **fixing it alone changes nothing.** The 18:20 run is the proof:
the variable was forced on, `sandboxed=True`, the code ran end to end, and the
file still failed.

No `sandbox-bookmarks.json` was ever created, in either run — consistent with
`macos_create_bookmark()` returning nil every time.

---

## A correction I owe you

After the last round I sent an analysis naming the `APP_SANDBOX_CONTAINER_ID`
check as *the* root cause. I had sampled only double-click launches and
generalised to "the variable is never set in a sandboxed process." That was
overstated, and your instrumentation caught it in its first run by printing
`sandboxed=True`.

The check is still a real bug. It is not the one that is breaking file opening.

That makes two of my hypotheses this week that the evidence has overturned — the
earlier unbalanced-`stopAccessingSecurityScopedResource` theory being the first,
which you correctly rejected. I am flagging the inference above accordingly.

---

## Two corrections to your document

**1. Powerbox does vend grants to an unprovisioned app.** Your document says it
"never vends a file grant to an unprovisioned app," and concludes you cannot
reproduce this locally. That is true of the *ad-hoc* signature you tested, but not
in general. The build in this run carries **no provisioning profile at all** —
`embedded.provisionprofile` was removed before signing — and Powerbox vended the
grant anyway, as the Qt bookmarks prove. A plain Developer ID signature is enough.

This matters because it means **you can reproduce this bug on your own machine**
with any Apple developer identity, and you no longer need a signing round trip to
work on it.

**2. The `grant: NO panel access` branch is live.** You wrote that if that line
appeared, "the problem is further upstream than anyone has assumed so far." It
appeared, in every single open, in both runs. Your instinct there was right — but
the cause is not that the panel is failing to grant. It is granting, and Qt is
taking it.

Separately: `log stream` will not help either of us here. Unified logging is
disabled machine-wide on this Mac, so a match-everything predicate returns zero
lines. Your diagnostic log was the only way to see any of this, which is why it
was worth doing.

---

## Where to look next

Three directions, all on Neight's side. Your call which is right:

- **Read through Qt.** Use `QFile` for the read path so Qt's own scoped-access
  handling applies, instead of Python `open()` / `Path.read_bytes()`.
- **Use the bookmark Qt already stored.** Qt has a valid, correctly-scoped
  bookmark for the file in `SecurityScopedBookmarks.plist` at the moment you need
  one. Resolving that may be simpler than minting your own.
- **Take the grant earlier.** If there is a point in the panel's lifetime where
  the live grant is still held, minting there would work — but this depends on Qt
  internals and looks the most fragile of the three.

Whichever you choose, the fix wants a test that exercises a **double-click
launch**, not a Terminal one — the two behave differently, as above.

---

## On the certificate

You offered the alternative of an Apple Development certificate and profile so
you can reproduce sandbox bugs locally. Muthu already holds an
`Apple Development: Muthu Nedumaran (GQ3UG4GVPW)` identity, so that route is
available if you want it.

Given the finding above, you may not need it — a Developer ID or Development
signature on your own machine reproduces this, and correction 1 means you were
blocked by a premise that does not hold rather than by anything real.

---

## Status

- **2026.084 has not been uploaded**, per your instruction that this is not a
  submission. Nothing has gone to App Review.
- 2026.083 was never submitted either.
- No `com.apple.security.temporary-exception.files.*` entitlement was added, and
  none will be.
- The next build needs a version bump: 2026.084 is now consumed as a diagnostic.

Signing-side items being fixed here, unrelated to this bug: our script was
overwriting your `LSMinimumSystemVersion` (you set 15.0; it forced 12.0, which
would have let macOS 12–14 users install an app that cannot run), and it was
applying `--options runtime`, which is unnecessary for a Store build. Both are
ours, not yours.
