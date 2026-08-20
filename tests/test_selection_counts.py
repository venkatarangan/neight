"""Status bar counts for a selection must agree with the document's.

Qt hands back two different spellings of the same text: `toPlainText()` uses
`\\n` between paragraphs, `selectedText()` uses U+2029.  Counting a selection
straight from `selectedText()` therefore drifts from the document counts on any
multi-paragraph text -- silently, and only for users who write in paragraphs.
Selecting everything is the case that pins it down: the two must agree exactly.

Also guards the delay asymmetry.  Selection counts appear on a 250 ms timer so
that transient selections never reach the status bar, but they must disappear
*immediately* when the selection is cleared -- a lingering "42 of 1240" that
describes a selection the user has already dismissed is worse than no feature.
The timer slot is invoked directly rather than waited on: these are plain
scripts with no event loop spinning.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from _harness import check, equal, report  # noqa: E402

# Multi-paragraph and mixed-script on purpose: the paragraph breaks are what
# make the U+2029 bug visible, and the Tamil exercises the reading-time split.
DOC = "\n\n".join([
    "The first paragraph is written in English. It has two sentences.",
    "இது தமிழில் எழுதப்பட்ட பத்தி. இதில் இரண்டு வாக்கியங்கள் உள்ளன.",
    "A third paragraph, mixing தமிழ் and English words together. Done!",
])


def main() -> None:
    import neight
    from PySide6.QtGui import QTextCursor

    # Point settings at a throwaway file *before* constructing the window.
    # Notepad saves preferences as a side effect of ordinary operation, so a
    # test that skips this writes the counter visibility it sets below into the
    # real settings of whoever runs it -- and the next test to start reads them.
    store = pathlib.Path(tempfile.mkdtemp()) / "settings.json"
    neight.SettingsManager._determine_active_path = lambda self: store

    app = neight.NeightApplication(sys.argv)  # noqa: F841
    window = neight.Notepad(initial_file=None, restore_last_session=False)

    # Every counter on, so each one is actually exercised.
    window._status_show_words = True
    window._status_show_sentences = True
    window._status_show_chars = True
    window._reading_time_enabled = True

    window.editor.setPlainText(DOC)
    window._update_status_bar()
    doc = dict(window._doc_counts)

    check(doc.get("words", 0) > 0, f"document word count should be positive, got {doc}")

    # --- Select All must reproduce the document counts exactly --------------
    window.editor.selectAll()
    window._update_selection_counts()
    sel = window._sel_counts
    check(sel is not None, "selecting everything should produce selection counts")
    for key in ("words", "sentences", "chars"):
        equal(sel.get(key), doc.get(key), f"select-all {key} must equal document {key}")

    equal(window.words_label.text(), f"Words: {doc['words']} of {doc['words']}",
          "select-all words label")
    equal(window.chars_label.text(), f"Chars: {doc['chars']} of {doc['chars']}",
          "select-all chars label")
    check(window.reading_time_label.text().startswith("Read (sel):"),
          "reading time must mark itself as a selection, got "
          f"{window.reading_time_label.text()!r}")

    # Counting the raw selectedText() instead of the normalised form is the bug
    # this file exists for.  Assert the two spellings really do differ, so the
    # check above cannot pass vacuously on a build where Qt stopped using U+2029.
    raw = window.editor.textCursor().selectedText()
    check("\u2029" in raw,
          "expected U+2029 paragraph separators in selectedText(); "
          "if Qt changed this, the normalisation guard above is no longer meaningful")

    # --- A partial selection must be strictly smaller -----------------------
    cursor = window.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.Start)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                        QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    window._update_selection_counts()
    part = window._sel_counts
    check(part is not None, "a partial selection should produce selection counts")
    check(0 < part.get("words", 0) < doc["words"],
          f"first-paragraph words {part.get('words')} should be between 0 and {doc['words']}")
    check(0 < part.get("chars", 0) < doc["chars"],
          f"first-paragraph chars {part.get('chars')} should be between 0 and {doc['chars']}")
    equal(window.words_label.text(), f"Words: {part['words']} of {doc['words']}",
          "partial selection words label")

    # --- Clearing reverts immediately, with no timer tick -------------------
    # _on_selection_changed_counts is what selectionChanged fires; the revert
    # path must complete inside it rather than deferring to the 250 ms timer.
    cursor.clearSelection()
    window.editor.setTextCursor(cursor)
    window._on_selection_changed_counts()
    check(window._sel_counts is None,
          "clearing the selection must drop the selection counts immediately")
    equal(window.words_label.text(), f"Words: {doc['words']}",
          "words label must revert to the plain document count immediately")
    equal(window.chars_label.text(), f"Chars: {doc['chars']}",
          "chars label must revert to the plain document count immediately")
    check(window.reading_time_label.text().startswith("Read:"),
          "reading time must drop its selection marker, got "
          f"{window.reading_time_label.text()!r}")

    # --- Hidden counters stay hidden and uncounted --------------------------
    # The feature must not resurrect a counter the user switched off.
    window._status_show_sentences = False
    window.sentences_label.setText("")
    window._update_status_bar()
    window.editor.selectAll()
    window._update_selection_counts()
    equal(window.sentences_label.text(), "",
          "a hidden sentence counter must stay empty while text is selected")
    check("sentences" not in (window._sel_counts or {}),
          "a hidden counter must never be computed for the selection")
    check(window.words_label.text().startswith("Words: "),
          "visible counters must still render while another is hidden")

    # --- Reserved width widens only while a selection is live --------------
    # Reserving the "N of Total" width unconditionally cost ~230px of status bar
    # even with nothing selected, pushing the smallest usable window from 928px
    # to 1159px and clipping the keyboard-layout label on a half-screen window.
    window._status_show_sentences = True
    window.editor.setPlainText(DOC)
    window._update_status_bar()
    narrow = window.words_label.minimumWidth()
    window.editor.selectAll()
    window._update_selection_counts()
    wide = window.words_label.minimumWidth()
    check(wide > narrow,
          f"counters must reserve more width while selected ({wide} vs {narrow})")
    cursor = window.editor.textCursor()
    cursor.clearSelection()
    window.editor.setTextCursor(cursor)
    window._on_selection_changed_counts()
    equal(window.words_label.minimumWidth(), narrow,
          "clearing the selection must give the reserved width back")

    sys.exit(report("Selection counts"))


if __name__ == "__main__":
    main()
