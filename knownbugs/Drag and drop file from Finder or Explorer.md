# Drag and Drop File from Finder / Explorer

## Current Behavior

When a text file is dragged from macOS Finder (or Windows Explorer) and dropped onto the Neight editor window, Qt's default `QPlainTextEdit` behavior kicks in: it treats the drop as text content and inserts the file path as plain text into the document. The file is not opened.

This is identical on both macOS and Windows — neither platform opens the file.

The `QFileOpenEvent` path already implemented in `NeightApplication.event()` is a separate mechanism that only fires for macOS Apple Events ("Open With", Dock drops), not for drag-and-drop onto the window.

## Expected Behavior

Dragging a `.txt` or `.md` file onto the editor window should open the file, the same way "Open With" or `File → Open` does.

## Proposed Fix

Override two methods in the `CodeEditor` class (the `QPlainTextEdit` subclass):

### `dragEnterEvent`

- Check if MIME data contains `hasUrls()` (a file drag, not a text drag)
- Extract the first URL and convert it to a local file path
- Accept only if the extension is `.txt` or `.md` (case-insensitive) — call `event.acceptProposedAction()`
- For any other file type, silently call `event.ignore()` (no status message while dragging)

### `dropEvent`

- Extract the first URL from the MIME data (multiple files: only the first is used, rest are ignored silently)
- Extension check: only `.txt` or `.md`. If anything else → show a brief status bar message e.g. `"Drop ignored — only .txt and .md files are supported"` and return. No popup dialog.
- **Unsaved changes**: call the existing `_maybe_save_changes()` on the parent `Notepad` window. This shows the existing Yes / No / Cancel dialog — intentional, because silently discarding unsaved work on an accidental drop would be a worse outcome than the dialog. If the user cancels → abort the drop.
- Call `_open_file_path(path, notify_errors=False, show_status=True)`:
  - `notify_errors=False` suppresses all `QMessageBox` popups for file errors (too large, binary, unreadable)
  - `show_status=True` shows `"Opened: <path>"` on the status bar on success
  - All existing guards inside `_open_file_path` (file size limit, encoding fallbacks, binary detection) remain fully active

### Where to insert

Right after `insertFromMimeData` (currently around line 1670), still inside the `CodeEditor` class, before the `FindReplaceDialog` class definition.

### What is NOT changed

- `_open_file_path` — used as-is with all its internal guards
- `_maybe_save_changes` — used as-is for unsaved-changes prompt
- `NeightApplication.event()` (macOS Apple Events) — untouched
