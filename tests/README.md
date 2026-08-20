# Tests

Regression checks for the behaviour that is easy to break silently and hard to
notice by hand.

```bash
QT_QPA_PLATFORM=offscreen python3 tests/test_startup_settings.py
QT_QPA_PLATFORM=offscreen python3 tests/test_text_integrity.py
QT_QPA_PLATFORM=offscreen python3 tests/test_cursor_layout.py
QT_QPA_PLATFORM=offscreen python3 tests/test_input_gestures.py
QT_QPA_PLATFORM=offscreen python3 tests/test_selection_counts.py
```

Each script exits non-zero on failure and prints failures as GitHub Actions
annotations, so `.github/workflows/checks.yml` runs them directly. They are
plain scripts rather than pytest so CI needs nothing beyond `requirements.txt`.

- **`test_startup_settings.py`** — loading preferences at startup must never
  persist a font the user did not choose. It inspects every settings write and
  confirms that the stored font is actually applied, guarding the multi-window
  startup regression fixed in 2026.070.

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

- **`test_input_gestures.py`** — trackpad zoom and click gestures, where the
  geometry was never wrong but the event bookkeeping was. Covers wheel and pinch
  accumulation (reversing direction must respond immediately, an idle gap must
  end the gesture, a pinch must move a few points and not the whole 6-100 pt
  range, a dropped `EndNativeGesture` must not disable wheel zoom) and
  triple-click-to-search. The click checks guard a feature that was inverted:
  Qt delivers the second click of a double click as `MouseButtonDblClick`, not
  `MouseButtonPress`, so the old press-counting handler never fired on a real
  triple click and *did* fire on ordinary clicks used to move the caret around a
  long document.

- **`test_selection_counts.py`** — the status bar counters must describe the
  selection correctly when one exists. Qt spells paragraph breaks as `\n` in
  `toPlainText()` but U+2029 in `selectedText()`, so counting a selection
  straight from Qt drifts from the document counts on any multi-paragraph text —
  silently, and only for people who write in paragraphs. Selecting everything
  pins it down: the numbers must match exactly. Also guards that counts appear
  on a delay but vanish *immediately* when the selection is cleared, and that a
  counter hidden in **View → Status Bar** is never computed or shown.

Not covered here — these need a real trackpad, keyboard or Finder, so they stay
manual: the *feel* of pinch-to-zoom (the arithmetic is covered above, the
calibration is not), Tamil/English keyboard switching, and the macOS file
associations. See the "Still needs a person" section of
`knownbugs/MACOS-VALIDATION-RESULTS.md`.
