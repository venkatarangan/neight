> **Superseded, kept as a record.** This request was answered on 2026-08-23:
> the signer ran 2026.084 twice and sent the log back, and it found the root
> cause — Qt's own security-scoped file engine consumes the Powerbox grant, so
> Python-level I/O never sees it. The fix (file I/O through Qt when sandboxed)
> is recorded in `session-notes/2026-08-23-qt-file-engine-fix.md`. One claim
> below is wrong and worth flagging: Powerbox **does** vend grants to an app
> with no provisioning profile, provided it carries a real Developer ID or
> Apple Development signature — only ad-hoc signatures are refused. Local
> reproduction is therefore possible with any Apple developer identity.

# Neight — a diagnostic run, before the next submission

**For:** whoever signs and submits Neight to the Mac App Store.
**From:** the Neight repository, <https://github.com/venkatarangan/neight>.
**Date:** 2026-08-23.

**This is not a submission.** Nothing here needs to go to App Review. It is a
request for one signed test build, run twice, and one small text file sent
back. It should take about fifteen minutes.

Thank you for the filesystem trace — it was decisive, and it is why this
document exists rather than another guess.

## Why we are asking you, and not doing it ourselves

The file-open fix shipped in 2026.082/2026.083 **does not work**. Your trace
showed why it could not be diagnosed from here: the app minted a security-scoped
bookmark, used the file successfully twice, and was then denied when it actually
read it, all within six milliseconds.

We tried hard to reproduce that locally before troubling you again, and we
cannot. An ad-hoc signature does carry the sandbox entitlements, and the sandbox
genuinely engages — but **Powerbox never vends a file grant to an unprovisioned
app**. On this machine the app is denied the file the instant the Open panel
closes, before any of the code we need to test has run. The failure happens one
step too early to tell us anything.

There is a second limit a trace cannot cross. A trace shows which system calls
happened; it cannot show what an API *returned*. The remaining question is
exactly that: when Neight redeems its bookmark, does macOS say yes or no? That
single value decides the fix, and only a properly signed build can answer it.

## What we need

Neight now has a diagnostic mode, off unless an environment variable is set. It
writes one line per step of the file-open path — including the two error objects
the code previously discarded — into a log inside the app's own container.

**Please sign a build as you normally would, run it with that variable set, open
two files, and send back the log.**

## Step 1 — sign as usual

> **Sign the bundle that came with this document, not the one on
> `dist-latest`.** Diagnostic mode does not exist in 2026.083, which is what
> that branch is still serving. A run of the wrong bundle produces no log at
> all and we would both have wasted the round trip.
>
> | | |
> |---|---|
> | **Version** | `2026.084` |
> | **Artifact** | `Neight-mac-arm64-unsigned.app.zip` |
> | **SHA-256** | `fa6fb9a9ad0555a73e3e3574fd5dce205b205763a96dd8b5a4c634843c7a9bb6` |
>
> ```bash
> shasum -a 256 Neight-mac-arm64-unsigned.app.zip
> ```

No change from the last handover. Sign the unsigned bundle with the entitlements
file that came with it:

```bash
codesign --force --sign "3rd Party Mac Developer Application: <NAME> (<TEAMID>)" \
         --entitlements Neight.entitlements \
         Neight.app
```

Then confirm the entitlements really are on the binary — this is the check that
matters most, because without `files.bookmarks.app-scope` the whole mechanism
returns nil and the run tells us nothing new:

```bash
codesign -d --entitlements - Neight.app
```

Expect all four keys: `app-sandbox`, `files.user-selected.read-write`,
`files.bookmarks.app-scope`, `files.bookmarks.document-scope`.

Reminders from last time, unchanged:

- **Do not use `--deep`.** It signs nested code with the outer bundle's options,
  which is wrong for anything carrying entitlements. `codesign` walks the bundle
  correctly without it.
- **Do not edit anything inside the bundle by hand.**
- **If you re-zip, use `ditto -c -k --keepParent`,** not `zip`.

A local signature is enough. This build does not need to be uploaded, notarised,
or submitted.

## Step 2 — run it with diagnostics on

Install the signed build to `/Applications` as usual, then launch it **from
Terminal** so the variable reaches it:

```bash
NEIGHT_SANDBOX_DIAG=1 /Applications/Neight.app/Contents/MacOS/Neight
```

The app window opens as normal. Leave the Terminal window alone while you use
it — quitting Neight returns you to the prompt.

If launching from Terminal is inconvenient, this works too, but it sets the
variable for *every* app you launch afterwards, so please undo it when you are
finished:

```bash
launchctl setenv NEIGHT_SANDBOX_DIAG 1     # then launch Neight from Finder
launchctl unsetenv NEIGHT_SANDBOX_DIAG     # afterwards
```

## Step 3 — open two files

Both through **File › Open** in the app. The Open panel is the whole point, so
please do not drag files onto the icon or use Open With.

1. **A plain local file** — something in `~/Documents`, on the internal disk,
   not in any synced folder. A short `.txt` is ideal.
2. **A file in a synced folder** — Dropbox, iCloud Drive or OneDrive, whichever
   you have. Ideally the same `sample.txt` you traced last time.

Expect both to fail with *"macOS did not grant Neight access to…"*. **That is
the expected result** — please do it anyway and carry on. If either one *opens*,
that is a genuinely valuable surprise and worth telling us on its own.

## Step 4 — send the log back

```
~/Library/Containers/com.murasu.neight/Data/Library/Application Support/Neight/sandbox-diagnostics.log
```

Note the `Containers` path: a sandboxed app's home is redirected, so this is
**not** in your own `~/Library/Application Support`. To copy it somewhere easy
to attach:

```bash
cp ~/Library/Containers/com.murasu.neight/Data/Library/Application\ Support/Neight/sandbox-diagnostics.log \
   ~/Desktop/neight-sandbox-diagnostics.log
```

**What is in it:** the app version, whether the sandbox is active, and one line
per step naming the files you opened. Nothing else — no file contents, no
account details, no identifiers of yours. It is a short text file; please read
it before sending if you would like to, and rename or redact any path you would
rather not share. The filenames are not important to us, only the outcomes.

## What the log will look like

A successful mint followed by a denied read reads roughly like this:

```
=== Neight 2026.083 — 2026-08-23 11:04:21 — sandboxed=True container='com.murasu.neight' ===
11:04:31.882  grant: panel access is live for /Users/…/sample.txt
11:04:31.884  mint: ok for /Users/…/sample.txt (812 bytes)
11:04:31.901  access: resolved /Users/…/sample.txt, stale=False
11:04:31.902  access: startAccessingSecurityScopedResource -> 0
11:04:31.903  read: DENIED on /Users/…/sample.txt
```

The line that decides everything is `startAccessingSecurityScopedResource`:

- **`-> 0`** — macOS refused to reopen the grant. The bookmark is being minted
  in a way that does not survive redemption, and the fix is in how Neight
  creates it.
- **`-> 1` followed by `read: DENIED`** — macOS says the grant is open while the
  sandbox denies the read anyway. A different bug, and a much stranger one; the
  `access: grant is attached to …` line would then tell us whether the grant
  landed on a different path than the one being read.

`grant:` and `mint:` matter too. If `grant:` reports **NO panel access**, then
the Open panel is not granting anything on your Mac either and the problem is
further upstream than anyone has assumed so far.

## What happens next

We fix it against whatever the log says, and send you a normal signed
submission — 2026.084 — with a fresh artifact hash and no diagnostic step. The
diagnostic mode stays in the shipped build but does nothing unless the
environment variable is set, so it costs users nothing.

If it turns out you would rather not do this round trip, the alternative that
removes you from the loop entirely is an **Apple Development certificate and
provisioning profile we can use locally**. That would let us reproduce and fix
sandbox bugs here in minutes instead of asking you each time. Either way, thank
you — this has been unblockable from our side without you.
