"""The sandboxed Qt I/O path must behave exactly like the Python one.

Inside the Mac App Store sandbox, Qt's security-scoped file engine holds the
grant the Open/Save panel produced, so every read and write of a user file
goes through QFile there (see the sandbox section in neight.py).
Nothing in a test environment is sandboxed, which is precisely why this needs
guarding: the Qt branch would otherwise only ever run in the one build nobody
here can sign.  Off-sandbox QFile is an ordinary file, so the helpers can be
exercised directly and compared byte for byte against the Python path.

Tamil is the point of the parity check.  ASCII-safe shortcuts break on
multi-codepoint clusters (vowel signs are Unicode Mc/Mn), so any divergence
between the two paths shows up here first, not in a user's manuscript.
"""
import os
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from _harness import check, equal, report  # noqa: E402

# Mixed corpus: Tamil with vowel signs and puḷḷi, English, blank lines.
CORPUS = (
    "இது ஒரு சோதனை.\n"
    "நெய்த் தமிழில் எழுதுவதற்கான ஒரு எடிட்டர்.\n"
    "\n"
    "Plain English line, with punctuation — and a dash.\n"
    "கடைசி வரி, முற்றுப்புள்ளி இல்லாமல்"
)


def sandbox_qt_io() -> None:
    """Sandboxed Qt file I/O parity"""
    import neight

    workdir = pathlib.Path(tempfile.mkdtemp())

    # --- reads -------------------------------------------------------------
    # The Qt read must hand back the same bytes Python reads, including a BOM,
    # which the decode pipeline downstream inspects byte-by-byte.
    for name, payload in [
        ("plain.txt", CORPUS.encode("utf-8")),
        ("bom.txt", b"\xef\xbb\xbf" + CORPUS.encode("utf-8")),
        ("crlf.txt", CORPUS.replace("\n", "\r\n").encode("utf-8")),
        ("empty.txt", b""),
    ]:
        sample = workdir / name
        sample.write_bytes(payload)
        equal(neight._sandbox_read_bytes(str(sample)), sample.read_bytes(),
              f"Qt read of {name} differs from the Python read")

    missing = workdir / "no-such-file.txt"
    try:
        neight._sandbox_read_bytes(str(missing))
        check(False, "reading a nonexistent file through Qt did not raise")
    except OSError as exc:
        check(bool(str(exc)), "the Qt read error carries no message")

    # --- writes ------------------------------------------------------------
    # On POSIX both paths must produce identical bytes.  On Windows they are
    # allowed to differ (_atomic_write_text translates \n to \r\n there) and
    # the comparison would be meaningless anyway: the Qt path is unreachable
    # off macOS.  Round-trip fidelity still holds everywhere.
    qt_target = workdir / "qt-write.txt"
    committed = neight._sandbox_write_text(str(qt_target), CORPUS)
    check(committed, "the Qt write did not report a commit")
    equal(qt_target.read_bytes().decode("utf-8"), CORPUS,
          "the Qt write did not round-trip the corpus")
    if os.linesep == "\n":
        py_target = workdir / "py-write.txt"
        neight._atomic_write_text(py_target, CORPUS)
        equal(qt_target.read_bytes(), py_target.read_bytes(),
              "Qt write bytes differ from _atomic_write_text bytes")

    # Overwriting must fully replace, not append or truncate short.
    neight._sandbox_write_text(str(qt_target), "short")
    equal(qt_target.read_bytes(), b"short", "the Qt overwrite left stale bytes")

    # A withdrawn should_commit must leave the target untouched -- this is the
    # contract the autosave generation check depends on.
    committed = neight._sandbox_write_text(
        str(qt_target), CORPUS, should_commit=lambda: False)
    equal(committed, False, "a withdrawn write still reported a commit")
    equal(qt_target.read_bytes(), b"short",
          "a withdrawn write modified the target anyway")

    # A write into a nonexistent directory must raise with Qt's message.
    # Unlike _atomic_write_text this deliberately does not mkdir the parent:
    # every real caller writes to a path a panel handed back.
    try:
        neight._sandbox_write_text(str(workdir / "no-dir" / "x.txt"), "x")
        check(False, "writing into a missing directory through Qt did not raise")
    except OSError as exc:
        check(bool(str(exc)), "the Qt write error carries no message")

    # An exception out of should_commit must propagate rather than being
    # swallowed, and must not leave the QFile open -- the try/finally in the
    # helper is what makes the second half true.
    def _explode():
        raise RuntimeError("should_commit blew up")

    guard_target = workdir / "guard.txt"
    guard_target.write_bytes(b"before")
    try:
        neight._sandbox_write_text(str(guard_target), CORPUS, should_commit=_explode)
        check(False, "a raising should_commit was swallowed")
    except RuntimeError:
        check(True, "")
    equal(guard_target.read_bytes(), b"before",
          "a raising should_commit still modified the target")

    # A directory is not a file: Qt must refuse and the helper must translate
    # that into an OSError rather than reporting a phantom success.
    try:
        neight._sandbox_write_text(str(workdir), CORPUS)
        check(False, "writing over a directory through Qt did not raise")
    except OSError as exc:
        check(bool(str(exc)), "the Qt directory-write error carries no message")

    # --- the app data folder ----------------------------------------------
    # Sandboxed, presets and recovery copies must land in Application Support:
    # ~/Documents there is the container's, invisible to the user and deleted
    # with the app.  Off the sandbox nothing may move.
    #
    # _get_app_data_dir creates what it returns, so home is redirected first --
    # a test must not leave folders in the real one.  neight.Path is pathlib's,
    # so this patches it process-wide and the finally is load-bearing.
    fake_home = pathlib.Path(tempfile.mkdtemp())
    original_home = neight.Path.home
    original_gate = neight._macos_is_sandboxed
    try:
        neight.Path.home = staticmethod(lambda: fake_home)
        neight._macos_is_sandboxed = lambda: True
        equal(str(neight.Notepad._get_app_data_dir()),
              str(fake_home / "Library" / "Application Support" / "Neight"),
              "the sandboxed app data folder is not in Application Support")
        # The panels must not open inside the container either.
        start = neight._default_start_directory()
        check(not neight._is_container_path(start),
              f"the sandboxed panel start directory is inside the container: {start}")

        neight._macos_is_sandboxed = original_gate
        equal(str(neight.Notepad._get_app_data_dir()),
              str(fake_home / "Documents" / "Neight"),
              "the unsandboxed app data folder moved")
    finally:
        neight.Path.home = original_home
        neight._macos_is_sandboxed = original_gate

    # --- the gate ----------------------------------------------------------
    # With detection forced on, the window-level open and save must run the Qt
    # branch end to end and agree with the plain path on content.
    original = neight._macos_is_sandboxed
    try:
        neight._macos_is_sandboxed = lambda: True
        window = neight.Notepad(initial_file=None, restore_last_session=False)
        sample = workdir / "gated.txt"
        sample.write_bytes(CORPUS.encode("utf-8"))
        check(window._open_file_path(str(sample), notify_errors=False),
              "the gated open failed on an ordinary file")
        equal(window.editor.documentText(), CORPUS,
              "the gated open decoded different text")
        check(window._write_to_path(str(sample)), "the gated save failed")
        equal(sample.read_bytes(),
              window.editor.documentText().encode("utf-8"),
              "the gated save wrote bytes that differ from the document")

        # Qt looks its bookmark up by the *incoming* fileName, so the sandboxed
        # branch must hand the path string over untouched.  A redundant "//" is
        # exactly what Path() would quietly normalise away.
        seen = []
        original_read = neight._sandbox_read_bytes
        try:
            neight._sandbox_read_bytes = lambda p: (seen.append(p),
                                                    original_read(p))[1]
            odd = str(sample.parent) + "//" + sample.name
            check(window._open_file_path(odd, notify_errors=False),
                  "the gated open failed on a path with a redundant separator")
        finally:
            neight._sandbox_read_bytes = original_read
        equal(seen, [odd], "the sandboxed read normalised the path before Qt saw it")

        # The autosave worker runs the same Qt branch off the UI thread.  Drive
        # it synchronously rather than waiting on the timer.
        autosaved = workdir / "autosaved.txt"
        autosaved.write_bytes(b"old")
        window.current_path = str(autosaved)
        window.editor.setPlainText(CORPUS)
        window.editor.document().setModified(True)
        window._autosave()
        # The worker reports back through a queued signal, so the flag only
        # clears once the event loop delivers it -- there is no loop running
        # here, hence the explicit pump.
        for _ in range(200):
            neight.QApplication.processEvents()
            if not window._autosave_in_progress:
                break
            time.sleep(0.01)
        equal(window._autosave_in_progress, False, "the autosave worker never finished")
        equal(autosaved.read_bytes().decode("utf-8"), CORPUS,
              "the sandboxed autosave did not write the document")

        window.close()
    finally:
        neight._macos_is_sandboxed = original


def main() -> None:
    import neight

    # Point settings at a throwaway file before any window exists: Notepad
    # persists preferences as a side effect of ordinary operation (see
    # tests/_harness.py, which does the same for the harness runner).
    store = pathlib.Path(tempfile.mkdtemp()) / "settings.json"
    neight.SettingsManager._determine_active_path = lambda self: store

    app = neight.NeightApplication(sys.argv)  # noqa: F841 -- Qt needs one alive
    sandbox_qt_io()
    sys.exit(report(sandbox_qt_io.__doc__ or "sandbox_qt_io"))


if __name__ == "__main__":
    main()
