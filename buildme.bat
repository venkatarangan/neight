@echo off
REM Enhanced build script that auto-increments version number before building
echo ========================================
echo Neight Enhanced Build Script
echo ========================================
echo.

REM ── Version bump, unless --no-bump was passed ──────────────────────────────
REM
REM Mac and Windows build on separate machines, so VERSION drifts between them:
REM a macOS session bumps it and pushes, leaving Windows a build behind. A plain
REM rebuild here would bump again rather than catch up, and since both platforms'
REM artifacts are served side by side from dist-latest, the two direct downloads
REM would sit permanently one version apart -- a user comparing them on the
REM website sees two different numbers for what is the same build.
REM
REM --no-bump rebuilds at the committed VERSION instead. It also leaves neight.py
REM unmodified, so the working tree stays clean and build_msix.ps1 -- which
REM refuses to run on a dirty tree -- can follow directly without a commit in
REM between.
set "SKIP_BUMP="
if /i "%~1"=="--no-bump" set "SKIP_BUMP=1"
if defined SKIP_BUMP goto :skip_bump

python increment_version.py
if errorlevel 1 (
    echo Error: Failed to increment version number
    pause
    exit /b 1
)
goto :after_bump

:skip_bump
echo Skipping the version bump ^(--no-bump^).

:after_bump
REM Report what is actually being built, whichever path ran above.
for /f "tokens=3" %%v in ('findstr /b /c:"VERSION = " neight.py') do set "BUILD_VERSION=%%~v"
echo Building version %BUILD_VERSION%

echo.
echo Starting PyInstaller build...
echo.

REM Build from the committed Windows spec.
REM Do NOT go back to a bare "pyinstaller ... neight.py" command line: that
REM regenerates a spec file in the repo root and used to clobber the macOS
REM build input on every Windows build.
pyinstaller packaging\Neight.windows.spec
if errorlevel 1 (
    echo Error: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.

REM ── Publish the build to the 'dist-latest' branch ──────────────────────────
REM
REM dist\ is gitignored on main on purpose, so ordinary clones stay small. An
REM external code-signing workflow still needs to fetch this build over a
REM plain raw.githubusercontent.com URL, which only works for a file actually
REM committed to *some* branch. dist-latest is that branch: unrelated to
REM main's history, holding only the current Mac and Windows artifacts. It is
REM force-pushed as a single amended commit every time so it never
REM accumulates old binaries -- always exactly one commit, always replaced. A
REM macOS build publishing here separately adds its own file alongside this
REM one without touching it; this step only ever touches Neight.exe.
REM
REM Runs in a throwaway temporary clone so the real working tree (checked out
REM on main) is never touched. Best-effort: a failure here (no network, no
REM remote, nothing configured) is reported but does not fail the build -- the
REM .exe is already built at this point regardless.
echo Publishing build to the 'dist-latest' branch...

set "DIST_LATEST_BRANCH=dist-latest"
set "ARTIFACT_NAME=Neight.exe"
set "ARTIFACT_PATH=dist\%ARTIFACT_NAME%"
set "REPO_ROOT=%CD%"
set "PUBLISH_RESULT=1"

if not exist "%ARTIFACT_PATH%" (
    echo Warning: %ARTIFACT_PATH% not found; skipping dist-latest publish.
    goto :after_publish
)

set "REMOTE_URL="
for /f "delims=" %%i in ('git config --get remote.origin.url 2^>nul') do set "REMOTE_URL=%%i"
if not defined REMOTE_URL (
    echo Warning: no 'origin' remote configured; skipping dist-latest publish.
    goto :after_publish
)

set "STAGE=%TEMP%\neight-dist-latest-%RANDOM%%RANDOM%"
mkdir "%STAGE%" >nul 2>&1

pushd "%STAGE%"
git init -q
git remote add origin "%REMOTE_URL%"
git fetch -q origin %DIST_LATEST_BRANCH% >nul 2>&1
if errorlevel 1 (
    git checkout -q --orphan %DIST_LATEST_BRANCH%
) else (
    git checkout -q -b %DIST_LATEST_BRANCH% origin/%DIST_LATEST_BRANCH%
)
mkdir dist >nul 2>&1
copy /y "%REPO_ROOT%\%ARTIFACT_PATH%" "dist\%ARTIFACT_NAME%" >nul
git add dist
REM No prior commit to amend on the very first run (the orphan branch has none
REM yet) -- fall back to a plain commit only in that case, so the branch is
REM left with exactly one commit either way.
git commit -q --amend --no-edit >nul 2>&1
if errorlevel 1 (
    git commit -q -m "Latest unsigned build artifacts"
)
git push -q --force origin HEAD:%DIST_LATEST_BRANCH%
set "PUBLISH_RESULT=%ERRORLEVEL%"
popd
rmdir /s /q "%STAGE%" >nul 2>&1

:after_publish
if "%PUBLISH_RESULT%"=="0" (
    echo Published %ARTIFACT_NAME% to '%DIST_LATEST_BRANCH%'.
    echo Raw URL: https://raw.githubusercontent.com/venkatarangan/neight/%DIST_LATEST_BRANCH%/dist/%ARTIFACT_NAME%
) else (
    echo Warning: could not publish to '%DIST_LATEST_BRANCH%' ^(see above^).
    echo The local build in dist\ is unaffected; re-run this script to retry.
)
echo.

REM Keyed on whether the publish actually happened.  This banner used to
REM print unconditionally, so a build whose publish was skipped -- no
REM remote, a missing artifact, no network -- still ended by announcing it
REM had gone live, directly below the warning saying it had not.
if "%PUBLISH_RESULT%"=="0" (
    echo This build is now the public Windows download - dist-latest is
    echo what the website and README link to, so it went live above.
) else (
    echo NOT published. The public Windows download is unchanged --
    echo dist-latest still holds whatever it held before this run.
    echo What is in dist\ here is a local artifact only.
)
echo.
echo For the Microsoft Store, package it with build_msix.ps1.
echo.
pause
