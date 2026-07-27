# Tests

Regression checks for the behaviour that is easy to break silently and hard to
notice by hand.

```bash
QT_QPA_PLATFORM=offscreen python3 tests/test_text_integrity.py
QT_QPA_PLATFORM=offscreen python3 tests/test_cursor_layout.py
```

Each script exits non-zero on failure and prints failures as GitHub Actions
annotations, so `.github/workflows/checks.yml` runs them directly. They are
plain scripts rather than pytest so CI needs nothing beyond `requirements.txt`.

- **`test_text_integrity.py`** — opening and saving must never alter the user's
  characters. Covers byte-identical round trips, encoding and newline detection
  (including BOM-less UTF-16/32), and Replace All. Guards two fixed bugs: Qt's
  `toPlainText()` rewriting no-break spaces on every save, and a BOM-less UTF-16
  file opening as `H e l l o` with a NUL between every character.

- **`test_cursor_layout.py`** — the logical cursor position, the painted caret
  and the position a click maps to must all agree. The custom line-spacing
  layout repositions every `QTextLine` as a side effect of being queried, and
  viewport margins are computed from that same layout, so this sweeps wrap
  modes, spacings, margins, font sizes and scroll offsets. Also checks that the
  last line stays fully visible at the end of the document, which is where Tamil
  descenders and stacked vowel marks get clipped.

Not covered here — these need a real trackpad, keyboard or Finder, so they stay
manual: pinch-to-zoom feel, Tamil/English keyboard switching, and the macOS file
associations. See `knownbugs/MACOS-TODO-pending-validation.md`.
