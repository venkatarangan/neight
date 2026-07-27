"""Cursor and layout agreement in a long document.

The custom line-spacing layout repositions every QTextLine as a side effect of
being queried, and viewport margins are recomputed from that same layout, so the
property worth guarding is agreement: the logical cursor position, the painted
caret and the position a click maps to must all describe the same visual line.

Scaled to stay quick under the offscreen platform plugin used by CI.
"""
import pathlib
import sys

from PySide6.QtCore import QPoint
from PySide6.QtGui import QTextCursor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from _harness import check, equal, main  # noqa: E402

TAMIL = "ஶ்ரீ முற்றும் ஞூமூகூ தூ பூ கூ"
WRAPPING_PARAGRAPH = (
    "This is a deliberately long paragraph that wraps several times across the "
    f"viewport. {TAMIL} and more English text to force multiple visual lines "
    "inside a single logical block. "
) * 3


def build_document(lines: int) -> str:
    out = []
    for i in range(1, lines + 1):
        if i % 97 == 0:
            out.append(WRAPPING_PARAGRAPH)
        elif i % 7 == 0:
            out.append(f"{i} {TAMIL}")
        elif i % 5 == 0:
            out.append(f"{i} mixed தமிழ் and English on one line")
        else:
            out.append(f"Line {i} plain ascii content here")
    return "\n".join(out)


def run(app, win):
    """Cursor and layout"""
    editor = win.editor
    win.resize(900, 500)
    win.show()
    editor.setPlainText(build_document(800))
    for _ in range(8):
        app.processEvents()

    def caret_top(position: int) -> int:
        cursor = QTextCursor(editor.document())
        cursor.setPosition(position)
        return editor.cursorRect(cursor).top()

    def round_trip(position: int, label: str) -> None:
        """position -> caret rect -> click there -> position; same visual line."""
        cursor = QTextCursor(editor.document())
        cursor.setPosition(position)
        rect = editor.cursorRect(cursor)
        if rect.height() <= 0:
            return
        point = QPoint(rect.left() + 2, rect.center().y())
        if not editor.viewport().rect().contains(point):
            return
        landed = editor.cursorForPosition(point).position()
        check(caret_top(position) == caret_top(landed),
              f"{label}: position {position} clicked back to {landed} on a "
              f"different visual line")

    # Sweep every visible line at a range of layout settings and scroll offsets.
    scrollbar = editor.verticalScrollBar()
    for wrap in (True, False):
        editor.setWordWrap(wrap)
        for spacing in ("single_line", "double_line"):
            win._set_line_spacing_preset(spacing, save=False, show_status=False)
            for margin in (0, 15):
                editor.setTextMarginPercent(margin)
                for _ in range(6):
                    app.processEvents()
                span = scrollbar.maximum() - scrollbar.minimum()
                for fraction in (0.0, 0.5, 1.0):
                    scrollbar.setValue(int(scrollbar.minimum() + fraction * span))
                    for _ in range(6):
                        app.processEvents()
                    label = f"wrap={wrap} spacing={spacing} margin={margin} scroll={fraction}"
                    viewport = editor.viewport().rect()
                    seen = set()
                    y = viewport.top() + 1
                    while y < viewport.bottom():
                        position = editor.cursorForPosition(
                            QPoint(viewport.left() + 4, y)).position()
                        if position not in seen:
                            seen.add(position)
                            round_trip(position, label)
                        y += 10
                    # The viewport edges are where an off-by-one-line error in
                    # the margin snapping would surface first.
                    for edge_y in (viewport.top() + 1, viewport.bottom() - 1):
                        round_trip(editor.cursorForPosition(
                            QPoint(viewport.left() + 4, edge_y)).position(),
                            f"{label} edge")

    editor.setWordWrap(False)
    win._set_line_spacing_preset("single_line", save=False, show_status=False)
    editor.setTextMarginPercent(0)
    for _ in range(6):
        app.processEvents()

    # Arrow-key navigation must visit consecutive blocks, never skipping one.
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.Start)
    editor.setTextCursor(cursor)
    previous = editor.textCursor().blockNumber()
    for step in range(200):
        editor.moveCursor(QTextCursor.MoveOperation.Down)
        app.processEvents()
        current = editor.textCursor().blockNumber()
        if not check(current == previous + 1,
                     f"Down press {step}: block {previous} -> {current}, expected "
                     f"{previous + 1}"):
            break
        previous = current

    # The caret must stay inside the viewport while navigating.
    escaped = 0
    for _ in range(200):
        editor.moveCursor(QTextCursor.MoveOperation.Down)
        app.processEvents()
        rect = editor.cursorRect()
        viewport = editor.viewport().rect()
        if rect.top() < viewport.top() - 1 or rect.bottom() > viewport.bottom() + 1:
            escaped += 1
    equal(escaped, 0, "caret left the viewport while pressing Down")

    # At the end of the document the last line must be fully visible, including
    # the descenders and stacked vowel marks Tamil puts below the baseline.
    for size in (10, 14, 18, 24, 28):
        font = editor.font()
        font.setPointSize(size)
        editor.setFont(font)
        for _ in range(8):
            app.processEvents()
        editor.moveCursor(QTextCursor.MoveOperation.End)
        editor.ensureCursorVisible()
        for _ in range(8):
            app.processEvents()
        rect = editor.cursorRect()
        viewport = editor.viewport().rect()
        check(rect.bottom() <= viewport.bottom() + 1,
              f"{size}pt: caret bottom {rect.bottom()} is past the viewport "
              f"bottom {viewport.bottom()} at the end of the document")

    font = editor.font()
    font.setPointSize(14)
    editor.setFont(font)
    for _ in range(6):
        app.processEvents()

    # The status bar must agree with where the cursor actually is.
    for block_number in (0, 1, 400, 799):
        cursor = QTextCursor(editor.document())
        cursor.setPosition(
            editor.document().findBlockByNumber(block_number).position())
        editor.setTextCursor(cursor)
        win._update_status_bar()
        app.processEvents()
        check(str(block_number + 1) in win.line_label.text(),
              f"status bar line for block {block_number} reads "
              f"{win.line_label.text()!r}")

    # Re-applying wrap must not move the cursor or the scroll position.
    cursor = QTextCursor(editor.document())
    cursor.setPosition(editor.document().findBlockByNumber(400).position() + 5)
    editor.setTextCursor(cursor)
    editor.ensureCursorVisible()
    for _ in range(6):
        app.processEvents()
    position_before = editor.textCursor().position()
    scroll_before = editor.verticalScrollBar().value()
    editor._refresh_wrap_layout(force=True)
    for _ in range(8):
        app.processEvents()
    equal(editor.textCursor().position(), position_before,
          "refreshing the wrap layout moved the cursor")
    check(abs(editor.verticalScrollBar().value() - scroll_before) <= 2,
          f"refreshing the wrap layout moved the scroll position "
          f"{scroll_before} -> {editor.verticalScrollBar().value()}")

    # Margin calculation reads the layout it is also mutating, so repeated calls
    # must settle rather than creep.
    editor._apply_viewport_margins()
    for _ in range(4):
        app.processEvents()
    first = editor.viewportMargins()
    first_height = editor.viewport().height()
    for _ in range(5):
        editor._apply_viewport_margins()
        for _ in range(4):
            app.processEvents()
    again = editor.viewportMargins()
    check((first.left(), first.top(), first.right(), first.bottom())
          == (again.left(), again.top(), again.right(), again.bottom()),
          "viewport margins drift across repeated recalculation")
    equal(editor.viewport().height(), first_height,
          "viewport height drifts across repeated recalculation")

    # Clicking below the last line belongs to the last line.
    editor.moveCursor(QTextCursor.MoveOperation.End)
    editor.ensureCursorVisible()
    for _ in range(6):
        app.processEvents()
    viewport = editor.viewport().rect()
    landed = editor.cursorForPosition(
        QPoint(viewport.center().x(), viewport.bottom() - 1)).position()
    equal(editor.document().findBlock(landed).blockNumber(),
          editor.document().blockCount() - 1,
          "clicking at the viewport bottom at the end of the document")


if __name__ == "__main__":
    main(run)
