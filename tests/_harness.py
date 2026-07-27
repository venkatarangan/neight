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
    import neight

    app = neight.NeightApplication(sys.argv)
    window = neight.Notepad(initial_file=None, restore_last_session=False)
    run(app, window)
    sys.exit(report(run.__doc__ or run.__name__))
