# Session Notes

Handoff records from working sessions, written so the *next* session — on
another machine, in another editor, with no memory of this one — can pick up
without re-deriving anything.

Each file covers one session: what changed, why, what was verified and how,
what was deliberately left alone, and what is still open. They are written for
a person or an AI assistant starting cold.

These are **point-in-time records of one working session, not living
documents.** A same-day continuation of the same session — picking back up
after a break, a model switch, whatever — updates its existing file, since
it's still one unfinished picture, not a new one. Once a session note is
superseded by a genuinely *later* session, it is frozen: the newer note says
what changed and links back, rather than editing history. Go by the newest
file, and by these instead for anything current:

| For | Read |
|---|---|
| What changed in each build | [`../CHANGELOG.md`](../CHANGELOG.md) |
| How to build, release, and why `dist/` isn't on GitHub | [`../DEVELOPER.md`](../DEVELOPER.md) |
| What the regression suite guards | [`../tests/README.md`](../tests/README.md) |
| Open Qt-level bugs and validation runs | [`../knownbugs/`](../knownbugs/) |

## Notes

| Date | Session |
|---|---|
| 2026-07-29 | [Trackpad zoom, click placement, build publishing, repository cleanup, docs audit](2026-07-29-trackpad-fixes-and-cleanup.md) |
| 2026-08-03 | [macOS 2026.077 signed release, and the Windows 2026.078 split forced by immutable releases](2026-08-03-macos-release-and-windows-handoff.md) |
| 2026-08-04 | [MSIX/Microsoft Store packaging built, blocked on Partner Center identity verification](2026-08-04-msix-store-packaging-pending-verification.md) |
| 2026-08-20 | [Update checker removed for App Store review, selection counts added, direct downloads moved to `dist-latest`](2026-08-20-store-distribution-and-status-bar-work.md) |
| 2026-08-21 | [Windows rebuilt at 2026.081, download shrunk 26%, file associations fixed for the Store build](2026-08-21-windows-catchup-and-clean-rebuild.md) |
| 2026-08-22 | [Mac App Store file-open permission bug fixed with security-scoped bookmarks; spurious save prompt removed; built 2026.082](2026-08-22-sandbox-file-open-and-save-prompt.md) |
