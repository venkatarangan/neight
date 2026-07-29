#!/bin/bash
# Creates (or updates) a GitHub Release for the current Neight version
# and uploads the signed macOS build as the macOS artifact.
#
# Requires: GitHub CLI (gh) - https://cli.github.com
#           Run `gh auth login` once before using this script.
#
# Expected signed asset: stable/Neight-mac-arm64-signed.zip
#
# Workflow:
#   1. Run ./buildme_mac_app.sh  →  produces dist/Neight-mac-arm64-unsigned.app.zip
#   2. Sign / notarize dist/Neight.app externally
#   3. Re-zip the signed app into stable/:
#        ditto -c -k --sequesterRsrc --keepParent dist/Neight.app stable/Neight-mac-arm64-signed.zip
#   4. Run ./release_macos.sh

set -euo pipefail

# ── Sanity checks ────────────────────────────────────────────────────────────

if ! command -v gh &>/dev/null; then
    echo "Error: GitHub CLI (gh) is not installed. Get it from https://cli.github.com"
    exit 1
fi

if ! command -v git &>/dev/null; then
    echo "Error: Git is not installed or not available on PATH."
    exit 1
fi

if ! gh auth status &>/dev/null; then
    echo "Error: Not authenticated with GitHub. Run: gh auth login"
    exit 1
fi

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "Error: Run this script from inside the Neight Git repository."
    exit 1
fi

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "Error: Tracked files have uncommitted changes."
    echo "Commit and push the version bump before releasing."
    exit 1
fi

UPSTREAM_COMMIT="$(git rev-parse '@{u}' 2>/dev/null || true)"
if [ -z "${UPSTREAM_COMMIT}" ]; then
    echo "Error: The current branch has no upstream. Push main before releasing."
    exit 1
fi
if [ "$(git rev-parse HEAD)" != "${UPSTREAM_COMMIT}" ]; then
    echo "Error: HEAD does not match the upstream branch."
    echo "Push main and confirm it is synchronized before releasing."
    exit 1
fi

SIGNED_ZIP="stable/Neight-mac-arm64-signed.zip"

if [ ! -f "$SIGNED_ZIP" ]; then
    echo "Error: Signed macOS build not found: $SIGNED_ZIP"
    echo ""
    echo "Steps to create it:"
    echo "  1. Run ./buildme_mac_app.sh"
    echo "  2. Sign dist/Neight.app externally"
    echo "  3. Re-zip the signed app into stable/:"
    echo "       ditto -c -k --sequesterRsrc --keepParent dist/Neight.app stable/Neight-mac-arm64-signed.zip"
    echo "  4. Run ./release_macos.sh again"
    exit 1
fi

# ── Read version from committed source ──────────────────────────────────────

VERSION=$(git show HEAD:neight.py | python3 -c '
import re
import sys
content = sys.stdin.read()
m = re.search(r'^VERSION = "(\d{4}\.\d{3})"', content, re.MULTILINE)
print(m.group(1) if m else "")
')

if [ -z "$VERSION" ]; then
    echo "Error: Could not read VERSION from committed neight.py"
    exit 1
fi

TAG="v${VERSION}"

echo "========================================"
echo "Neight macOS Release Script"
echo "========================================"
echo ""
echo "Version : $VERSION"
echo "Tag     : $TAG"
echo "Asset   : $SIGNED_ZIP"
echo ""

# Repository rules require the tag to exist before an immutable release is
# created. Fetch it when present; otherwise create it at the verified HEAD and
# push it explicitly.
git fetch origin "refs/tags/${TAG}:refs/tags/${TAG}" 2>/dev/null || true
if TAG_COMMIT="$(git rev-list -n 1 "${TAG}" 2>/dev/null)"; then
    if [ "${TAG_COMMIT}" != "$(git rev-parse HEAD)" ]; then
        echo "Error: Tag ${TAG} points to ${TAG_COMMIT}, not HEAD $(git rev-parse HEAD)."
        exit 1
    fi
else
    git tag -a "${TAG}" -m "Neight ${VERSION}"
    git push origin "refs/tags/${TAG}"
fi

# ── Create or upload to existing release ─────────────────────────────────────

if gh release view "$TAG" &>/dev/null; then
    echo "Release $TAG already exists — uploading asset..."
    gh release upload "$TAG" "$SIGNED_ZIP" --clobber
    echo ""
    echo "✓ macOS build uploaded to release $TAG"
else
    echo "Creating new release $TAG..."
    gh release create "$TAG" "$SIGNED_ZIP" \
        --title "Neight $VERSION" \
        --notes-file release_install_notes.md
    echo ""
    echo "✓ Release $TAG created with macOS build"
fi

# ── Also upload Windows artifact if present ──────────────────────────────────

WIN_EXE="dist/Neight.exe"
if [ -f "$WIN_EXE" ]; then
    echo "Windows artifact found — uploading to same release..."
    gh release upload "$TAG" "$WIN_EXE" --clobber
    echo "✓ Neight.exe uploaded to release $TAG"
else
    echo "Note: Windows artifact not found ($WIN_EXE) — skipping."
    echo "      Run release_windows.ps1 on Windows to add it to this release."
fi

echo ""
echo "Release URL: https://github.com/venkatarangan/neight/releases/tag/$TAG"
