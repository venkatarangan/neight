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
import threading

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

    # --- The cache holds finished values, never the token list -------------
    # Caching tokens retained ~6.7 MB on a 730 KB document and made every
    # repaint reclassify every token (41 ms), including the supposedly free
    # selection-clear path.  Invisible from the outside, so assert it directly.
    window._status_show_sentences = True
    window._reading_time_enabled = True
    window.editor.setPlainText(DOC)
    window._update_status_bar()
    check("tokens" not in window._doc_counts,
          f"_doc_counts must not retain the token list; keys = {sorted(window._doc_counts)}")
    check(isinstance(window._doc_counts.get("reading"), str),
          "_doc_counts must cache the finished reading-time string")
    for value in window._doc_counts.values():
        check(isinstance(value, (int, str)),
              f"cached counts must be finished values, got {type(value).__name__}")

    # An unchanged document must not be recounted.
    window._update_status_bar()
    first = window._doc_counts
    window._update_status_bar()
    check(window._doc_counts is first,
          "an unchanged document must reuse the cached counts, not recount")
    window.editor.setPlainText(DOC + " extra words here.")
    window._update_status_bar()
    check(window._doc_counts is not first,
          "an edited document must be recounted")

    # --- Script-classification memo: same answers, bounded memory ----------
    # Classification is memoised on the word to keep the reading-time estimate
    # off the per-character path.  Two things must hold: a warm memo must give
    # exactly the figures a cold one does, and the memo must stop growing at
    # its byte budget rather than following the document's vocabulary.
    window._reading_time_enabled = True
    window.editor.setPlainText(DOC)

    neight._SCRIPT_MEMO.clear()
    neight._script_memo_bytes = 0
    window._update_status_bar()
    cold = window.reading_time_label.text()
    check(len(neight._SCRIPT_MEMO) > 0, "the memo should have been populated")
    window._doc_counts = None          # force a real recount, memo now warm
    window._update_status_bar()
    equal(window.reading_time_label.text(), cold,
          "a warm memo must give the same reading time as a cold one")

    # Freeze at the cap: shrink the budget, then push far past it.
    real_cap = neight._SCRIPT_MEMO_MAX_BYTES
    try:
        neight._SCRIPT_MEMO.clear()
        neight._script_memo_bytes = 0
        neight._SCRIPT_MEMO_MAX_BYTES = 4096
        probes = [f"நினைவு{i}" if i % 2 else f"writing{i}" for i in range(4000)]
        answers = [neight.Notepad._classify_word_script(w) for w in probes]
        frozen = len(neight._SCRIPT_MEMO)
        check(neight._script_memo_bytes <= 4096 + 200,
              f"memo byte counter must stop at the budget, got {neight._script_memo_bytes}")
        check(0 < frozen < len(probes),
              f"memo must freeze partway, not hold all {len(probes)} words (held {frozen})")
        for _ in range(2):
            for w in probes:
                neight.Notepad._classify_word_script(w)
        equal(len(neight._SCRIPT_MEMO), frozen,
              "a frozen memo must not grow on further lookups")
        # Freezing may cost speed; it must never cost correctness.
        rejected = [w for w in probes if w not in neight._SCRIPT_MEMO]
        check(rejected, "expected some words to be refused entry to the memo")
        wrong = [w for w, a in zip(probes, answers)
                 if neight.Notepad._classify_word_script(w) != a]
        check(not wrong, f"words refused by the memo must still classify correctly: {wrong[:3]}")
    finally:
        neight._SCRIPT_MEMO_MAX_BYTES = real_cap
        neight._SCRIPT_MEMO.clear()
        neight._script_memo_bytes = 0

    # --- Memo safety under concurrency -------------------------------------
    # The counters run on the Qt main thread today, so this cannot happen now.
    # It is asserted because the failure mode of getting it wrong later is
    # silent: the byte budget is a non-atomic `+=`, so a counting thread would
    # lose increments and quietly stop bounding memory.  Two invariants must
    # survive regardless of how many threads call in -- answers stay correct
    # (the function is pure and dict get/set are atomic), and the entry ceiling
    # still bounds the memo even when the byte counter drifts low.
    real_cap = neight._SCRIPT_MEMO_MAX_BYTES
    real_max = neight._SCRIPT_MEMO_MAX_ENTRIES

    def reference(word):
        tamil = english = 0
        for ch in word:
            code = ord(ch)
            if 0x0B80 <= code <= 0x0BFF:
                tamil += 1
            elif ("A" <= ch <= "Z") or ("a" <= ch <= "z"):
                english += 1
        if tamil == 0 and english == 0:
            return "other"
        return "tamil" if tamil > english else ("english" if english > tamil else "other")

    try:
        neight._SCRIPT_MEMO.clear()
        neight._script_memo_bytes = 0
        neight._SCRIPT_MEMO_MAX_BYTES = 1 << 30    # let the ceiling be what binds
        neight._SCRIPT_MEMO_MAX_ENTRIES = 500
        probes = [f"நினைவு{i}" if i % 2 else f"writing{i}" for i in range(4000)]
        wrong = []

        def hammer():
            for word in probes:
                if neight.Notepad._classify_word_script(word) != reference(word):
                    wrong.append(word)

        workers = [threading.Thread(target=hammer) for _ in range(4)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        check(not wrong,
              f"concurrent lookups must stay correct; {len(wrong)} wrong, e.g. {wrong[:3]}")
        check(len(neight._SCRIPT_MEMO) <= neight._SCRIPT_MEMO_MAX_ENTRIES,
              f"entry ceiling must hold under threads: {len(neight._SCRIPT_MEMO)} "
              f"> {neight._SCRIPT_MEMO_MAX_ENTRIES}")
    finally:
        neight._SCRIPT_MEMO_MAX_BYTES = real_cap
        neight._SCRIPT_MEMO_MAX_ENTRIES = real_max
        neight._SCRIPT_MEMO.clear()
        neight._script_memo_bytes = 0

    # A cached False must not be mistaken for a cache miss -- the classic
    # memoisation bug, which would silently recompute every space forever.
    neight._WORD_CHAR_MEMO.clear()
    for ch in " a?இ\t1":
        neight._is_word_char_cached(ch)
    cached_false = [k for k, v in neight._WORD_CHAR_MEMO.items() if v is False]
    check(cached_false, "expected some characters to cache as False")
    check(all(neight._is_word_char_cached(k) is False for k in cached_false),
          "a cached False must be returned, not treated as a miss")

    sys.exit(report("Selection counts"))


if __name__ == "__main__":
    main()
