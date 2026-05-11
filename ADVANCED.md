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
| Font | Noto Serif Tamil Regular 24 pt (falls back to any Tamil-script font, then system default) |
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
| Font | Noto Sans Tamil Thin 14 pt (falls back to system default at 14 pt) |
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

**Help → Save as Writer Mode Preset…** saves your current Neight settings to:

```
~/Documents/neight/writer_mode.json
```

**Help → Save as Techie Mode Preset…** saves your current settings to:

```
~/Documents/neight/techie_mode.json
```

The next time you select **Writer (சொல்வெளி) Mode** or **Techie (நுட்பர்) Mode**, Neight silently loads your saved preset instead of the built-in defaults. If the file is missing or unreadable for any reason, Neight falls back to its built-in defaults automatically — nothing breaks.

Both files survive app deletion and reinstallation. They are plain JSON and can be inspected, edited by hand, or copied between machines.

---

## Reading Time

Reading Time estimates how long the current document would take to read and shows the result in the status bar as **Read:**.

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

The Word Index Overlay numbers every word in the document and floats those numbers over the text. Useful for quickly finding, citing, or referencing a specific word during review or editing.

Toggle it from **View → Word Index**, or click the **Words:** label in the status bar.

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

## Settings and File Locations

Neight creates and updates `settings.json` automatically.

### Where settings are stored

- If the app folder is writable, settings are saved next to the executable or script.
- Otherwise:
  - **Windows:** `%LOCALAPPDATA%\Neight\settings.json`
  - **macOS / Linux:** `~/.config/Neight/settings.json`

### Accessing settings files

**Help → Debug Info** shows the exact paths to `settings.json` and today's autosave log, with buttons alongside each:

- **Copy path** — copies the path to the clipboard
- **Open** — opens the file in your default application
- **Reset configuration** (settings row only) — permanently erases all saved preferences and restores factory defaults. A confirmation dialog warns before proceeding.

> Modifying settings files by hand is supported but proceed with care — a corrupted file is caught on startup with a recovery prompt.

### Preset files

User mode presets (see [Save Presets](#save-presets-power-user-feature) above) are stored separately from `settings.json`:

- `~/Documents/neight/writer_mode.json`
- `~/Documents/neight/techie_mode.json`

These files are plain JSON, survive app reinstallation, and can be copied between machines.

---

## Known Issue — Tamil Text Navigation

Tamil text navigation in Qt-based editors has a segmentation quirk for some consonant + pulli + consonant combinations. The caret or selection can jump across a whole cluster instead of stepping through individual logical letters.

This is a Qt-level behavior, not specific to Neight. Detailed notes and reproduction examples are in [knownbugs/Bug in QT for Tamil text handling.md](knownbugs/Bug%20in%20QT%20for%20Tamil%20text%20handling.md).
