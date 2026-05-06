# Neight — Notepad Enhanced, Tamil-Friendly

**Current Version: 2026.021** | [Version History](changes/VERSION_SUMMARY.md) | [Privacy Policy](PRIVACY.md)

**Neight** is a lightweight text editor for Windows and macOS, built for real writing: Tamil, English, mixed-language drafting, quick notes, Markdown, and distraction-free composition.

It started as a tool for my own daily workflow and continues to evolve as a practical AI-assisted software project.

---

## Quick Start

### Download a pre-built app

- **Windows:** [Download Neight.exe](https://github.com/venkatarangan/neight/blob/main/dist/Neight.exe) (~51 MB)
- **macOS Apple Silicon (arm64):** [Download signed Neight.app zip](https://github.com/venkatarangan/neight/blob/main/stable/Neight-mac-arm64-signed.zip) (~40 MB, recommended)
- **Latest unsigned macOS development build:** [Download from dist](https://github.com/venkatarangan/neight/blob/main/dist/Neight-mac-arm64-unsigned.app.zip) (~40 MB)

### Install on Windows

1. Download `Neight.exe`.
2. Copy it to a folder of your choice.
3. Optionally pin it to Start or the taskbar.
4. Double-click to run.

If Windows Defender SmartScreen appears, click **More info** and then **Run anyway**.

### Install on macOS

1. Download the signed zip.
2. Unzip it in Finder.
3. Drag `Neight.app` to `/Applications`.
4. Launch it normally.

If macOS still blocks the app for any reason, run this once in Terminal:

```bash
xattr -dr com.apple.quarantine /Applications/Neight.app
```

> The signed macOS build is provided as-is. It is the same open-source app, with a proper Apple Developer signature contributed by a well-wisher to make installation smoother.

> The macOS build currently targets **Apple Silicon (arm64)** only.

---

## Screenshots

Main editor:

![Neight main editor](screenshots/neight-1.png)

Language Switch settings on macOS:

![Neight language switch settings on macOS](screenshots/macos/2026-april-28-mac-keyboard-screenshot.png)

Debug information panel on macOS:

![Neight debug info on macOS](screenshots/macos/2026-april-28-mac-debuginfo-screenshot.png)

Additional screenshots are available in the [screenshots](screenshots) folder.

---

## Why Neight Exists

I started Neight after running into Tamil text rendering and editing issues in the newer Windows Notepad. Other editors were either too heavy, too cluttered, or simply not suited to quick bilingual writing.

The goal was simple: make a small, dependable editor that feels close to Notepad, but works better for the way I actually write.

Neight is especially useful if you want:

- a simple editor for short and medium-form writing
- better support for Tamil + English workflows
- a lightweight app instead of a full IDE or word processor
- a Markdown-capable editor without a cluttered toolbar

---

## Menu Structure

Neight's menus are organized by what you are doing, not by how things are implemented.

| Menu | What you find there |
|---|---|
| **File** | New, Open, Save, Save As, PDF Export, Exit |
| **Edit** | Undo/Redo, clipboard, Find/Replace, Go To, Time/Date, Google Search, blank-line tools, Normalize Unicode |
| **Markdown** | All Markdown insertion shortcuts — headings, lists, formatting, links, tables |
| **Format** | Font, Line Spacing, Margins, Word Wrap |
| **View** | Line Numbers in Margin, Word Index, Highlight partial word selections, Status Bar controls |
| **Settings** | Auto-save, Appearance, Language Switch |
| **Help** | About, Debug Info |

### Status Bar submenu (under View)

Every element in the status bar can be individually shown or hidden from **View → Status Bar**:

- Word Count
- Sentence Count
- Character Count
- Reading Time… (opens the reading speed configuration)
- Cursor Line
- Cursor Column

Positions are fixed — hiding one item does not cause the others to shift.

---

## What Neight Can Do

### Familiar editor basics

- New, Open, Save, Save As, Exit
- Undo, Redo, Cut, Copy, Paste, Select All, Find, Find Next, Replace, Replace All, Go To, Time/Date
- Word wrap, custom fonts, status bar, zoom, dark mode support
- Standard shortcuts such as `Ctrl+S`, `Ctrl+F`, `Ctrl+G`, `F5`

### Writing-focused improvements

- **Line Numbers in Margin** — gutter line numbers alongside each paragraph, similar to code editors. Toggled from **View → Line Numbers in Margin**. Labelled clearly so it is not confused with the status bar cursor-position display.
- **Adjustable margins** from **Format → Margins** for comfortable reading width
- **Adjustable line spacing** from **Format → Line Spacing** with five presets from Very Tight to Loose
- **Live status bar counts** for words, sentences, and characters — each independently shown or hidden
- **Word-match highlighting** for single-word selections, with live match count in the status bar
- **Auto-save** with configurable intervals under **Settings → Auto-save**
- **Plain-text paste** with `Shift+Ctrl+V` or `Shift+Insert`
- **Quick Google Search** for selected text with `Ctrl+E`, or for the word under the cursor if nothing is selected
- **Sorkuvai lookup** for a selected single Tamil word from the right-click context menu
- **New Window** support for side-by-side writing
- **About** and **Debug Info** under **Help**

### Status bar

The status bar is organized into fixed-width positions. Every element has a dedicated slot so layout stays stable as values change.

From left to right:

- **Read:** — estimated reading time (when enabled)
- **Matches:** — match count when a word is selected and highlighted
- **Words:** — total word count
- **Sentences:** — total sentence count
- **Chars:** — total character count
- **Ln / Col** — cursor line and column
- **Keyboard layout** — current input method on the far right

Any element can be turned off from **View → Status Bar** without affecting the spacing of the others.

### Performance

Neight is optimized for typing speed. Writers working in long documents, or with non-Latin scripts like Tamil, need the editor to stay fast and out of the way.

Key optimizations:

- **Debounced status bar updates** — counters update 90 ms after you stop typing, never on every keystroke. This keeps the UI thread free during bursts.
- **Debounced Word Index overlay** — the Word Index repaints 150 ms after you pause, not per keystroke.
- **Burst suppression flags** — during rapid typing, expensive full-document passes are skipped entirely. The overlay defers cache rebuilds and partial repaints until the burst ends.
- **Smart token reuse** — when both word count and reading time are enabled, the word tokenization pass runs only once per update cycle.
- **`contentsChange` signal** — Neight uses Qt's lower-level `contentsChange` signal (which fires with change coordinates) rather than `contentsChanged` (which fires blindly for every event), so updates can be targeted rather than global.
- **Custom line spacing engine** — Qt's `QPlainTextEdit` does not support line-height adjustments through its standard formatting API. Neight uses a custom `SpacedPlainTextDocumentLayout` subclass that overrides `blockBoundingRect()` to add configurable extra pixels per block, without rebuilding the document on every keystroke.

### Sentence count

Sentence count is calculated from sentence-ending punctuation rather than grammar analysis. Neight splits text on common boundaries (`.`, `!`, `?`, and several Unicode equivalents), ignores empty fragments, and counts what remains. Lightweight, fast, and practical for mixed-language drafts.

### Blank-line tools

Two small editing tools for cleaning up drafts, available from **Edit**:

- **Collapse Blank Lines** — reduces long runs of empty lines to a single blank line
- **Insert Blank Lines** — adds one blank line after every non-empty line

**Insert Blank Lines** is useful when you want to turn a dense block of writing into a double-spaced draft for review, annotation, or pasting into chat-style tools. **Collapse Blank Lines** is the reverse: it normalizes over-spaced pasted content in one step.

---

## Word Index Overlay

The Word Index Overlay numbers every word in your document and floats those numbers over the text. It is useful for quickly finding, citing, or referencing a specific word during review or editing.

Toggle it from **View → Word Index**, or click the **Words:** label in the status bar.

### How it works

- When active, a semi-transparent backdrop covers the editor
- Each word gets a small superscript number positioned to its left, center, or right
- Numbers scale down automatically when many words are on screen (adaptive density), keeping the view readable

### Visual customization from Settings → Appearance

All overlay appearance is configured in **Settings → Appearance → Word Index Overlay**:

| Setting | What it controls |
|---|---|
| Shrink numbers when many words are visible | Adaptive density — scales numbers down when the screen is dense |
| Number color | Color of the word number labels |
| Number position | Left, centered, or right of each word |
| Clear space at top (px) | Leaves that many pixels at the top uncovered, keeping the first line clean |
| Backdrop opacity (dark / light) | Strength of the translucent wash behind the numbers |
| Number text opacity | How solid the numbers themselves are |
| Glow opacity (dark / light) | Contrasting aura around each number for legibility against any background |

Each setting has a **ⓘ** button that shows a plain-English explanation when clicked, without opening any extra dialog.

Presets for backdrop, text, and glow are applied automatically when you change the number color, so you can switch colors without manually tweaking opacities.

---

## Tamil and Keyboard Workflow

### Quick keyboard switching

Press **⌃ Control twice quickly** on macOS (or **Ctrl twice** on Windows/Linux) to switch between two keyboard layouts without leaving the editor.

Additional shortcuts:

- **Ctrl+,** — switch to the first layout in the active pair
- **Ctrl+.** — switch to the second layout in the active pair

The current layout is always shown at the bottom-right of the status bar.

### Configuring the switch — Settings → Language Switch

**Settings → Language Switch** opens the configuration dialog (previously called "Keyboards"). The dialog explains the feature in plain language for writers who may not be familiar with the concept of input method switching.

From the dialog you can:

- enable or disable the double-press quick switch
- choose whether to use the **first two installed layouts** from your system list
- or force switching between the **auto-detected Tamil and English layouts** when both are found

The dialog is aware of your platform:

- **macOS** — shows **⌃ Control** and links to System Settings
- **Windows / Linux** — shows **Ctrl** and links to system keyboard settings

If only one layout is installed, the feature is automatically disabled and the dialog tells you how to add a second layout.

### How layout selection works on macOS

- **macOS:** uses native Text Input Services via Carbon

### How layout selection works on Windows

- **Windows:** uses native Windows layout APIs

---

## Appearance Settings

**Settings → Appearance** is split into two sections: **Theme** and **Word Index Overlay**.

### Theme

| Option | What it does |
|---|---|
| Follow OS | Matches your system Light or Dark mode automatically |
| Force Dark | Locks the editor to dark mode regardless of system settings |
| Force Light | Locks the editor to light mode regardless of system settings |
| Custom Colors | Lets you pick exact background and text colors from a color picker |

Custom color rows are only shown when **Custom Colors** is selected — the dialog stays compact otherwise.

A **Reset to defaults** button restores all theme settings at once.

### Word Index Overlay

See the [Word Index Overlay](#word-index-overlay) section above for the full setting reference.

Every control in the Appearance dialog has:

- a **tooltip** — hover over any control to read what it does
- a **ⓘ button** — click it to see the explanation as a popup without opening any other window

---

## Reading Time

Reading Time estimates how long it takes to read the current document and shows the result in the status bar.

Configure it from **View → Status Bar → Reading Time…**

- configurable Tamil reading speed from **50 to 400 words per minute**
- configurable English reading speed from **50 to 400 words per minute**
- other scripts use a fixed **180 words per minute**
- settings are remembered across launches
- off by default

Neight classifies each word as Tamil, English, or Other and computes:

$$
T = \frac{W_t}{R_t} + \frac{W_e}{R_e} + \frac{W_o}{R_o}
$$

Where $W_t$, $W_e$, $W_o$ are word counts and $R_t$, $R_e$, $R_o$ are the reading speeds in words per minute. This handles mixed Tamil-English text naturally.

---

## Markdown Support

All Markdown shortcuts live in the **Markdown** menu (previously called **Insert**). The rename reflects what the menu actually does — every item inserts or wraps Markdown syntax.

- headings with `Ctrl+1` through `Ctrl+6`
- bold, italic, bold italic
- unordered lists, ordered lists, checkboxes
- quotes, code blocks, strikethrough, highlight
- horizontal rules and table templates
- image and hyperlink insertion with URL validation
- automatic `https://` prefixing during link/image validation
- open and save both `.txt` and `.md` files

### Smart tag replacement

When you change formatting, Neight replaces existing markers cleanly. Changing a heading level removes the old `#` markers first; changing italic to bold removes the old asterisks before inserting the new ones. This prevents accidental marker stacking.

---

## Unicode Tools

### Normalize Unicode (NFC) — Edit menu

Rewrites the entire document into Unicode NFC normalized form. Useful before publishing, especially for Tamil text that may have accumulated inconsistent codepoint sequences from copy-paste or mixed input methods.

### Highlight partial word selections — View menu

When enabled, Neight highlights substring matches when you select a word. Useful for Tamil and other inflected languages where you may want to track a stem inside multiple longer forms.

Example: selecting `நடிகர்` can also highlight `நடிகர்கள்` and `நடிகர்களே`.

Off by default.

---

## PDF Export

Neight can export both plain text and Markdown to PDF from the **File** menu.

- **Text to PDF:** available when a `.txt` file is open
- **Markdown to PDF:** available when a `.md` file is open
- Export options appear contextually based on the current file type
- A4 layout with proper margins
- filename header for text export
- rendered headings, tables, and code blocks for Markdown export
- font choice carried into the PDF output

Requires the Python `markdown` package (included in [requirements.txt](requirements.txt)).

---

## Remembered Preferences

Neight remembers what you would expect a daily-use editor to remember:

- last opened file and directory
- window size
- font family and size
- word wrap state
- line-number visibility
- text margin percentage
- line spacing
- auto-save interval
- per-item status bar visibility (words, sentences, chars, cursor line, cursor column, reading time)
- Word Index overlay settings (color, position, opacity, density)
- theme mode and custom colors
- language switch settings
- reading time enabled state and WPM values
- search URL prefixes

---

## Settings and File Locations

Neight creates and updates `settings.json` automatically.

### Where settings are stored

- If the app folder is writable, settings are saved next to the executable or script.
- Otherwise:
  - **Windows:** `%LOCALAPPDATA%\Neight\settings.json`
  - **macOS / Linux:** `~/.config/Neight/settings.json`

### Settings reliability

- On first run, a default settings file is created automatically.
- If settings are corrupted, a startup prompt shows the file path with three options: **Copy Path**, **Reset to Defaults**, or **Exit**.

### Customizable URL prefixes

- `google_search_url_prefix` — used by **Edit → Search with Google** (`Ctrl+E`)
- `sorkuvai_search_url_prefix` — used by the right-click **Search Sorkuvai** context menu item

Update either prefix in `settings.json` if the service URLs change without needing to rebuild the app.

---

## Running from Source

```bash
git clone https://github.com/venkatarangan/neight.git
cd neight
python -m pip install --upgrade pip
pip install -r requirements.txt
python neight.py
```

### Requirements

- Python 3.10+
- PySide6 6.x (Qt 6)
- markdown
- pillow (for design helpers only)
- pyinstaller (only if building distributables)

See [requirements.txt](requirements.txt) for the current dependency list.

> Neight uses **PySide6 exclusively**. All PyQt5 references have been removed. There is no Qt5 fallback.

---

## Building Distributables

### Windows

```bat
buildme.bat
```

Or manually:

```bat
python -m pip install pyinstaller
pyinstaller --name Neight --onefile --windowed --icon neight.ico neight.py
```

The executable is written to `dist\Neight.exe`.

### macOS app bundle

```bash
chmod +x buildme_mac_app.sh
./buildme_mac_app.sh
```

This produces:

- `dist/Neight.app`
- `dist/Neight-mac-arm64-unsigned.app.zip`

### macOS standalone onefile build

```bash
chmod +x changes/buildme_mac_onefile.sh
./changes/buildme_mac_onefile.sh
```

### Manual macOS build

```bash
pip3 install pyinstaller
pyinstaller --name Neight --windowed --icon neight.icns neight.py
```

> Tested on Apple Silicon. An Intel build would need to be produced on appropriate hardware.

---

## Keyboard Shortcuts

| Action | Shortcut |
|---|---|
| New File | Ctrl+N |
| New Window | Ctrl+Shift+N (Win/Linux), Meta+Shift+N (macOS) |
| Open | Ctrl+O |
| Save | Ctrl+S |
| Save As | Ctrl+Shift+S |
| Find / Replace | Ctrl+F / Ctrl+H |
| Go To Line | Ctrl+G |
| Insert Date/Time | F5 |
| Search with Google | Ctrl+E |
| Plain-text Paste | Shift+Ctrl+V or Shift+Insert |
| Language Switch | Double Ctrl (Win/Linux) or Double ⌃ Control (macOS) |
| Switch to layout 1 / 2 | Ctrl+, / Ctrl+. |
| Markdown menu | Alt+M |
| Heading 1–6 | Ctrl+1 to Ctrl+6 |
| Bold / Italic / Bold Italic | Ctrl+B / Ctrl+I / Ctrl+Shift+B |
| Code Block | Ctrl+Shift+K |
| Hyperlink | Ctrl+K |

---

## Known Issue

Tamil text navigation in Qt-based editors has a segmentation quirk for some consonant + pulli + consonant combinations. The caret or selection can jump across a whole cluster instead of stepping through individual logical letters.

This is a Qt-level behavior, not specific to Neight. Detailed notes and reproduction examples are in [knownbugs/Bug in QT for Tamil text handling.md](knownbugs/Bug%20in%20QT%20for%20Tamil%20text%20handling.md).

---

## About the Project

Neight is a personal, practical writing tool and an ongoing experiment in AI-assisted software development. The codebase has been created and evolved through iterative prompting and review inside VS Code, while the app itself is kept intentionally small and direct.

The name comes from **NotepadEnhanced → NotepadE → N8 → Neight**.

---

## Future Ideas

- Markdown live preview pane
- Export to DOCX
- A proper Windows installer
- Page numbers in PDF footer
- Print preview before PDF export
- Optional AI features for translation, rewriting, or lookup
- ~~Integrate Tamil dictionary (like Tamil Nadu Government's Sorkuvai)~~

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## Disclaimer

Neight is provided **AS IS**, without warranties of any kind, express or implied, including fitness for a particular purpose, reliability, availability, performance, and accuracy.

Neight is not affiliated with, endorsed by, or sponsored by Google, Sorkuvai, the Government of Tamil Nadu, or any other third-party service or brand referenced by this project. Neight only opens those public services by passing user-selected query text through configured URL prefixes. All third-party names, trademarks, service marks, logos, and copyrights remain the property of their respective owners.

You are responsible for validating whether it is suitable for your own workflow.

