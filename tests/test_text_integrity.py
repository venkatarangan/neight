"""Text integrity: opening and saving must not alter the user's characters.

Guards the two silent-mutation bugs fixed alongside this file:
  * QTextDocument.toPlainText() turns U+00A0 into a plain space, so every save
    used to strip no-break spaces out of the document.
  * A BOM-less UTF-16/32 file holding ASCII decodes as UTF-8 with a NUL between
    every character, opening as "H e l l o".
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from _harness import check, equal, main  # noqa: E402

TAMIL = "ஶ்ரீ முற்றும் ஞூமூகூ தூ பூ கூ"
NBSP = " "


def run(app, win):
    """Text integrity"""
    editor = win.editor
    tmp = pathlib.Path(tempfile.mkdtemp())
    native_newline = "\r\n" if win.NATIVE_NEWLINE == "CRLF" else "\n"

    # The document text used by every save path must be exactly what went in.
    for name, text in {
        "tamil": TAMIL,
        "tamil and latin": f"{TAMIL} mixed with English",
        "no trailing newline": "alpha\nbeta\ngamma",
        "trailing newline": "alpha\nbeta\ngamma\n",
        "repeated trailing newlines": "alpha\n\n\n\n",
        "empty": "",
        "only newlines": "\n\n\n",
        "tabs": "a\tb\tc\n\tindented",
        "trailing spaces": "line with spaces   \nnext\t\n",
        "emoji": "hello 👋🏽 family 👨‍👩‍👧‍👦 flag 🇮🇳",
        "long line": "x" * 200_000,
        "combining marks": "é à ñ",
        "bidi": "شسيب עברית mixed",
        f"no-break space": f"price:{NBSP}10{NBSP}INR",
    }.items():
        editor.setPlainText(text)
        equal(editor.documentText(), text, f"document round trip for {name}")

    # Opening then saving a file already using the native newline must not touch a byte.
    for name, text in {
        "utf-8 lf": f"{TAMIL}\nsecond line\n",
        "no trailing newline": f"{TAMIL}\nsecond line",
        "empty": "",
        "single line": "just one line",
        "blank lines": "a\n\n\nb\n",
        "no-break space": f"price:{NBSP}10{NBSP}INR\n",
        "emoji": "hi 👋🏽 👨‍👩‍👧‍👦\n",
    }.items():
        path = tmp / f"roundtrip_{name.replace(' ', '_').replace('-', '_')}.txt"
        original = text.replace("\n", native_newline).encode("utf-8")
        path.write_bytes(original)
        if not check(win._open_file_path(path, notify_errors=False, show_status=False),
                     f"could not open {name}"):
            continue
        equal(win._pending_conversions(), [], f"unexpected conversion notice for {name}")
        win.current_path = str(path)
        win._write_to_path(str(path))
        check(path.read_bytes() == original,
              f"{name}: not byte-identical after open and save")

    # Encoding detection, including the wide encodings with no BOM to go on.
    body = "Hello world\nsecond line\n"
    for name, raw, want_text, want_encoding in [
        ("utf-16-le no BOM", body.encode("utf-16-le"), body, "utf-16"),
        ("utf-16 with BOM", body.encode("utf-16"), body, "utf-16"),
        ("utf-32-le no BOM", body.encode("utf-32-le"), body, "utf-32"),
        ("utf-8", body.encode("utf-8"), body, "utf-8"),
        ("utf-8 with BOM", b"\xef\xbb\xbf" + body.encode("utf-8"), body, "utf-8-sig"),
        ("utf-16-le tamil no BOM", f"{TAMIL}\n".encode("utf-16-le"), f"{TAMIL}\n", "utf-16"),
        ("crlf", b"a\r\nb\r\n", "a\nb\n", "utf-8"),
    ]:
        path = tmp / f"encoding_{name.replace(' ', '_').replace('-', '_')}.txt"
        path.write_bytes(raw)
        if not check(win._open_file_path(path, notify_errors=False, show_status=False),
                     f"could not open {name}"):
            continue
        equal(win.editor.documentText(), want_text, f"decoded text for {name}")
        equal(win._source_encoding, want_encoding, f"detected encoding for {name}")

    # A file that genuinely contains a NUL is pathological, but rewriting the
    # user's bytes is worse than opening it as-is.
    path = tmp / "with_nul.txt"
    original = b"before\x00after" + native_newline.encode("ascii")
    path.write_bytes(original)
    if check(win._open_file_path(path, notify_errors=False, show_status=False),
             "UTF-8 file containing a NUL could not be opened"):
        win.current_path = str(path)
        win._write_to_path(str(path))
        check(path.read_bytes() == original,
              "UTF-8 file containing a NUL was altered by open and save")

    # Binary input must be refused rather than mangled into text.
    path = tmp / "binary.bin"
    path.write_bytes(bytes(range(256)) * 40)
    check(not win._open_file_path(path, notify_errors=False, show_status=False),
          "a binary file was accepted as text")

    # Replace All: correct counts, no runaway when the replacement contains the
    # search text, and a single undo step for the whole operation.
    for name, source, find, replace, want in [
        ("growing replacement", "a a a", "a", "aa", "aa aa aa"),
        ("shrinking replacement", "aaa aaa", "aaa", "a", "a a"),
        ("deletion", "x-y-z", "-", "", "xyz"),
        ("tamil", "கூ தூ கூ", "கூ", "பூ", "பூ தூ பூ"),
        ("across lines", "a\nb\na\n", "a", "Z", "Z\nb\nZ\n"),
        ("no match", "hello", "zzz", "Q", "hello"),
        ("replacement contains the search text", "cat", "cat", "cat-cat", "cat-cat"),
    ]:
        editor.setPlainText(source)
        win._replace_all_occurrences(find, replace)
        equal(editor.documentText(), want, f"replace all, {name}")

    editor.setPlainText("a a a")
    win._replace_all_occurrences("a", "Z")
    editor.undo()
    equal(editor.documentText(), "a a a", "one undo reverts an entire Replace All")


if __name__ == "__main__":
    main(run)
