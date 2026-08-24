"""One document, one owning instance.

Every Neight window is its own *process* -- new_window() spawns one, and
NeightApplication keeps a single _main_window that Finder's "Open With" reuses
rather than opening a second window in-process.  So two windows on one file
means two processes writing it, and nothing used to stop them: both ran
autosave against the same path, and neither ever noticed the file changing
underneath it.  Whichever autosave landed last won, silently.

This is not a sandbox problem -- New Window is a separate process on Windows
too -- so nothing here forces the macOS gate on.  It is checked with a real
second QLockFile rather than a spawned process: Qt refuses a second lock even
within one process (verified before this test was written), so the cheaper
form exercises the same refusal the real case produces.

Tamil filenames throughout, on the same reasoning as test_sandbox_qt_io: the
lock key is a hash of the path, and a multi-byte name is where an encoding
assumption in that hash would show up.
"""
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from _harness import check, equal, report  # noqa: E402

CORPUS = (
    "இது ஒரு சோதனை.\n"
    "நெய்த் தமிழில் எழுதுவதற்கான ஒரு எடிட்டர்.\n"
    "Plain English line, with punctuation — and a dash.\n"
)


def document_lock() -> None:
    """Document ownership across instances"""
    import neight

    workdir = pathlib.Path(tempfile.mkdtemp())

    # --- the key -----------------------------------------------------------
    # Deliberately the opposite choice from _grant_path: two instances that
    # reached the same file by differently spelled paths must still collide.
    doc = workdir / "பகிரப்பட்ட.txt"
    doc.write_text(CORPUS, encoding="utf-8")
    odd = str(doc.parent) + "//" + doc.name
    equal(str(neight.Notepad._document_lock_path(odd)),
          str(neight.Notepad._document_lock_path(str(doc))),
          "two spellings of one path produced different locks")
    check(neight.Notepad._document_lock_path(str(doc))
          != neight.Notepad._document_lock_path(str(workdir / "other.txt")),
          "two different files shared one lock")
    # Never beside the user's file: inside the sandbox the panel grants the
    # chosen file, not its directory, so a sibling there cannot be created.
    check(neight.Notepad._document_lock_path(str(doc)).parent != doc.parent,
          "the lock was placed beside the user's file")

    # --- a window with no contender owns its document -----------------------
    window = neight.Notepad(initial_file=None, restore_last_session=False)
    check(window._holds_document_lock(), "an untitled document is not owned")
    check(window._open_file_path(str(doc), notify_errors=False), "the open failed")
    check(window._holds_document_lock(),
          "the only window open on a file did not own it")
    check("open in another window" not in window.windowTitle(),
          f"the sole owner's title claims a contender: {window.windowTitle()}")

    # --- a second instance does not ----------------------------------------
    contended = workdir / "போட்டி.txt"
    contended.write_text(CORPUS, encoding="utf-8")
    rival = neight.QLockFile(str(neight.Notepad._document_lock_path(str(contended))))
    rival.setStaleLockTime(0)
    check(rival.tryLock(0), "the stand-in for the other instance could not lock")

    second = neight.Notepad(initial_file=None, restore_last_session=False)
    # notify_errors=False keeps the "already open" dialog from blocking a run
    # that has nothing to dismiss it.  The refusal itself is what is tested.
    check(second._open_file_path(str(contended), notify_errors=False),
          "a file open elsewhere refused to open at all -- it must stay editable")
    check(not second._holds_document_lock(),
          "the second instance claimed a document another instance owns")
    check("open in another window" in second.windowTitle(),
          f"the non-owner's title does not say so: {second.windowTitle()}")
    check(second._document_lock_owner_pid() is not None,
          "the owning PID could not be read, so the warning cannot name it")

    # --- the non-owner's autosave must not touch the file -------------------
    before = contended.read_bytes()
    second.editor.setPlainText("இது எழுதப்படக் கூடாது\n")
    second.editor.document().setModified(True)
    second._autosave()
    for _ in range(200):
        neight.QApplication.processEvents()
        if not second._recovery_in_progress:
            break
        time.sleep(0.01)
    equal(contended.read_bytes(), before,
          "the non-owner's autosave overwrote the owning instance's file")
    check(second.editor.document().isModified(),
          "the non-owner's autosave cleared the dirty flag without writing")
    recovery = second._recovery_path
    check(recovery is not None and recovery.exists(),
          "the non-owner's autosave kept no recovery copy of the typing")
    if recovery is not None and recovery.exists():
        equal(recovery.read_text(encoding="utf-8"), "இது எழுதப்படக் கூடாது\n",
              "the recovery copy does not hold what was typed")

    # --- a manual save is still allowed -------------------------------------
    # The user is present and was told when the file opened; refusing here
    # would take away a save they asked for by hand.
    check(second.save_file(), "the non-owner could not save by hand")
    equal(contended.read_text(encoding="utf-8"), "இது எழுதப்படக் கூடாது\n",
          "the non-owner's manual save did not reach the file")

    # --- ownership follows the document ------------------------------------
    moved = workdir / "நகர்த்தப்பட்டது.txt"
    check(window._acquire_document_lock(str(moved)),
          "Save As could not take the new file's lock")
    held_elsewhere = neight.QLockFile(str(neight.Notepad._document_lock_path(str(moved))))
    held_elsewhere.setStaleLockTime(0)
    check(not held_elsewhere.tryLock(0),
          "the window did not actually hold the file it moved to")
    # The first document is given up by the acquire, so a newcomer can take it.
    successor = neight.QLockFile(str(neight.Notepad._document_lock_path(str(doc))))
    successor.setStaleLockTime(0)
    check(successor.tryLock(0),
          "the previous document stayed locked after the window moved on")
    successor.unlock()

    # --- new_file and close give the document up ----------------------------
    window._release_document_lock()
    check(window._open_file_path(str(doc), notify_errors=False), "the reopen failed")
    check(window._holds_document_lock(), "the reopen did not take the lock")
    window.new_file()
    retaker = neight.QLockFile(str(neight.Notepad._document_lock_path(str(doc))))
    retaker.setStaleLockTime(0)
    check(retaker.tryLock(0), "New did not release the document")
    retaker.unlock()

    check(window._open_file_path(str(doc), notify_errors=False), "the third open failed")
    window.editor.document().setModified(False)
    window.close()
    after_close = neight.QLockFile(str(neight.Notepad._document_lock_path(str(doc))))
    after_close.setStaleLockTime(0)
    check(after_close.tryLock(0), "closing the window did not release the document")
    after_close.unlock()

    rival.unlock()
    second.editor.document().setModified(False)
    second.close()


def main() -> None:
    import neight

    store = pathlib.Path(tempfile.mkdtemp()) / "settings.json"
    neight.SettingsManager._determine_active_path = lambda self: store
    # _get_app_data_dir() builds on Path.home(), and this test is entirely
    # about the lock files that land under it.  One fixed directory, not a
    # fresh mkdtemp per call: every instance has to resolve to the same lock
    # folder or nothing here can contend for anything.
    run_home = pathlib.Path(tempfile.mkdtemp())
    neight.Path.home = staticmethod(lambda: run_home)

    app = neight.NeightApplication(sys.argv)  # noqa: F841 -- Qt needs one alive
    document_lock()
    sys.exit(report(document_lock.__doc__ or "document_lock"))


if __name__ == "__main__":
    main()
