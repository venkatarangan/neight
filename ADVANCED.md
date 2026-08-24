# Neight — Advanced Features

This document covers the features and configuration options aimed at power users — those who want to go beyond the defaults and tailor Neight precisely to their workflow.

For a general introduction see [README.md](README.md).
For developer and build information see [DEVELOPER.md](DEVELOPER.md).

---

## One-Click Writing Modes

Neight ships with two built-in mode presets accessible from the **Help** menu. Each applies a complete, coherent set of settings in one click.

### Writer (சொல்வெளி) Mode

**Help → Writer (சொல்வெளி) Mode** applies a preset optimized for Tamil prose writing. It configures a clean, distraction-free environment: large serif Tamil font, generous line spacing and margins, minimal status bar, and quiet auto-save.

| Setting | Value |
|---|---|
| Font | **macOS:** Tamil MN 24 pt (falls back to system default at 24 pt) · **Windows:** Nirmala UI 24 pt (falls back to system default at 24 pt) |
| Line spacing | Double |
| Text margins | 25% |
| Word wrap | On |
| Word Count | Shown |
| Sentence / Char / Reading Time / Line / Col | Hidden |
| Auto-save | Every 2 minutes |
| Gutter line numbers | Off |
| Auto-hide scrollbar | On |
| Partial word highlighting | Off |
| Continue where you left off | Off |
| Appearance theme | Follow OS |
| Typing layout | Tamil Anjal (if available) |

All settings are applied to the live UI immediately and written atomically — the settings file is never left in a partially updated state.

---

### Techie (நுட்பர்) Mode

**Help → Techie (நுட்பர்) Mode** applies a preset optimized for software engineers: compact font, full status bar, gutter line numbers enabled, and information-dense layout.

| Setting | Value |
|---|---|
| Font | **macOS:** Tamil Sangam MN 14 pt (falls back to system default at 14 pt) · **Windows:** Nirmala UI 14 pt (falls back to system default at 14 pt) |
| Line spacing | Single Line |
| Text margins | 0% |
| Word wrap | On |
| Word Count | Shown |
| Sentence Count | Shown |
| Character Count | Shown |
| Reading Time | Shown |
| Cursor Line | Shown |
| Cursor Column | Shown |
| Auto-save | Every 2 minutes |
| Gutter line numbers | On |
| Auto-hide scrollbar | Off |
| Partial word highlighting | On |
| Continue where you left off | On |
| Appearance theme | Follow OS |

---

## Save Presets (Power User Feature)

The built-in Writer and Techie modes are starting points. If you have invested time crafting your own exact settings — a specific font, particular margin widths, a custom color scheme — Save Presets let you make those settings the new baseline for whichever mode you prefer.

**Settings → Save Current Settings to → Writer Mode Preset** saves your current Neight settings to:

```
~/Documents/Neight/writer_mode.json
```

**Settings → Save Current Settings to → Techie Mode Preset** saves your current settings to:

```
~/Documents/Neight/techie_mode.json
```

The next time you select **Writer (சொல்வெளி) Mode** or **Techie (நுட்பர்) Mode**, Neight silently loads your saved preset instead of the built-in defaults. If the file is missing or unreadable for any reason, Neight falls back to its built-in defaults automatically — nothing breaks.

Both files are plain JSON and can be inspected, edited by hand, or copied between machines. In the direct download and on Windows they also survive app deletion and reinstallation.

> **Mac App Store version:** from 2026.086 these files live in
> `~/Library/Application Support/Neight/` instead. See
> [The Mac App Store version keeps its files elsewhere](#the-mac-app-store-version-keeps-its-files-elsewhere).


## Reading Time

Reading Time estimates how long the current document would take to read and shows the result in the status bar as **Read:**.

With text selected it estimates the **selection** instead, and relabels itself **Read (sel):** so the two are never confused. (`N of Total` is used for the word, sentence and character counts, but a duration reads badly that way — `<1 of 2 min` is more puzzling than useful — so reading time carries a marker rather than a ratio.)

Configure it from **View → Status Bar → Reading Time…**

- Configurable Tamil reading speed: **50–400 words per minute** (in steps of 50: 50, 100, 150 … 400; default 150)
- Configurable English reading speed: **50–400 words per minute** (in steps of 50; default 250)
- Other scripts use a fixed **180 words per minute**
- Settings are remembered across launches
- Off by default

Neight classifies each word as Tamil, English, or Other and computes total reading time as:

$$
T = \frac{W_t}{R_t} + \frac{W_e}{R_e} + \frac{W_o}{R_o}
$$

Where $W_t$, $W_e$, $W_o$ are word counts and $R_t$, $R_e$, $R_o$ are the configured reading speeds.

---

## Word Index Overlay

The Word Index Overlay numbers every word in the document and floats those numbers over the text — a semi-transparent wash over the page, lovingly called the **butter paper effect** (like placing a translucent sheet over a manuscript to annotate word positions). Useful for quickly finding, citing, or referencing a specific word during review or editing.

Toggle it from **View → Word Index Overlay**, or click the **Words:** label in the status bar.

### How it works

- A semi-transparent backdrop covers the editor
- Each word gets a small superscript number positioned to its left, center, or right
- Numbers scale down automatically when many words are on screen (adaptive density)

### Customization — Settings → Appearance → Word Index Overlay

| Setting | What it controls |
|---|---|
| Shrink numbers when many words are visible | Adaptive density |
| Number color | Color of the word number labels |
| Number position | Left, centered, or right of each word |
| Clear space at top (px) | Pixels left uncovered at the top of the editor |
| Backdrop opacity (dark / light) | Strength of the translucent wash behind the numbers |
| Number text opacity | Solidity of the numbers themselves |
| Glow opacity (dark / light) | Contrasting aura around each number for legibility |

Changing the number color automatically adjusts backdrop, text, and glow presets so you do not need to tune all three manually.

Every control has a **ⓘ button** — click it to see a plain-English explanation as a popup.

---

## Configuring the Language Switch — Settings → Language Switch

**Settings → Language Switch** opens the keyboard switching configuration. The dialog explains the feature for writers who may not be familiar with input method switching.

From the dialog you can:

- Enable or disable the double-press quick switch
- Choose whether to use the **first two installed layouts** from your system list
- Or force switching between the **auto-detected Tamil and English layouts** when both are found

The dialog is platform-aware:

- **macOS** — shows **⌃ Control** and links to System Settings
- **Windows / Linux** — shows **Ctrl** and links to system keyboard settings

If only one layout is installed, the feature is automatically disabled and the dialog tells you how to add a second layout.

**macOS** uses native Text Input Services via Carbon. **Windows** uses native Windows layout APIs.

---

## Appearance Settings — Settings → Appearance

Split into two sections: **Theme** and **Word Index Overlay**.

### Theme

| Option | What it does |
|---|---|
| Follow OS | Matches your system Light or Dark mode automatically |
| Force Dark | Locks the editor to dark mode |
| Force Light | Locks the editor to light mode |
| Custom Colors | Lets you pick exact background and text colors |

Custom color rows appear only when **Custom Colors** is selected.

A **Reset to defaults** button restores all theme settings at once.

Every control in the Appearance dialog has a tooltip and a **ⓘ button** for plain-English explanations.

---

## Partial Word Highlighting

When enabled (**View → Partial Word Highlighting**), Neight highlights substring matches when you select a word. Useful for Tamil and other inflected languages where you may want to track a stem across multiple longer word forms.

Example: selecting `நடிகர்` also highlights `நடிகர்கள்` and `நடிகர்களே`.

Off by default.

### Match limit

To keep the editor fast even in very long documents, Neight caps highlighting at **1,000 matches** per selection. When the limit is reached:

- The status bar shows **Matches: 1000+** instead of an exact count.
- A brief message appears explaining that only the first 1,000 matches are shown.
- The full document is not blocked or slowed — the scan stops as soon as the cap is hit.

In practice the cap is only reached when searching for extremely common single characters or short stems in a large document. For normal stems it will never be hit.

---

## Find/Replace Escape Sequences

Neight’s Find and Replace fields support escape sequences for characters that cannot be typed directly.

Click the **ℹ button** inside the Find/Replace bar to open the escape sequence helper. The helper shows a full list and lets you click any sequence to insert it into the active field.

| Sequence | Character inserted |
|---|---|
| `\n` | Newline |
| `\t` | Tab |
| `\r` | Carriage return |
| `\f` | Form feed |
| `\v` | Vertical tab |
| `\0` | Null character |
| `\\` | Literal backslash |
| `\xHH` | Byte by hex code (e.g. `\x0A`) |
| `\u0000` | Unicode codepoint by hex (e.g. `\u0B95` for க) |

This is especially useful when searching for linebreaks, paragraph separators, or invisible Unicode characters in Tamil or multilingual text.

---

## Unicode Tools

### Normalize Unicode — Edit menu

**Edit → Normalize Unicode (NFC)** rewrites the entire document into NFC normalized form. Useful before publishing Tamil text that may have accumulated inconsistent codepoint sequences from copy-paste or mixed input methods.

### Triple-click to search

**Triple-click** any word to instantly look it up in Google. The word under the cursor is selected and your default browser opens the search. This works for both Tamil and English words. (Right-click on a single Tamil word also shows **Search Sorkuvai** to look it up in the Tamil dictionary.)

---

## Recovery Copies for Unsaved Documents

When you have typed content but have not yet named or saved the file, Neight silently keeps a recovery copy on every autosave tick. This means your work is protected even before you ever press `Ctrl+S`.

### How it works

- On the first autosave tick after the window opens with unsaved content, Neight creates a recovery file inside `~/Documents/Neight/` with a name like `recovery-12345-678901.txt` (process ID + random number).
- Each subsequent tick overwrites the same file so only one copy accumulates per window session.
- The write is atomic: a temp file is written and fsync'd first, then renamed over the previous copy — the recovery file is never left in a corrupt state. This holds in every build, the Mac App Store one included, because recovery copies are written inside Neight's own folder rather than to a file you picked.
- **The recovery file is deleted automatically** the moment you save the document (giving it a real name), open a different file, start a new document, or close the window and choose **Don't Save**. You do not need to clean up manually during normal use.
- The feature is completely silent — no status bar message, no notification.

### Accessing recovery files

**File → View Recovery Folder** opens `~/Documents/Neight/` in Finder (macOS) or Explorer (Windows). The folder is created automatically if it does not yet exist.

> **Mac App Store version:** from 2026.086 these files live in
> `~/Library/Application Support/Neight/` instead. See
> [The Mac App Store version keeps its files elsewhere](#the-mac-app-store-version-keeps-its-files-elsewhere).


**File → Empty Recovery Folder** permanently deletes all `recovery-*.txt` and `recovery-*.md` files in the folder. A confirmation dialog warns before proceeding, and the file belonging to the current window (if any) is always skipped. Use this periodically to keep the folder tidy.

### When autosave is disabled

If the autosave interval is set to **Off** (0 minutes), the timer never starts and no recovery copies are written. This matches the existing behaviour — recovery writes use the same timer as normal autosave.

---

## Smart Suggested Filename

When you press `Ctrl+S` (`Cmd+S` on macOS) on a document that has never been named, the save dialog opens pre-filled with a filename derived from the first words of your text.

### Naming rules

| Rule | Detail |
|---|---|
| Source | First 4 words of the document (fewer if the document is shorter) |
| Maximum length | 100 characters including the `.txt` extension (stem capped at 96) |
| Word count preference | As many words as fit within the 96-character stem limit; fewer words tried before hard-trimming |
| Illegal characters | Characters invalid on Windows or macOS (`\ / : * ? " < > |` and ASCII control characters) are stripped before the name is used |
| Trailing dots | Removed (Windows rejects filenames ending with `.`) |
| Empty result | If the document contains no words, or only illegal characters, the dialog falls back to `Untitled.txt` as usual |

### Behaviour

- The suggestion fires **only** from `Ctrl+S` on an unsaved document. **File → Save As** (direct menu action) always opens the dialog with `Untitled.txt` as today — no suggestion is injected.
- The user can accept the suggested name, edit it, or navigate to a completely different location. The dialog is fully interactive and behaves identically to a normal Save As.
- Once the file is saved under any name, subsequent `Ctrl+S` presses write directly to that file (normal save), and the suggestion is never shown again for that session.

---

## Settings and File Locations

Neight creates and updates `settings.json` automatically.

### Where settings are stored

The location differs by platform, because what is safe differs by platform.

**Windows and Linux** keep `settings.json` **next to the executable or script**, which makes a Windows install portable — copy the folder, keep your preferences. Only when that folder cannot be written to does Neight fall back to a per-user location:

- **Windows:** `%LOCALAPPDATA%\Neight\settings.json`
- **Linux:** `~/.config/Neight/settings.json`

**macOS** always uses a per-user location and never writes inside the app bundle:

```
~/Library/Application Support/Neight/settings.json
```

Beside the executable would mean *inside* `Neight.app`, where settings are destroyed every time the app is replaced by an update. Your settings now survive updates and reinstalls.

The first launch after upgrading to this behaviour performs a **one-time migration**: if the Application Support file does not exist yet, Neight copies your existing `settings.json` from inside the old bundle, or failing that from `~/.config/Neight/`. The old file is copied, not moved — nothing is deleted, it is simply no longer read. If neither file is still present (because the old `Neight.app` was deleted before the new one was first launched), Neight starts with factory defaults.

**Help → Debug Info** always shows the path actually in use. Do not assume — check there.

### The Mac App Store version keeps its files elsewhere

From **2026.086**, the Mac App Store build keeps presets and recovery copies in
`~/Library/Application Support/Neight/` rather than `~/Documents/Neight/`.

App Store apps run inside a **sandbox**, and inside it `~` does not mean your
home folder — macOS redirects it into a private container at
`~/Library/Containers/com.murasu.neight/Data/`. Writing to `~/Documents/Neight/`
from in there succeeds, which is why this went unnoticed for so long, but the
files land in the *container's* Documents folder: somewhere Finder does not show
you, and somewhere macOS deletes along with the app. A preset that promises to
outlive the app, sitting in a folder that does not, is worse than one that is
honestly app-private — so the sandboxed build puts both kinds of file where a
sandboxed app is meant to keep its own state.

Two consequences worth knowing:

- **Presets do not survive deleting the App Store version.** They are plain
  JSON, so copy them somewhere else first if you want to keep them.
- **Every dialog that names the folder shows the resolved path.**
  **File → View Recovery Folder** and the preset confirmation dialogs tell you
  where the files actually are on your machine. Read the path they show rather
  than assuming from this document.

The Open and Save dialogs are also affected: they used to start in `~`, which
inside the sandbox is that same container root — an unfamiliar folder where a
saved file effectively disappeared. From 2026.086 they start in your real
Documents folder, and can navigate anywhere from there as normal.

**The direct download, Windows and Linux are unaffected.** None of them is
sandboxed, and all of them keep using `~/Documents/Neight/`.

> The version live on the Mac App Store today predates this and cannot open or
> save files at all. Everything in this section applies from 2026.086 onward.

### Accessing settings files

**Help → Debug Info** shows the exact paths to `settings.json` and today's autosave log, with buttons alongside each:

- **Copy path** — copies the path to the clipboard
- **Open** — opens the file in your default application
- **Reset configuration** (settings row only) — permanently erases all saved preferences and restores factory defaults. A confirmation dialog warns before proceeding.

> Modifying settings files by hand is supported but proceed with care — a corrupted file is caught on startup with a recovery prompt.

### File associations

**Help → Debug Info** has a **File Associations** section for opening `.txt` and `.md` files with Neight. The two platforms behave differently, because their operating systems allow different things.

#### Windows

**Where the association comes from depends on how you installed Neight.**

- **Microsoft Store** — from the **2026.081** update onward, `.txt`, `.md` and `.markdown` are registered by the app package itself, so Neight appears in the right-click → **Open With** menu for those types with nothing to switch on. (On an earlier Store build no association exists; update from the Store to get it.) This is handled by Windows, not by Neight, so it cannot be turned off from inside the app; use Windows' own Open With settings if you want it gone.
- **Direct download** — the `.exe` is not registered with the Windows shell and will not appear under **Open With**. Install from the Store if you want that integration.

Earlier versions offered two checkboxes here that wrote the association into `HKEY_CURRENT_USER` directly. They have been removed. That approach cannot work for a Store install: the writes do not survive, and the command they record points at a versioned `WindowsApps` folder that ceases to exist at the next Store update. If those old registrations left dead entries in your **Open With** menu, opening **Help → Debug Info** clears them out automatically.

Neight never becomes your **default** application for a file type, and no application is allowed to make itself one on Windows: since Windows 8 the setting that records your default app is protected by a hash the operating system verifies, specifically so that software cannot silently take over your file types.

So the last step is yours, and only yours. The **Open Windows Default Apps settings…** button takes you straight to the right page — on a Store install, straight to Neight's own entry — where you can set it per file type. There is also a link to Microsoft's own instructions for doing it.

#### macOS

macOS *does* let an application register itself as the default handler, through Launch Services. Debug Info shows which application currently owns `.md`, and **Open .md files with Neight** switches it to Neight.

Two conditions apply:

- It works only for the built **Neight.app**, not a source checkout. Launch Services identifies handlers by bundle identifier, which a plain Python run does not have — Debug Info says so if that is your situation.
- `Neight.app` must be registered with Launch Services. If macOS refuses the change, move the app to `/Applications`, launch it once from there, and try again.

### Preset files

User mode presets (see [Save Presets](#save-presets-power-user-feature) above) are stored separately from `settings.json`:

- `~/Documents/Neight/writer_mode.json`
- `~/Documents/Neight/techie_mode.json`

These files are plain JSON and can be copied between machines. Outside the Mac App Store build they also survive app reinstallation.

> **Mac App Store version:** from 2026.086 these files live in
> `~/Library/Application Support/Neight/` instead. See
> [The Mac App Store version keeps its files elsewhere](#the-mac-app-store-version-keeps-its-files-elsewhere).


### Recovery folder

Recovery copies of unsaved documents (see [Recovery Copies for Unsaved Documents](#recovery-copies-for-unsaved-documents) above) are written to:

- `~/Documents/Neight/recovery-<PID>-<random>.txt`

Recovery files share the correctly capitalized `~/Documents/Neight/` directory
with preset files; they are separate from `settings.json`. This exact
capitalization also applies on macOS, where paths can be case-sensitive. Files
here are cleaned up automatically during normal use. Use **File → Empty
Recovery Folder** to delete any leftovers.

> **Mac App Store version:** from 2026.086 these files live in
> `~/Library/Application Support/Neight/` instead. See
> [The Mac App Store version keeps its files elsewhere](#the-mac-app-store-version-keeps-its-files-elsewhere).


---

## Known Issue — Tamil Text Navigation

Tamil text navigation in Qt-based editors has a segmentation quirk for some consonant + pulli + consonant combinations. The caret or selection can jump across a whole cluster instead of stepping through individual logical letters.

This is a Qt-level behavior, not specific to Neight. Detailed notes and reproduction examples are in [knownbugs/Bug in QT for Tamil text handling.md](knownbugs/Bug%20in%20QT%20for%20Tamil%20text%20handling.md).

---

## Updating Neight

Neight never checks for updates on its own — it makes no automatic network
request of any kind. How you get a new version depends on where you installed
it from:

- **Microsoft Store (Windows)** — updates arrive automatically, like any other
  Store app. Nothing to do.
- **Mac App Store (macOS)** — same: updates arrive automatically. The
  [listing](https://apps.apple.com/app/neight/id6800348235?mt=12) is the recommended install on macOS.
- **Direct download** — manual. These come from the `dist-latest` branch and
  are rebuilt with every build, so they run ahead of the store versions and are
  **unsigned**. **Help → Neight on GitHub** opens the project page in your
  browser; compare the latest build against the version in **Help → About**.

### Installing an update (direct downloads)

#### Windows

1. Download the new [`Neight.exe`](https://raw.githubusercontent.com/venkatarangan/neight/dist-latest/dist/Neight.exe).
2. Close the running Neight instance.
3. Replace the old `Neight.exe` with the downloaded file in the same folder.
4. Replacing only the `.exe` leaves `settings.json` untouched, wherever it lives. Check **Help → Debug Info** for its exact path if you are moving the whole folder.

#### macOS

1. Download [`Neight-mac-arm64-unsigned.app.zip`](https://raw.githubusercontent.com/venkatarangan/neight/dist-latest/dist/Neight-mac-arm64-unsigned.app.zip).
2. Unzip the archive.
3. Drag the new `Neight.app` to `/Applications`, replacing the old one when prompted.
4. The build is unsigned, so the first launch needs a **right-click → Open → Open**. If macOS still blocks it, run once in Terminal:
   ```bash
   xattr -dr com.apple.quarantine /Applications/Neight.app
   ```

### What happens to your settings when you delete Neight on macOS?

They survive. Settings live outside the app bundle:

```
~/Library/Application Support/Neight/settings.json
```

Deleting or replacing `Neight.app` does not touch that folder, so an update keeps your preferences.

**One exception, and it applies only once.** Older versions stored `settings.json` *inside* the bundle, at a path such as `/Applications/Neight.app/Contents/MacOS/settings.json`. Those settings are migrated on the first launch of the new version — but only if the old bundle is still there to read from. If you delete the old `Neight.app` before launching the new one, the settings inside it are already gone. Check **Help → Debug Info** to see which path is in use.

**To protect your preferences across updates,** use **Save Presets** (below). In the direct download, preset files live in your `Documents` folder, entirely outside the bundle, and survive app deletion, reinstallation, and a factory reset. In the Mac App Store build from 2026.086 they live inside the app's sandbox container instead and are deleted with the app, so copy them somewhere else first — see [The Mac App Store version keeps its files elsewhere](#the-mac-app-store-version-keeps-its-files-elsewhere).

Note that `settings.json` also contains a few machine-specific values (last-opened file path, window size). If you move to a new machine those will not apply, but font, theme, line spacing, autosave interval and the rest carry over cleanly.

### Protecting your settings with Save Presets

The safest way to preserve your carefully tuned settings across updates, reinstalls, or new machines is to save them as a named preset *before* making any changes.

Use **Settings → Save current settings to → Writer Mode Preset** or **Techie Mode Preset** to export your current configuration to:

```
~/Documents/Neight/writer_mode.json
~/Documents/Neight/techie_mode.json
```

These files live in your `Documents` folder — completely separate from the app and from `settings.json`. They survive app deletion, reinstallation, and a factory reset of `settings.json`. They are plain JSON and can be backed up, copied between machines, or opened in any text editor.

> **Mac App Store version:** from 2026.086 these files live in
> `~/Library/Application Support/Neight/` instead. See
> [The Mac App Store version keeps its files elsewhere](#the-mac-app-store-version-keeps-its-files-elsewhere).
>
> There they are *inside* the app's container, so they do **not** survive
> deleting the app. Copy them out yourself to keep them.


The next time you select **Help → Writer (சொல்வெளி) Mode** or **Help → Techie (நுட்பர்) Mode**, Neight loads your saved preset and restores all your preferences in one click.
