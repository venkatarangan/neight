## Installing this update

There is no automatic installer. Please follow the steps below for your platform.

### macOS

1. Download **Neight-mac-arm64-signed.zip** from the assets below.
2. Double-click the zip to unzip it — you will get **Neight.app**.
3. Open **Finder → Applications**, and delete the existing **Neight.app**.
4. Drag the new **Neight.app** into the Applications folder.
5. Launch Neight normally.
6. **Note:** From this version onward, settings are stored in `~/Library/Application Support/Neight/` and survive updates. This upgrade is the last one that can lose them: older versions kept `settings.json` *inside* `Neight.app`, so deleting the old app in step 3 deletes it. To carry your preferences across, copy `Neight.app/Contents/MacOS/settings.json` to `~/Library/Application Support/Neight/settings.json` before step 3.

### Windows

1. Download **Neight.exe** from the assets below.
2. To find where your current copy lives: right-click the Neight icon or shortcut → **Properties** → click **Open File Location**.
3. Delete the existing **Neight.exe** in that folder.
4. Copy the newly downloaded **Neight.exe** into the same folder.
5. Launch Neight normally.
