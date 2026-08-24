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

        # --- the grant key survives the open -------------------------------
        # The read is keyed on the exact string the panel returned; every later
        # save has to present that same string.  Storing only the Path()-
        # normalised current_path meant a file opened fine and could then never
        # be written -- the shipped 2026.086 bug.
        keyed = workdir / "keyed.txt"
        keyed.write_bytes(CORPUS.encode("utf-8"))
        odd_open = str(keyed.parent) + "//" + keyed.name
        check(window._open_file_path(odd_open, notify_errors=False),
              "the gated open failed on the grant-key path")
        equal(window._grant_path, odd_open,
              "the exact path the read was keyed on was not kept")
        check(window.current_path != odd_open,
              "current_path is expected to hold the normalised form")

        written = []
        original_write = neight._sandbox_write_text
        try:
            neight._sandbox_write_text = lambda pth, txt, **kw: (
                written.append(pth), original_write(pth, txt, **kw))[1]
            check(window.save_file(), "the save after the gated open failed")
        finally:
            neight._sandbox_write_text = original_write
        equal(written, [odd_open],
              "the save was keyed on the normalised path, not the grant's")

        window.close()
    finally:
        neight._macos_is_sandboxed = original

    # --- handing a file to another application -----------------------------
    # openUrl does not go through a file engine, so LaunchServices checks this
    # process's own access.  Inside the sandbox the file is opened through Qt
    # first, both to wake the dormant grant and as a detector: no grant means
    # no openUrl call, so macOS never gets to post its own alert.
    original = neight._macos_is_sandboxed
    original_open_url = neight.QDesktopServices.openUrl
    try:
        neight._macos_is_sandboxed = lambda: True
        target = workdir / "\u0b8f\u0bb1\u0bcd\u0bb1\u0bc1\u0bae\u0ba4\u0bbf.pdf"
        target.write_bytes(b"%PDF-1.4\n")
        odd = str(target.parent) + "//" + target.name

        seen = []
        live = []

        def _fake_open_url(url):
            seen.append(url.toLocalFile())
            # The scoped access has to be live *while* LaunchServices looks:
            # the handle must still be open at this point, not closed on the
            # way out of the helper.
            live.append(all(h.isOpen() for h in neight._sandbox_external_open_handles)
                        and bool(neight._sandbox_external_open_handles))
            return True

        neight.QDesktopServices.openUrl = _fake_open_url
        check(neight._sandbox_open_externally(odd),
              "the sandboxed external open reported failure on a readable file")
        equal(seen, [odd],
              "the external open resolved the path before Qt saw it")
        equal(live, [True],
              "the file handle was not open while openUrl ran")

        # No grant, no call: Neight reports it rather than letting macOS do it.
        seen.clear()
        missing = str(workdir / "\u0b87\u0bb2\u0bcd\u0bb2\u0bc8.pdf")
        check(not neight._sandbox_open_externally(missing),
              "the external open claimed success on an unreadable file")
        equal(seen, [], "openUrl was called for a file with no grant")
    finally:
        neight.QDesktopServices.openUrl = original_open_url
        neight._macos_is_sandboxed = original
        del neight._sandbox_external_open_handles[:]

    # --- a failed autosave must be loud, and must not lose the text ---------
    # A three-second status message is how someone keeps typing for an hour
    # into a file that is no longer being written.
    fake_home = pathlib.Path(tempfile.mkdtemp())
    original_home = neight.Path.home
    original = neight._macos_is_sandboxed
    original_write = neight._sandbox_write_text
    original_exec = neight.QMessageBox.exec
    try:
        neight.Path.home = staticmethod(lambda: fake_home)
        neight._macos_is_sandboxed = lambda: True
        # The report is modal; offscreen it would block the run forever.
        neight.QMessageBox.exec = lambda self: 0

        window = neight.Notepad(initial_file=None, restore_last_session=False)
        doomed = workdir / "\u0b95\u0bc8\u0baf\u0bc6\u0bb4\u0bc1\u0ba4\u0bcd\u0ba4\u0bc1.txt"
        doomed.write_bytes(b"old")
        window.current_path = str(doomed)
        window._grant_path = str(doomed)
        window.editor.setPlainText(CORPUS)
        window.editor.document().setModified(True)
        window._start_autosave()

        def _denied(*_a, **_kw):
            raise PermissionError(1, "Operation not permitted", str(doomed))

        neight._sandbox_write_text = _denied
        window._autosave()
        for _ in range(200):
            neight.QApplication.processEvents()
            if not window._autosave_in_progress:
                break
            time.sleep(0.01)
        equal(window._autosave_in_progress, False,
              "the failing autosave worker never reported back")

        equal(window.editor.document().isModified(), True,
              "a failed autosave left the document looking saved")
        equal(window.autosave_enabled, False,
              "autosave kept running after it failed")
        equal(window._autosave_failure_reported, True,
              "the autosave failure was not reported")

        app_dir = fake_home / "Library" / "Application Support" / "Neight"
        copies = sorted(app_dir.glob("unsaved-*"))
        equal(len(copies), 1,
              f"expected exactly one failure copy, found {[c.name for c in copies]}")
        equal(copies[0].read_text(encoding="utf-8"), CORPUS,
              "the failure copy does not hold the document text")
        equal(doomed.read_bytes(), b"old",
              "the failed autosave wrote to the target after all")

        # Closing a still-dirty window would raise the unsaved-changes prompt,
        # which offscreen has nothing to dismiss it.  The assertions above are
        # the point; the flag has served it.
        window.editor.document().setModified(False)
        window.close()
    finally:
        neight.QMessageBox.exec = original_exec
        neight._sandbox_write_text = original_write
        neight._macos_is_sandboxed = original
        neight.Path.home = original_home


def main() -> None:
    import neight

    # Point settings at a throwaway file before any window exists: Notepad
    # persists preferences as a side effect of ordinary operation (see
    # tests/_harness.py, which does the same for the harness runner).
    store = pathlib.Path(tempfile.mkdtemp()) / "settings.json"
    neight.SettingsManager._determine_active_path = lambda self: store
    # And home, for the same reason: _get_app_data_dir() builds on Path.home(),
    # and opening a file takes an advisory lock under it.  Sections below
    # redirect it again to assert on the resolved paths; they restore to this.
    run_home = pathlib.Path(tempfile.mkdtemp())
    neight.Path.home = staticmethod(lambda: run_home)

    app = neight.NeightApplication(sys.argv)  # noqa: F841 -- Qt needs one alive
    sandbox_qt_io()
    sys.exit(report(sandbox_qt_io.__doc__ or "sandbox_qt_io"))


if __name__ == "__main__":
    main()
