"""Minimal check harness.

Deliberately not pytest: the project ships no test dependency, and these run in
CI with nothing installed beyond requirements.txt.  Import this, call check(),
then exit with report() as the process exit code.
"""
import sys

_failures: list[str] = []
_passed = 0


def check(condition: bool, message: str) -> bool:
    """Record a check.  ``message`` describes the failure, not the success."""
    global _passed
    if condition:
        _passed += 1
        return True
    _failures.append(message)
    return False


def equal(got, want, message: str) -> bool:
    return check(got == want, f"{message}: got {got!r}, want {want!r}")


def report(title: str) -> int:
    print(f"{title}: {_passed} passed, {len(_failures)} failed")
    for failure in _failures:
        # GitHub Actions renders this as an annotation on the job.
        print(f"::error::{failure}")
    return 1 if _failures else 0


def main(run) -> None:
    """Run ``run`` inside a Qt application and exit with the check result."""
    import pathlib
    import tempfile

    import neight

    # Point settings at a throwaway file before the window exists.  Notepad
    # persists preferences as a side effect of ordinary operation, so without
    # this a test run rewrites the real settings of whoever executes it -- and
    # then reads them back on the next run, making results depend on what the
    # previous test happened to leave behind.
    store = pathlib.Path(tempfile.mkdtemp()) / "settings.json"
    neight.SettingsManager._determine_active_path = lambda self: store

    # Redirect home for the same reason.  _get_app_data_dir() builds on
    # Path.home(), and opening a file now takes an advisory lock under it, so
    # without this every test run leaves lock and recovery files in the real
    # ~/Documents/Neight of whoever executes it.
    fake_home = pathlib.Path(tempfile.mkdtemp())
    neight.Path.home = staticmethod(lambda: fake_home)

    app = neight.NeightApplication(sys.argv)
    window = neight.Notepad(initial_file=None, restore_last_session=False)
    run(app, window)
    sys.exit(report(run.__doc__ or run.__name__))
