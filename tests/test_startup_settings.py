"""Startup must never persist a font the user did not choose.

Regression guard for the multi-window font loss fixed in 2026.070 (CHANGELOG.md).
Applying settings used to emit `toggled()` from the checkable actions being
synchronised, and those handlers saved the half-applied window — writing Qt's
default font over the stored one, because the font is applied at the end of that
method.

Every write is inspected rather than the final file contents: a legitimate
first-run seeding write happens for an incomplete settings file, and a later
write can repair an earlier bad one, masking the bug depending on which keys the
store happens to hold. The invariant that matters is that no write during
startup may carry a font the user never chose.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from _harness import check, equal, report  # noqa: E402

STORED_FAMILY = "Courier New"
STORED_SIZE = 17


def main() -> None:
    import neight

    store = pathlib.Path(tempfile.mkdtemp()) / "settings.json"
    # Every one of these differs from its QAction construction default, so each
    # would emit toggled() while settings are being applied.
    store.write_text(json.dumps({
        "font_family": STORED_FAMILY,
        "font_size": STORED_SIZE,
        "unicode_substring_highlight": True,
        "word_wrap": False,
        "line_numbers_visible": False,
        "status_show_words": False,
    }), encoding="utf-8")

    # Point the store at a temporary file rather than writing one next to the
    # script.  The real location is platform-specific and has already moved once
    # (macOS now uses Application Support), and a guard that wrote to the wrong
    # place would still pass while testing nothing.  This also keeps the run from
    # touching the settings of whoever executes it.
    neight.SettingsManager._determine_active_path = lambda self: store

    writes = []
    original_save = neight.SettingsManager.save
    neight.SettingsManager.save = lambda self, data: (
        writes.append((data.get("font_family"), data.get("font_size")))
        or original_save(self, data))

    app = neight.NeightApplication(sys.argv)
    window = neight.Notepad(initial_file=None, restore_last_session=False)

    bad = [w for w in writes if w != (STORED_FAMILY, STORED_SIZE)]
    check(not bad,
          f"startup persisted a font the user never chose: {bad} "
          f"(all writes: {writes})")

    # Proves the stored settings were actually read.  Without this the guard
    # would pass on a build that silently ignored the settings file entirely.
    font = window.editor.font()
    equal(font.family(), STORED_FAMILY, "font family after startup")
    equal(font.pointSize(), STORED_SIZE, "font size after startup")

    print(f"startup made {len(writes)} write(s)")
    sys.exit(report("Startup settings"))


if __name__ == "__main__":
    main()
