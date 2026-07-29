# Trackpad zoom and click placement — findings and fixes

**Run:** 2026-07-29 on macOS 26.5.2 · Apple M4 · arm64
**Environment:** Python 3.14.6 · PySide6 6.11.1
**Starting point:** `4b08936`
**Reported as:** trackpad zoom in/out not working correctly or too fast; clicking
text in the middle or start of a long file leaves the cursor haywire

Follows on from [`MACOS-VALIDATION-RESULTS.md`](MACOS-VALIDATION-RESULTS.md),
which closed A5 and left A1 as *partial* — "the arithmetic is proven, the feel is
not". The arithmetic turned out not to be proven either.

---

## Summary

Six defects, all in event bookkeeping rather than geometry. The most serious one
inverts a documented feature: triple-click-to-search **never fired on a real
triple click**, and *did* fire on ordinary clicks used to move the caret around a
long document — selecting a word the user did not select and opening a browser.

| | |
|---|---|
| Defects found and fixed | 6 |
| New automated checks | 25 (`tests/test_input_gestures.py`) |
| Checks failing on the pre-fix code | 9 |
| Still requires a person | pinch *calibration* only |

---

## What was ruled out first

The report named cursor placement, so hit testing was measured before anything
was changed. It is not at fault, and no layout code was touched.

- **Block-level hit testing is exact.** Every block painted in the viewport was
  located by its own painted geometry (`firstVisibleBlock` + `blockBoundingRect`,
  not `cursorRect`, so the check is independent of the caret), then clicked at
  its vertical centre. 30/30 configurations clean — wrap on/off × three line
  spacings × five scroll offsets, on both the offscreen plugin and real Cocoa.
- **Column mapping is exact on ASCII.** 0 of 248 caret positions mis-mapped.
- The only mismatches are 14 **inside Tamil grapheme clusters** — clicking a
  combining mark such as `்` or `ீ` snaps to the cluster boundary. That is
  correct Unicode behaviour, not a defect.
- **Clicking a 20,000-line file before layout settles** lands correctly.
- **Drag selection** spans exactly press-point to release-point.

This is consistent with the earlier 6,802-round-trip sweep, and reconfirms B2's
advice to leave `SpacedPlainTextDocumentLayout` alone.

---

## The defects

### 1. Triple-click-to-search was inverted — the cause of the haywire cursor

`mousePressEvent` counted left-button presses and treated the third within the
double-click interval as a triple click. Two things are wrong with that.

**Qt never delivers three presses.** The second click of a double click arrives
as `MouseButtonDblClick`, not `MouseButtonPress`, so `mousePressEvent` fires on
clicks 1 and 3 only. The counter reached 2 and never 3, confirmed by an event
filter:

```
QTest.mouseDClick then a third click (faithful triple-click)
  events: ['DblClick', 'Press', 'Release']
  search launched: []          <- the documented feature never fired
```

**There was no distance test.** macOS's double-click interval is 500 ms, so any
three presses Qt had *not* paired into a double click — which is exactly what
repositioning clicks in different parts of a file look like — were stitched
together:

```
3 quick clicks at y=30, 250, 480 (hundreds of pixels apart)
  searches launched: ['21']
  selection: True  selected='21'  pos=918
```

Typing between the clicks did not reset the counter either, so click → type →
click → click also fired it. The caret jumping to a word it had not selected,
plus a browser window, is the reported symptom.

Fixed by using Qt's own model: `mouseDoubleClickEvent` opens the window in which
a third click counts, and that click must fall within `startDragDistance()` (10 px)
of it. Typing, scrolling and focus loss end the sequence. The handler no longer
returns early — `super().mousePressEvent()` always runs, so `QWidgetTextControl`
keeps coherent selection and drag state; previously it never saw the press at all.

A genuine triple click now selects the word and searches for it, as
`README.md` and `ADVANCED.md` have always documented.

### 2. Reversing wheel zoom direction was damped

`_consume_zoom_steps` compared the sign of the **accumulator** against its own
running total, so a reversal was only noticed once the accumulator had crossed
zero — the user first had to pay off the travel banked in the other direction:

```
+40 +40 +40 +40 +40   ->  1 step, 80 units banked
-40 -> 0   -40 -> 0   -40 -> 0   -40 -> 0   -40 -> -1
```

Five reversed notches for the first step down, against three for the first step
up. The sign is now taken from the incoming delta and the opposite bank is
discarded on reversal, so both directions cost three.

The code comment and the A5 row of the validation results both claimed reversal
was *not* damped. It was.

### 3. Trackpads were zoomed on the mouse-wheel scale

The pixel path was only used when `angleDelta` was exactly zero, which on macOS
it never is — so a pixel-precise device was driven by the 120-unit mouse-notch
scale. `pixelDelta` now wins when present, with `_PIXEL_STEP` (80 px) tuned for
it; `angleDelta` remains the mouse fallback.

### 4. The accumulator had no gesture boundary

Banked travel persisted indefinitely, so a partial step left over from one
gesture ate the start of the next one — possibly minutes later. A 250 ms quiet
gap (`_ZOOM_GESTURE_IDLE_S`) now ends the gesture and clears the bank.

### 5. Pinch zoom was roughly three times too fast

At 0.08 magnification per point, an ordinary pinch moved the font **14 points**
and a fast one **18** — from a 12 pt document that is the 6 pt or 100 pt limit in
a single gesture, which is precisely what A1's test 4 was written to catch.

`_PINCH_MAGNIFICATION_PER_STEP` is now **0.20**, giving about five points for the
same gesture, and `_PINCH_MAX_STEPS_PER_EVENT` caps any single event at one point
so one outsized delta cannot jump several. Pinch reversal discards banked
magnification, matching the wheel path.

### 6. A dropped `EndNativeGesture` disabled wheel zoom for the session

Recorded as a known limitation in the previous run; fixed here. `_native_zoom_active`
was set on every `ZoomNativeGesture` and cleared only by `EndNativeGesture`, so
a missed end event left Ctrl+wheel zoom permanently swallowed. `_native_pinch_in_progress()`
now treats a pinch idle for 0.5 s as finished.

---

## Regression suite

`tests/test_input_gestures.py`, wired into `.github/workflows/checks.yml`
alongside the existing three.

```bash
QT_QPA_PLATFORM=offscreen python3 tests/test_input_gestures.py
```

25 checks. **9 of them fail on the pre-fix code** — verified by stashing the fix
and running against it, so they guard behaviour rather than passing vacuously:

```
three reversed third-notches after zooming in should give one step down: got 0, want -1
idle gap: 'CodeEditor' object has no attribute '_last_zoom_wheel_ts'
an ordinary pinch (total magnification 1.2) moved the size 14 points; expected roughly 2-9
a fast pinch moved the size 18 points in a single gesture
one pinch event applied [10], exceeding the per-event cap
a dropped EndNativeGesture left wheel zoom suppressed forever
a genuine triple click did not launch the documented search: got 0, want 1
clicking around a long document launched a web search: got 1, want 0
typing between clicks did not break the triple-click sequence: got 1, want 0
```

Native gesture events cannot be synthesised, so the pinch checks drive
`_handle_native_gesture` through a `FakeGesture` stand-in. They assert a point
*budget* (an ordinary pinch is 2-9 points) rather than an exact size, because the
constants are meant to be tuned against real hardware — what must not regress is
the order of magnitude.

Full suite, both platform plugins:

| | offscreen | cocoa |
|---|---|---|
| `test_startup_settings.py` | 3 pass | 3 pass |
| `test_text_integrity.py` | 67 pass | 67 pass |
| `test_cursor_layout.py` | 601 pass | 710 pass |
| `test_input_gestures.py` | 25 pass | 25 pass |

---

## Still needs a person

Only one thing, and it is calibration rather than correctness:

**Pinch feel on a real trackpad.** The arithmetic is now covered by tests and the
magnitude is sane, but nobody has pinched a real trackpad. If it is still wrong,
turn exactly one constant — `CodeEditor._PINCH_MAGNIFICATION_PER_STEP`
(`neight.py`, above `_handle_native_gesture`). **Larger is slower.** 0.20 is
about five font points for a full comfortable pinch; 0.30 would be about three.

The equivalent knob for Ctrl+two-finger zoom is `_PIXEL_STEP`, same direction.

A1's other manual items are unchanged: ordinary two-finger scrolling must still
feel native (the non-Ctrl path is untouched), and pinch must not double-apply
against the wheel path (`_native_pinch_in_progress()` still suppresses it, now
with a timeout).
