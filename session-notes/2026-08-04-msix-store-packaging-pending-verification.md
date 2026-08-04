# 2026-08-04 — MSIX/Microsoft Store packaging built, blocked on Partner Center identity verification

**State at close:** `main` @ `c177817`, working tree clean. The MSIX
packaging pipeline is built, tested, and pushed. It cannot go further right
now because it needs identity values that only exist after Microsoft
finishes verifying the maintainer's new Partner Center account — that
verification is in progress with no fixed ETA.

## Why this thread exists

`Neight.exe` triggers Windows SmartScreen warnings because it isn't signed
by a certificate with an established reputation. Two ways to fix that were
discussed: pay for/obtain a code-signing certificate (e.g. SignPath.io's
free open-source program), or publish through the Microsoft Store, where
Microsoft re-signs every package on publish so SmartScreen never appears at
all. The maintainer chose the **Microsoft Store** route — individual
developer registration is free (Microsoft dropped the old $19 fee).

## What was built this session (commit `c177817`)

- **`design/gen_msix_assets.py`** — generates the Store logo assets
  (`Square44x44Logo.png`, `Square150x150Logo.png`, `Wide310x150Logo.png`,
  `StoreLogo.png`, etc.) from the existing `neight.ico`, no new artwork
  needed. Already run; output committed under `packaging/msix_assets/Assets/`.
- **`packaging/AppxManifest.xml.template`** — the package manifest. Wraps
  `Neight.exe` as a classic Win32 app under the Desktop Bridge
  (`EntryPoint="Windows.FullTrustApplication"`), **not** a native UWP
  rewrite — no application source changed.
- **`packaging/msix_identity.json`** — holds the three identity values
  Partner Center assigns once the app name is reserved. Currently
  placeholders (`REPLACE_ME`) — see "What happens next" below.
- **`build_msix.ps1`** — orchestrates the build: validates identity is
  filled in and the working tree is clean (same provenance discipline as
  `release_windows.ps1`), converts `VERSION` (`"2026.078"`) to the 4-part
  numeric version MSIX requires (`2026.78.0.0`), stages `Neight.exe` +
  assets + rendered manifest, and runs `makeappx.exe pack` to produce
  `dist\Neight.msix`. An optional `-Sign` flag creates a throwaway local
  test certificate (`packaging\NeightTestCert.pfx`/`.cer`, gitignored) for
  sideload testing only — never used for the actual Store submission.
- **`DEVELOPER.md`** — new "Microsoft Store (MSIX) Packaging" section
  documents the whole flow end to end, including the account setup steps
  below.
- **`.gitignore`** — added `packaging/*.pfx`, `*.cer`, `*.pfx.password` so
  the local test-signing key can never be committed.

**Verified before pushing:** ran the full pipeline with fake placeholder
identity values (`CN=00000000-...`, restored to `REPLACE_ME` afterward, no
test artifacts left committed). This caught a real bug — the manifest
template's XML comment contained a literal `--`, which is invalid inside
XML comments and made `makeappx` reject the whole manifest
(`error C00CEE23`). Fixed by removing the double hyphens from the comment
text. Both the unsigned path and `-Sign` (self-signed cert creation +
`signtool` signing) were run successfully end to end.

## Where the maintainer is right now

Registered a free individual developer account at
[partner.microsoft.com/dashboard](https://partner.microsoft.com/dashboard).
**Waiting on Microsoft's identity verification** — no action possible on
the repo side until that clears.

## What happens next, once verification completes

1. **Reserve the app name** `Neight` — Partner Center → Apps and games →
   **+ New product**.
2. Open that app's **Product identity** page (under App management) and
   copy the three values shown there — **Package/Identity/Name**,
   **Package/Identity/Publisher**, **Package/Properties/PublisherDisplayName**
   — into `packaging/msix_identity.json`, replacing the `REPLACE_ME`
   placeholders exactly. (These three values are **not secret** — they ship
   inside every installed copy of the app — so committing them to the
   public repo is intentional and fine. What must never be pasted into the
   repo or into chat: the Partner Center login password, any identity
   verification documents, bank/tax/payout details, or the local
   `NeightTestCert.pfx` private key.)
3. Run `buildme.bat` (if a fresh `.exe` is wanted) then `build_msix.ps1` →
   produces `dist\Neight.msix`.
4. Test locally: enable Developer Mode once
   (Settings → Privacy & security → For developers), then
   `Add-AppxPackage -Register dist\msix_staging\AppxManifest.xml` — fastest
   path, no signing needed. Or use `build_msix.ps1 -Sign` to test the actual
   signed `.msix` closer to what Partner Center receives.
5. Upload `dist\Neight.msix` in Partner Center → **Packages**. Fill in the
   Store listing content (description, screenshots, age rating) — that part
   isn't automatable and needs the maintainer's input.

## Deliberately deferred, not forgotten

File/type associations for `.txt`/`.md` were left out of the manifest on
purpose for this first submission — Store apps can register them, but it
adds review scrutiny that isn't needed just to get SmartScreen-free
installs working. Worth adding in a follow-up once the base listing is
approved.

## Unrelated open items, unchanged from the previous session

Carried forward from [`2026-07-29`](2026-07-29-trackpad-fixes-and-cleanup.md)
and [`2026-08-03`](2026-08-03-macos-release-and-windows-handoff.md) — not
touched this session: pinch-zoom calibration on a real trackpad, drag-and-drop
from Finder/Explorer, and the general mac/Windows release-split situation
(`v2026.077` mac-only/immutable, `v2026.078` Windows-only/Latest).
