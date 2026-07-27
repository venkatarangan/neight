# Tamil last-line descender clipping at end of document

## Symptoms

When the cursor is on the **last line** of the document and the line contains
Tamil text (or other Indic scripts), only the **top ~10%** of the glyphs on
that line is visible — the bottom of the characters (including kombu, pulli,
stacked vowel marks such as ு / ூ, and other below-baseline marks) is clipped
at the viewport's bottom edge.

Reproduces by any of:

- `Cmd+Down` / `End`-of-document shortcut.
- Pressing **Right arrow** repeatedly until the cursor reaches end of document.
- Typing new content on the last line.

Secondary symptom that was present before the navigation fixes: pressing
`Right` at end-of-document made the cursor visually "disappear" instead of
staying anchored after the final character.

## Root cause

`QPlainTextEdit` clips text painting to the viewport rectangle. At
`verticalScrollBar().maximum()` Qt positions the **last block** such that its
`blockBoundingRect().bottom()` lines up with `viewport().rect().bottom()`.
That alignment is computed from `QFontMetrics.lineSpacing()` / `descent()`.

Tamil (and other Indic) glyphs shaped by HarfBuzz can extend **below** the
font's reported `descent()`. Qt's layout engine does not account for this
extra ink, so:

- The block-bounding rectangle reported by Qt ends a few pixels *above* where
  the glyph actually paints.
- At maximum scroll the glyph paints into pixels that are outside the viewport
  rect and therefore clipped.
- There is no scroll position past `vsb.maximum()` that would push the line
  upward to reveal the descender — Qt clamps the value.

Adding bottom **viewport margin** does not help, because that region is
*outside* the viewport — the text engine never paints into it. It only makes
the visible area smaller.

## What was attempted

### Option A — wider scroll-correction in `_ensure_cursor_line_fully_visible`

Use `blockBoundingGeometry` (custom layout-aware) instead of `cursorRect`, and
clamp to `vsb.maximum()` when the cursor is on the last block. Also schedule
the visibility check from `keyPressEvent` for nav keys (Left/Right/Up/Down/
Home/End/PageUp/PageDown) so that boundary key-presses — where
`cursorPositionChanged` does **not** fire because the cursor did not actually
move — still trigger a scroll correction.

**Outcome:** Fixes the "cursor disappears when pressing Right past end" case
and is generally beneficial. **Does not** fix the Tamil descender clipping,
because Qt will not scroll past its own `maximum()`.

Status: **REMOVED from the code.** Commit `ca5a73d` ("new mac build with the QT
Text Scrolling fixes", 2026-05-23) deleted all 61 lines of it:
`_cursor_vis_timer`, the `cursorPositionChanged` → `_schedule_cursor_visibility_check`
connection, `_schedule_cursor_visibility_check()`, `_ensure_cursor_line_fully_visible()`
and the navigation-key fallback in `keyPressEvent`.

This document previously said the code was kept, which was wrong from `ca5a73d`
onwards. **Do not restore it blindly** — it was removed as part of macOS
scrolling fixes, so putting it back may reintroduce whatever it was removed to
solve. Reproduce the cursor problem against the current layout first and compare
the three candidates (current custom layout, the historical guard, and stock
`QPlainTextDocumentLayout`) under identical conditions.

### Option B — carve a "glyph safety" slack inside the viewport snap

The existing snap in `_apply_viewport_margins` rounds the viewport height
down to a whole multiple of the rendered line height (so no partial line
shows at the bottom in mid-document). The idea was to leave a slack strip of
`max(2, fm.descent(), 0.25 * fm.height())` pixels just below the last full
line slot, so the descender of the bottom-most line could paint into it:

```python
addition = (remainder - glyph_safety) % spaced
```

**Why this failed (regression):**

1. The "slack" was created by *adding bottom margin*. Bottom margin is
   **outside** the viewport rect — Qt never paints text into it. The
   descender was still clipped at the new (smaller) viewport bottom.
2. When `remainder < glyph_safety` the modulo wraps and the formula adds
   close to a **full line height** of extra bottom margin. With certain
   widget heights this hid the entire last line — observed and reported as
   "the whole line is invisible, with no indication to the user there is a
   line there."

Status: **reverted**. The snap is back to its original `addition = remainder`.

### Option C — phantom trailing block in the document

Append an invisible/empty block after the user's last block so Qt has an
"extra" line to scroll to, leaving room below the real last line.

**Why not pursued:** modifies `blockCount()`, affects line-number gutter,
word-count, save-on-disk content, undo stack, find-replace ranges, and every
other feature that iterates blocks. Too invasive.

### Option D — override `documentSize()` on the custom layout

Have `SpacedPlainTextDocumentLayout.documentSize()` report a slightly taller
document so `vsb.maximum()` increases.

**Why not pursued (untested):** Qt source for
`QPlainTextEditPrivate::_q_adjustScrollbars` computes `vmax` from
**block/line counts** (`lineCount - pageStep`), not from `documentSize`.
`documentSize` mainly drives the horizontal scrollbar in `QPlainTextEdit`.
Overriding it is unlikely to grow `vsb.maximum()`. Would need to be verified
on the target Qt version before relying on it.

### Option E — override the layout's per-block bounding rect

Make `blockBoundingRect()` for the **last block** report `height + glyph_safety`.
Since `_q_adjustScrollbars` derives line counts and positions from the layout,
inflating the last block could push `vsb.maximum()` up by one tick and leave
slack below the last line at maximum scroll. Effect on cursor positioning,
selection rectangles and click-to-position math is unclear.

Status: **not implemented** — most promising candidate for a future attempt,
but needs careful study of how the custom `SpacedPlainTextDocumentLayout`
already overrides height/positioning, and broad regression testing on
non-Tamil text.

### Option F — viewport paint translation

Install an event filter on the viewport, intercept `QPaintEvent`, translate
the painter up by `glyph_safety` pixels when the cursor is on the last block,
then call the default paint.

**Why not pursued:** very hacky; interacts with line-number area painting,
current-line highlight, selection painting, search-result highlighting, and
the custom line-spacing layout. High risk of subtle breakage.

## Current state in the code (FIXED)

The bug is fixed by combining two mechanisms:

1. **`SpacedPlainTextDocumentLayout.blockBoundingRect()`** — for the last
   block in the document, returns a height inflated by
   `fm.lineSpacing() + fm.descent()` pixels. Qt's `_q_adjustScrollbars`
   uses block bounding rects to compute the document's total height and
   scrollbar tick allocation, so this gives `vsb.maximum()` real, reachable
   ticks below the actual last-line ink. Configured via
   `setLastBlockExtra(extra)` from `CodeEditor._apply_viewport_margins`.
2. **`QTextDocument.setDocumentMargin()`** — sized at
   `max(8, descent + 4, height / 2)`. Painted *inside* the viewport, so the
   descender of the final line paints into this strip rather than into
   clipped pixels at the viewport bottom edge.

The `_ensure_cursor_line_fully_visible` strengthening (Option A) and the nav-key
scheduling in `keyPressEvent` are **no longer present** — they were removed in
`ca5a73d`. The two mechanisms above are what the fix now rests on entirely. If
the "cursor disappears when pressing Right past end of document" symptom returns,
that removal is the first thing to check.

### Validated outcome

Empirical sweep of font sizes 10–28 pt with Tamil last line
(`ஶ்ரீ முற்றும்`, `ஞூமூகூ`, `தூ பூ கூ`) — slack between the last block's
reported bottom and the viewport bottom is **positive at every size**:

| sz  | slack (px) |
|-----|------------|
| 10  | 13 |
| 12  | 6  |
| 14  | 8  |
| 16  | 10 |
| 18  | 14 |
| 20  | 11 |
| 24  | 16 |
| 28  | 16 |

Also verified with line-spacing multipliers 1.0 / 1.5 / 2.0 (all positive
slack), ASCII-only short and long documents (no regression), and Tamil short
document that fits entirely in the viewport (no spurious scroll).

## Notes for a future attempt

- The fundamental constraint is that Qt does **not** allow scrolling past
  `vsb.maximum()`, and bottom viewport margin is outside the paint area.
  Any real fix must change one of those two facts.
- Increasing `vsb.maximum()` requires Qt to believe there is more
  content/line-slots below the user's last line. The two viable handles are
  the layout's per-block height (Option E) or its line/block count (Option C,
  rejected as too invasive).
- Whatever approach is taken, verify on:
  - Pure-ASCII documents (must not introduce extra trailing blank space).
  - Mid-document scrolling (must not bring back the partial-line-at-bottom
    artefact that the original snap was added to prevent).
  - Cursor click-to-position arithmetic on the last line.
  - Selection rectangles that include the last line.
  - Find/replace highlight on the last line.
  - Line-number gutter alignment with the last line.
  - Custom line-spacing settings other than the default multiplier.

## Validation approach for any future fix

Before declaring success:

1. Headless `QPlainTextEdit` instrumentation is **not sufficient** — the
   clipping happens at the paint layer and depends on actual glyph ink
   extent, not on `blockBoundingRect` numbers. Use a real visible window and
   inspect a screenshot of the bottom strip.
2. Test with at least these inputs on the last line:
   - Tamil with deep marks: `ஶ்ரீ`, `கூ`, `தூ`, `மூ`, `ஞூ`.
   - Mixed Tamil + Latin.
   - Tamil at the application's largest configurable font size.
3. Test the navigation paths separately: `Cmd+Down`, `End`, repeated `Right`,
   click-on-last-line, typing-at-end, `Enter`-then-typing.
4. Compare against the *initial commit* of the snap code to make sure no
   mid-document regression has crept in.
