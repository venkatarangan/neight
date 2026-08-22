#!/bin/bash
# Build script for Neight on macOS
#
# Usage:
#   chmod +x buildme_mac_app.sh
#   ./buildme_mac_app.sh            # increments version, builds app

set -euo pipefail

echo "========================================"
echo "Neight macOS .app Build Script"
echo "========================================"
echo ""

ARCH="$(uname -m)"
echo "Host architecture: ${ARCH}"
if [ "${ARCH}" != "arm64" ]; then
    echo "Error: This build supports Apple Silicon (arm64) only."
    echo "       Current architecture: ${ARCH}"
    exit 1
fi
echo "Build target: Apple Silicon (arm64)"
echo ""

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "Error: Python command not found: ${PYTHON_BIN}"
    echo "Create and activate the build environment documented in DEVELOPER.md."
    exit 1
fi

if ! "${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.prefix != sys.base_prefix else 1)'; then
    echo "Error: Build inside an activated virtual environment."
    echo "See the macOS build steps in DEVELOPER.md."
    exit 1
fi

if ! "${PYTHON_BIN}" -c 'import PyInstaller' >/dev/null 2>&1; then
    echo "Error: PyInstaller is not installed in the active virtual environment."
    echo "Run: python -m pip install -r requirements.txt -r requirements-build.txt"
    exit 1
fi

echo "Python: $("${PYTHON_BIN}" -c 'import sys; print(sys.executable)')"
echo ""

# The Store signing step lives on another machine and reads this file over the
# repository, so a broken one is not discovered until a submission fails.  Check
# it here, where the cost is a second.
#
# Both checks earn their place.  plutil accepts a plist whose XML is malformed
# in ways codesign's parser rejects -- notably a double hyphen inside a comment,
# which is illegal XML and cost a build already (a36b9a6, same mistake in the
# MSIX manifest).  xmllint is what catches that; codesign reports only
# "AMFIUnserializeXML: syntax error near line N".
ENTITLEMENTS="packaging/Neight.entitlements"
echo "Validating ${ENTITLEMENTS}..."
if [ ! -f "${ENTITLEMENTS}" ]; then
    echo "Error: ${ENTITLEMENTS} is missing."
    echo "       It is the source of truth for the Mac App Store sandbox entitlements."
    exit 1
fi
if ! plutil -lint "${ENTITLEMENTS}" >/dev/null; then
    echo "Error: ${ENTITLEMENTS} is not a valid property list."
    plutil -lint "${ENTITLEMENTS}"
    exit 1
fi
if command -v xmllint >/dev/null 2>&1; then
    if ! xmllint --noout "${ENTITLEMENTS}"; then
        echo "Error: ${ENTITLEMENTS} is not well-formed XML; codesign will reject it."
        exit 1
    fi
fi
echo "  OK (not applied to this build -- see DEVELOPER.md)"
echo ""

# Run the Python script to increment version
"${PYTHON_BIN}" increment_version.py

echo ""
echo "Cleaning old build artifacts..."
rm -rf build
# Both PyInstaller outputs, not just the bundle: the spec's COLLECT step writes
# dist/Neight alongside dist/Neight.app, and PyInstaller refuses to reuse a
# non-empty output directory.  Leaving it behind failed every rebuild after the
# first with "The output directory is not empty".
rm -rf dist/Neight dist/Neight.app
rm -rf __pycache__ .pytest_cache tests/__pycache__

echo ""
echo "Starting PyInstaller .app build from packaging/Neight.macos.spec..."

# Run PyInstaller using the committed spec file (preserves info_plist, argv_emulation,
# file associations and the BUNDLE step).  This previously pointed at an untracked
# Neight.spec that a clean clone did not have.
if ! "${PYTHON_BIN}" -m PyInstaller packaging/Neight.macos.spec; then
    echo ""
    echo "Error: PyInstaller command failed."
    exit 1
fi

if [ ! -d "dist/Neight.app" ]; then
    echo "Error: dist/Neight.app was not created."
    echo "PyInstaller may have encountered issues. Check output above."
    exit 1
fi

echo ""
echo "Checking the declared macOS floor against what the bundle actually needs..."
# LSMinimumSystemVersion in the spec is a claim.  Every Mach-O carries the real
# answer in LC_BUILD_VERSION's minos field, and the bundle can only run on the
# highest of them.  Claiming lower than the truth is the damaging direction:
# macOS lets the app install and it then fails to launch, which is exactly what
# 2026.081 shipped -- a Homebrew Python built for macOS 26 inside a bundle
# declaring 12.0.  Measure, and correct the claim upward if it is short, so what
# ships is true whichever interpreter built it.
DECLARED="$(/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' dist/Neight.app/Contents/Info.plist 2>/dev/null || echo '0.0')"
REQUIRED="$(
    find dist/Neight.app -type f -print0 \
        | xargs -0 file 2>/dev/null \
        | grep 'Mach-O' \
        | sed 's/:.*//' \
        | while read -r bin; do
              otool -l "$bin" 2>/dev/null \
                  | awk '/LC_BUILD_VERSION/{f=1} f&&/minos/{print $2; exit}'
          done \
        | sort -t. -k1,1n -k2,2n \
        | tail -1
)"
REQUIRED="${REQUIRED:-0.0}"
echo "  Declared: ${DECLARED}   Actually required by the binaries: ${REQUIRED}"
HIGHEST="$(printf '%s\n%s\n' "${DECLARED}" "${REQUIRED}" | sort -t. -k1,1n -k2,2n | tail -1)"
if [ "${HIGHEST}" != "${DECLARED}" ]; then
    echo ""
    echo "  WARNING: the bundle cannot run on the macOS version it claims."
    echo "           Raising LSMinimumSystemVersion to ${REQUIRED} so the store"
    echo "           and Finder refuse the install rather than letting it crash."
    echo ""
    echo "           This is almost always the build interpreter.  Homebrew's"
    echo "           Python is compiled for the macOS running it; python.org's"
    echo "           installer builds target an old floor and are what this"
    echo "           project wants.  Check yours with:"
    echo "             otool -l \"\$(python -c 'import sys,os;print(os.path.realpath(sys.executable))')\" \\"
    echo "               | awk '/LC_BUILD_VERSION/{f=1} f&&/minos/{print;exit}'"
    echo ""
    /usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion ${REQUIRED}" dist/Neight.app/Contents/Info.plist
fi

echo ""
echo "Applying ad-hoc signature (no Apple Developer account required)..."
# Ad-hoc signing improves consistency but is not notarization.  Deliberately no
# --entitlements: packaging/Neight.entitlements asks for com.apple.security.
# app-sandbox, and applying that to the direct-download build would sandbox an
# app that has no provisioning profile to make the sandbox workable.  The Store
# signing step, which runs elsewhere, is the one that passes them.
#
# --deep is gone: Apple deprecated it years ago and it signs nested code with
# the *outer* options, which is wrong for any bundle that carries entitlements.
# Signing the bundle plainly lets codesign walk it the supported way.
codesign --force --sign - dist/Neight.app

echo "Verifying code signature..."
codesign --verify --strict --verbose=2 dist/Neight.app

echo ""
echo "Creating release zip for distribution..."
ZIP_NAME="Neight-mac-${ARCH}-unsigned.app.zip"
rm -f "dist/${ZIP_NAME}"
ditto -c -k --sequesterRsrc --keepParent dist/Neight.app "dist/${ZIP_NAME}"

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "App bundle: dist/Neight.app"
echo "Release zip: dist/${ZIP_NAME}"
echo "========================================"
echo ""

# ── Publish the unsigned build to the 'dist-latest' branch ──────────────────
#
# dist/ is gitignored on main on purpose (see knownbugs/MACOS-VALIDATION-RESULTS.md,
# decision C4) so ordinary clones stay small.  An external code-signing workflow
# still needs to fetch the unsigned build over a plain raw.githubusercontent.com
# URL, which only works for a file that is actually committed to *some* branch.
# dist-latest is that branch: unrelated to main's history, holding only the
# current Mac and Windows artifacts.  It is force-pushed as a single amended
# commit every time so it never accumulates old binaries — always exactly one
# commit, always just replaced.  A Windows build publishing here later adds its
# own file alongside this one without touching it; this step only ever touches
# the macOS artifact.
#
# Runs in a throwaway temporary clone so the real working tree (checked out on
# main) is never touched.  Best-effort: a failure here (no network, no remote,
# nothing configured) is reported but does not fail the build — the app is
# already built and signed at this point regardless.
DIST_LATEST_BRANCH="dist-latest"

publish_to_dist_latest() {
    local artifact_path="$1"
    local artifact_name
    artifact_name="$(basename "${artifact_path}")"
    local repo_root
    repo_root="$(pwd)"
    local remote_url
    remote_url="$(git config --get remote.origin.url || true)"

    if [ -z "${remote_url}" ]; then
        echo "  No 'origin' remote configured; skipping."
        return 1
    fi

    local stage
    stage="$(mktemp -d "${TMPDIR:-/tmp}/neight-dist-latest.XXXXXX")"
    (
        cd "${stage}"
        git init -q
        git remote add origin "${remote_url}"
        if git fetch -q origin "${DIST_LATEST_BRANCH}" 2>/dev/null; then
            git checkout -q -b "${DIST_LATEST_BRANCH}" "origin/${DIST_LATEST_BRANCH}"
        else
            git checkout -q --orphan "${DIST_LATEST_BRANCH}"
        fi
        mkdir -p dist
        cp "${repo_root}/${artifact_path}" "dist/${artifact_name}"
        git add dist
        # No prior commit to amend on the very first run (the orphan branch has
        # none yet) -- fall back to a plain commit only in that case, so the
        # branch is left with exactly one commit either way.
        git commit -q --amend --no-edit >/dev/null 2>&1 \
            || git commit -q -m "Latest unsigned build artifacts"
        git push -q --force origin "HEAD:${DIST_LATEST_BRANCH}"
    )
    local rc=$?
    rm -rf "${stage}"
    return ${rc}
}

echo "Publishing unsigned build to the '${DIST_LATEST_BRANCH}' branch..."
if publish_to_dist_latest "dist/${ZIP_NAME}"; then
    echo "Published ${ZIP_NAME} to '${DIST_LATEST_BRANCH}'."
    echo "Raw URL: https://raw.githubusercontent.com/venkatarangan/neight/${DIST_LATEST_BRANCH}/dist/${ZIP_NAME}"
else
    echo "Warning: could not publish to '${DIST_LATEST_BRANCH}' (see above)."
    echo "The local build in dist/ is unaffected; re-run this script to retry."
fi
echo ""

echo "Friend install instructions (unsigned app):"
echo "1) Download and unzip ${ZIP_NAME}"
echo "2) Drag Neight.app to Applications"
echo "3) First launch: right-click Neight.app -> Open -> Open"
echo "4) If blocked, run: xattr -dr com.apple.quarantine /Applications/Neight.app"
echo ""
echo "To publish a signed release:"
echo "  Sign dist/Neight.app externally, then re-zip it into stable/:"
echo "    ditto -c -k --sequesterRsrc --keepParent dist/Neight.app stable/Neight-mac-arm64-signed.zip"
echo "  Then run to release to GitHub and end users:"
echo "    ./release_macos.sh"
echo ""
echo "========================================"
echo "REMINDER: Run ./release_macos.sh to push"
echo "the new release to GitHub Releases."
echo "Until you do, end users will NOT see the"
echo "update badge in Neight."
echo "========================================"
