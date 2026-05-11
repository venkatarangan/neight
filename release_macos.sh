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

if ! gh auth status &>/dev/null; then
    echo "Error: Not authenticated with GitHub. Run: gh auth login"
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

# ── Read version from neight.py ──────────────────────────────────────────────

VERSION=$(python3 - <<'EOF'
import re
content = open("neight.py", encoding="utf-8").read()
m = re.search(r'^VERSION = "(\d{4}\.\d{3})"', content, re.MULTILINE)
print(m.group(1) if m else "")
EOF
)

if [ -z "$VERSION" ]; then
    echo "Error: Could not read VERSION from neight.py"
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

echo ""
echo "Release URL: https://github.com/venkatarangan/neight/releases/tag/$TAG"
