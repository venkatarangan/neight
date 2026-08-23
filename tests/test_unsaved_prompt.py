"""A save prompt must only appear when there is something to save.

Two separate bugs met here.  Applying saved preferences at startup resizes the
document margin and restyles blocks, and Qt counts each of those as a content
change, so a freshly launched window came up already flagged as modified:
launching Neight and going straight to File > Open asked whether to save an
untouched, empty document.  Separately, typing something and then deleting it
all again leaves an untitled document flagged modified with nothing in it, where
the only save on offer would write an empty file.

Guards the two together because they share one symptom and one gate,
Notepad._maybe_save_changes(): every entry point that could discard work --
New, Open, close, and the Finder hand-off -- asks it first, so a false positive
here is a prompt on every one of them.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from _harness import check, equal, report  # noqa: E402

from PySide6.QtGui import QTextCursor  # noqa: E402


def _type(window, text: str) -> None:
    """Insert through a cursor, the way a keystroke does.

    setPlainText() cannot stand in for this: it resets the undo stack and
    clears the modified flag, so a test written with it would show a document
    that is never dirty and would pass against a completely broken gate.
    """
    cursor = window.editor.textCursor()
    cursor.insertText(text)


def _select_all_and_delete(window) -> None:
    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    cursor.removeSelectedText()


def unsaved_prompt(app, window) -> None:
    """Unsaved-changes prompt"""
    import neight

    # 1. A window that has just started has nothing to save.
    equal(window.editor.document().isModified(), False,
          "a freshly started window reports itself modified before any edit")
    check(window._maybe_save_changes(),
          "startup state would raise a save prompt on File > Open")
    equal(window.windowTitle(), "Untitled - Neight",
          "title carries the modified marker before any edit")

    # 2. Real typing is a real change, and must still be caught.
    _type(window, "வணக்கம்")
    equal(window.editor.document().isModified(), True,
          "typing did not mark the document modified")
    equal(window.windowTitle(), "Untitled* - Neight",
          "title missing the modified marker after typing")

    # 3. Typed and then cleared: still flagged, but an untitled empty document
    #    has nothing worth writing.
    _select_all_and_delete(window)
    equal(window.editor.documentText(), "", "document not empty after clearing")
    check(window._maybe_save_changes(),
          "an emptied untitled document would raise a save prompt")

    # 4. A document with a path is different: emptying a file is a real edit,
    #    and losing it silently would destroy the user's content.
    path = pathlib.Path(tempfile.mkdtemp()) / "sample.txt"
    path.write_text("இது ஒரு சோதனை\n", encoding="utf-8")
    check(window._open_file_path(path), "could not open the sample file")
    equal(window.editor.document().isModified(), False,
          "a just-opened file reports itself modified")
    check(window._maybe_save_changes(),
          "a just-opened, unedited file would raise a save prompt")

    _select_all_and_delete(window)
    equal(window.editor.document().isModified(), True,
          "emptying an opened file did not mark it modified")
    check(window.current_path is not None and
          not (window.current_path is None and not window.editor.documentText().strip()),
          "emptying a saved file was treated as nothing to save")

    # 5. Sandbox detection must say "not sandboxed" here, because that answer
    #    is what routes every read and write in this suite down the plain
    #    Python path.  A false positive would silently move all file I/O onto
    #    the Qt path and this test would no longer exercise what users run.
    equal(neight._macos_is_sandboxed(), False,
          "sandbox detection reports a sandbox in a plain test run")


if __name__ == "__main__":
    from _harness import main
    main(unsaved_prompt)
