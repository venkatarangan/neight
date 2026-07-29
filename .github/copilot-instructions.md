# Copilot Instructions

## Tamil Text — CRITICAL RULE
Tamil strings must never be retyped, autocompleted, or modified by any AI tool or editor.

- Correct: சொல்வெளி (short ொ)
- Wrong:   சோல்வெளி (long ோ) — this word does not exist in Tamil
- Never retype, autocomplete, or modify any Tamil string in any file

## Git — Branch Policy
Always commit directly to `main`. Never create worktree branches or feature branches.

`main` is the only branch anyone works on. There is exactly one other branch,
`dist-latest`, and it is not a development branch: it holds only the current
unsigned Mac and Windows build artifacts for an external code-signing workflow
that fetches them over a `raw.githubusercontent.com` URL. The build scripts
write to it automatically and force-push it to a single commit. Never branch
from it, merge it, or commit source to it. See "Why `dist/` Isn't on GitHub" in
`DEVELOPER.md`.
