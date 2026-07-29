"""Trackpad zoom and click gestures.

Two families of bug live here, both of which shipped and both of which are
invisible to a layout test because the geometry was never wrong — the *event
bookkeeping* was.

1. Zoom accumulation.  Wheel and pinch deltas are accumulated so a slow gesture
   still zooms, but the accumulator compared the sign of its own running total
   rather than of the incoming delta.  Reversing direction therefore had to pay
   off the banked travel first: after zooming in, several notches of zoom-out did
   nothing.  There was also no gesture boundary, so a partial step banked minutes
   earlier ate the start of the next gesture.

2. Triple-click-to-search.  Qt delivers the second click of a double click as
   MouseButtonDblClick, *not* MouseButtonPress, so a handler counting presses can
   never reach three.  The old code counted presses on a timer with no distance
   test, which inverted the feature: it never fired on a real triple click, and
   did fire on ordinary clicks used to move the caret around a long document —
   selecting a word and opening a browser.

The pinch checks assert a point *budget* rather than an exact size, since the
constants are meant to be tuned against a real trackpad.  What must not regress
is the order of magnitude: an ordinary pinch is a few points, not the whole
6-100 pt range.
"""
import pathlib
import sys
import time

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from _harness import check, equal, main  # noqa: E402


class FakeGesture:
    """Stands in for a macOS QNativeGestureEvent, which cannot be synthesised."""

    def __init__(self, gesture_type, value=0.0):
        self._type = gesture_type
        self._value = value

    def gestureType(self):
        return self._type

    def value(self):
        return self._value


BEGIN = Qt.NativeGestureType.BeginNativeGesture
ZOOM = Qt.NativeGestureType.ZoomNativeGesture
END = Qt.NativeGestureType.EndNativeGesture


def check_wheel_zoom(editor):
    step = int(editor._WHEEL_STEP)

    # One mouse-wheel notch is one point, in both directions.
    editor._reset_zoom_accumulator()
    equal(editor._consume_zoom_steps(step, 0), 1, "one wheel notch up")
    editor._reset_zoom_accumulator()
    equal(editor._consume_zoom_steps(-step, 0), -1, "one wheel notch down")

    # Sub-notch travel accumulates rather than being discarded.
    editor._reset_zoom_accumulator()
    produced = sum(editor._consume_zoom_steps(step // 6, 0) for _ in range(6))
    equal(produced, 1, "six sixth-notch deltas should accumulate to one step")

    # Reversal responds on the same amount of travel as the original direction:
    # the banked opposite travel must be discarded, not paid off.  This is the
    # regression — it previously took five reversed notches to get one step.
    editor._reset_zoom_accumulator()
    for _ in range(5):
        editor._consume_zoom_steps(step // 3, 0)
    reversed_deltas = []
    for _ in range(3):
        reversed_deltas.append(editor._consume_zoom_steps(-(step // 3), 0))
    equal(sum(reversed_deltas), -1,
          "three reversed third-notches after zooming in should give one step "
          "down (banked travel must be discarded on reversal)")

    # A pixel-precise device (trackpad) must use the pixel scale, not the
    # 120-unit mouse-notch scale, even when the platform also reports an angle.
    # The two scales must disagree here, or the check proves nothing: two wheel
    # notches of angle alongside one pixel step must yield the pixel answer.
    editor._reset_zoom_accumulator()
    pixel_step = int(editor._PIXEL_STEP)
    equal(editor._consume_zoom_steps(step * 2, pixel_step), 1,
          "pixelDelta must win over angleDelta on a pixel-precise device")

    # An idle gap ends the gesture, so nothing is carried into the next one.
    editor._reset_zoom_accumulator()
    editor._consume_zoom_steps(0, pixel_step - 1)
    editor._last_zoom_wheel_ts -= editor._ZOOM_GESTURE_IDLE_S + 1.0
    equal(editor._consume_zoom_steps(0, pixel_step - 1), 0,
          "travel banked before an idle gap must not spill into the next gesture")


def check_pinch_zoom(app, win, editor):
    applied = []
    original = win._apply_font_size_delta
    win._apply_font_size_delta = lambda steps: applied.append(steps)
    try:
        per_step = editor._PINCH_MAGNIFICATION_PER_STEP

        def pinch(total, events):
            applied.clear()
            editor._handle_native_gesture(FakeGesture(BEGIN))
            for _ in range(events):
                editor._handle_native_gesture(FakeGesture(ZOOM, total / events))
            editor._handle_native_gesture(FakeGesture(END))
            return sum(applied)

        # An ordinary pinch is a handful of points.  At the shipped 0.08 this was
        # 14 points, which ran a 12 pt document straight into the size limit.
        points = pinch(1.2, 40)
        check(2 <= points <= 9,
              f"an ordinary pinch (total magnification 1.2) moved the size "
              f"{points} points; expected roughly 2-9")

        # Symmetric in both directions.
        equal(pinch(-1.2, 40), -points, "pinching in and out are not symmetric")

        # A fast pinch must not slam into the 6 / 100 pt limit in one gesture.
        fast = pinch(1.5, 15)
        check(abs(fast) <= 12,
              f"a fast pinch moved the size {fast} points in a single gesture")

        # No single event may jump several points.
        applied.clear()
        editor._handle_native_gesture(FakeGesture(BEGIN))
        editor._handle_native_gesture(FakeGesture(ZOOM, per_step * 10))
        editor._handle_native_gesture(FakeGesture(END))
        check(all(abs(s) <= editor._PINCH_MAX_STEPS_PER_EVENT for s in applied),
              f"one pinch event applied {applied}, exceeding the per-event cap")

        # Reversing a pinch responds at once instead of first undoing travel.
        applied.clear()
        editor._handle_native_gesture(FakeGesture(BEGIN))
        for _ in range(10):
            editor._handle_native_gesture(FakeGesture(ZOOM, per_step / 2))
        out_points = sum(applied)
        applied.clear()
        for _ in range(10):
            editor._handle_native_gesture(FakeGesture(ZOOM, -per_step / 2))
        in_points = sum(applied)
        editor._handle_native_gesture(FakeGesture(END))
        equal(in_points, -out_points,
              "reversing a pinch mid-gesture is damped by banked magnification")
    finally:
        win._apply_font_size_delta = original

    # A pinch that never receives EndNativeGesture must not disable Ctrl+wheel
    # zoom for the rest of the session.
    editor._handle_native_gesture(FakeGesture(BEGIN))
    editor._handle_native_gesture(FakeGesture(ZOOM, 0.05))
    check(editor._native_pinch_in_progress(),
          "wheel zoom should be suppressed while a pinch is in progress")
    editor._last_native_zoom_ts -= editor._NATIVE_ZOOM_IDLE_S + 1.0
    check(not editor._native_pinch_in_progress(),
          "a dropped EndNativeGesture left wheel zoom suppressed forever")


def check_triple_click(app, win, editor):
    searches = []
    original = win.launch_web_search
    win.launch_web_search = searches.append
    viewport = editor.viewport()
    editor.setFocus()

    def pump(times=4):
        for _ in range(times):
            app.processEvents()

    def click(point):
        QTest.mouseClick(viewport, Qt.LeftButton, Qt.NoModifier, point)
        pump()

    def double_click(point):
        QTest.mouseDClick(viewport, Qt.LeftButton, Qt.NoModifier, point)
        pump()

    try:
        # A genuine triple click: double click, then a third press in the same
        # place.  This is the documented feature, and it never fired before.
        searches.clear()
        editor._clear_triple_click()
        spot = QPoint(120, 100)
        double_click(spot)
        click(spot)
        equal(len(searches), 1,
              "a genuine triple click did not launch the documented search")
        # Documented as selecting the *word*, not Qt's default whole-line
        # triple-click selection, and the search must be for that word.
        selected = editor.textCursor().selectedText()
        equal(selected, searches[0] if searches else None,
              "the search text and the selection disagree")
        check(selected and " " not in selected and " " not in selected,
              f"a triple click selected {selected!r}, expected a single word")

        # Ordinary clicks to move the caret must not launch anything, however
        # fast, because they are nowhere near each other.
        searches.clear()
        editor._clear_triple_click()
        for y in (30, 250, 480):
            click(QPoint(60, y))
        equal(len(searches), 0,
              "clicking around a long document launched a web search")
        check(not editor.textCursor().hasSelection(),
              "clicking around a long document force-selected a word")

        # A double click just past the drag slop is a new gesture, not a third
        # click of the previous one.
        searches.clear()
        editor._clear_triple_click()
        double_click(QPoint(120, 100))
        slop = app.startDragDistance()
        click(QPoint(120 + slop * 4, 100))
        equal(len(searches), 0,
              "a third click far from the double click still counted as a "
              "triple click")

        # Typing between the double click and the next click ends the sequence.
        searches.clear()
        editor._clear_triple_click()
        double_click(spot)
        QTest.keyClicks(editor, "x")
        pump()
        click(spot)
        equal(len(searches), 0,
              "typing between clicks did not break the triple-click sequence")

        # So does scrolling: the text has moved out from under the pointer.
        searches.clear()
        editor._clear_triple_click()
        double_click(spot)
        editor.verticalScrollBar().setValue(
            editor.verticalScrollBar().value() + 5)
        editor._clear_triple_click()  # wheelEvent's effect, without a wheel
        pump()
        click(spot)
        equal(len(searches), 0,
              "scrolling between clicks did not break the triple-click sequence")

        # And so does time: a third click after the interval is a fresh click.
        searches.clear()
        editor._clear_triple_click()
        double_click(spot)
        editor._triple_click_deadline = time.monotonic() - 0.01
        click(spot)
        equal(len(searches), 0,
              "a third click after the double-click interval still searched")

        # A double click on its own selects the word (Qt's behaviour) and must
        # not search.
        searches.clear()
        editor._clear_triple_click()
        double_click(spot)
        equal(len(searches), 0, "a plain double click launched a search")
        check(editor.textCursor().hasSelection(),
              "a plain double click no longer selects the word under it")
    finally:
        win.launch_web_search = original


def check_drag_selection(app, editor):
    """The press must still reach Qt, or selection and drag tracking break."""
    editor.verticalScrollBar().setValue(0)
    for _ in range(4):
        app.processEvents()
    viewport = editor.viewport()
    start, end = QPoint(60, 60), QPoint(400, 200)
    expected_anchor = editor.cursorForPosition(start).position()
    expected_pos = editor.cursorForPosition(end).position()

    QTest.mousePress(viewport, Qt.LeftButton, Qt.NoModifier, start)
    for _ in range(4):
        app.processEvents()
    for k in range(1, 9):
        QTest.mouseMove(viewport, QPoint(
            start.x() + (end.x() - start.x()) * k // 8,
            start.y() + (end.y() - start.y()) * k // 8))
        for _ in range(2):
            app.processEvents()
    QTest.mouseRelease(viewport, Qt.LeftButton, Qt.NoModifier, end)
    for _ in range(4):
        app.processEvents()

    cursor = editor.textCursor()
    equal((cursor.anchor(), cursor.position()), (expected_anchor, expected_pos),
          "dragging did not select from the press point to the release point")


def run(app, win):
    """Input gestures"""
    editor = win.editor
    win.resize(1000, 600)
    win.show()
    editor.setPlainText("\n".join(
        f"Line {i} alpha beta gamma delta epsilon zeta" for i in range(1, 3001)))
    for _ in range(8):
        app.processEvents()

    check_wheel_zoom(editor)
    check_pinch_zoom(app, win, editor)
    check_triple_click(app, win, editor)
    check_drag_selection(app, editor)


if __name__ == "__main__":
    main(run)
