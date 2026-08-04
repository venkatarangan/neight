## What's in this update

This is the Windows `2026.078` release. No application code changed since
`2026.076` — this release exists because GitHub's immutable-releases setting
blocked adding a Windows build to the signed macOS `v2026.077` release, so
Windows shipped as its own version instead. `v2026.078` is now the **Latest**
release; the signed macOS build remains permanently on
[`v2026.077`](https://github.com/venkatarangan/neight/releases/tag/v2026.077)
and will not receive further assets.

The full list of application changes, most recently trackpad zoom and
triple-click fixes, is in
[CHANGELOG.md](https://github.com/venkatarangan/neight/blob/main/CHANGELOG.md).

---

## Installing this update

There is no automatic installer. Please follow the steps below for your platform.

### macOS

1. Download **Neight-mac-arm64-signed.zip** from the assets below.
2. Double-click the zip to unzip it — you will get **Neight.app**.
3. Open **Finder → Applications**, and delete the existing **Neight.app**.
4. Drag the new **Neight.app** into the Applications folder.
5. Launch Neight normally.
6. Settings are stored in `~/Library/Application Support/Neight/` and survive
   this update — deleting the old app in step 3 does not touch them.

### Windows

1. Download **Neight.exe** from the assets below.
2. To find where your current copy lives: right-click the Neight icon or shortcut → **Properties** → click **Open File Location**.
3. Delete the existing **Neight.exe** in that folder.
4. Copy the newly downloaded **Neight.exe** into the same folder.
5. Launch Neight normally.
