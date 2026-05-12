# Tamil Font Rendering in Status Bar on macOS

## Issue

When Writer (சொல்வெளி) Mode or Techie (நுட்பர்) Mode is applied, the status bar
`showMessage()` call displays Tamil text in an inconsistent font — not the macOS
system UI font (San Francisco). This is because `self.status.setFont()` was set
globally to `Tamil Sangam MN`, which covers Tamil well but uses its own Latin
glyphs instead of San Francisco for all other status bar text.

The same global `setFont` approach used for the fix on Windows (Nirmala UI) works
safely there because Nirmala UI's Latin glyphs are visually matched to Segoe UI.
On macOS, Tamil Sangam MN's Latin does not match San Francisco.

Additionally, `QAction.setFont()` for the Help menu items is likely silently ignored
by macOS's native AppKit menu bar, so the menu fix may have no visible effect on macOS.

## Affected locations

- `self.status.showMessage("Writer (சொல்வெளி) Mode applied", 3000)` — line ~6592
- `self.status.showMessage("Techie (நுட்பர்) Mode applied", 3000)` — line ~6815
- `self.solveli_act` and `self.engineer_act` QAction font (Help menu) — line ~2369

## Planned Fix

Instead of setting a Tamil font globally on the status bar widget, swap the font
only for the duration of the two transient `showMessage()` calls:

1. Before calling `showMessage()`, save the current status bar font.
2. Set the Tamil-capable font (`Tamil Sangam MN` on macOS, `Nirmala UI` on Windows).
3. Call `showMessage()`.
4. Use a single-shot `QTimer` with the same timeout (3000 ms) to restore the
   original font after the message disappears.

This keeps the status bar in San Francisco for all normal text (word count, line/col,
etc.) and only uses the Tamil font for those two brief mode-applied messages.

The global `setFont` on `self.status` added as a workaround should be removed once
this per-call fix is implemented.
