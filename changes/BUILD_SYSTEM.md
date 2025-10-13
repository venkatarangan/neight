# Build System Documentation

## Overview

The Neight build system now includes automatic version incrementing. Each time you build, the version number is automatically incremented before creating the executable.

## Version Format

Versions follow the format: `YYYY.NNN`
- `YYYY` = Current year (4 digits)
- `NNN` = Build number (3 digits, zero-padded)

Examples: `2025.001`, `2025.002`, `2025.123`

## Build Script

### `buildme.bat`
The build script automatically:
1. Increments the version number in `neight.py`
2. Runs PyInstaller to create the executable
3. Shows clear status messages

**Usage:**
```batch
buildme.bat
```

> **Note:** The build script always increments the version. If you need to build without incrementing, manually edit the VERSION in `neight.py` after building.

## Version Incrementing

### Automatic Incrementing
The `increment_version.py` script handles version management:

- **Same year**: Increments build number (e.g., `2025.002` → `2025.003`)
- **New year**: Resets to `.001` (e.g., `2025.123` → `2026.001`)
- **Manual use**: Can be run independently for testing

**Manual usage:**
```batch
python increment_version.py
```

### Version Rules
1. Build numbers range from `001` to `999`
2. When the year changes, build number resets to `001`
3. Version is stored in `neight.py` at line 19: `VERSION = "YYYY.NNN"`
4. The version appears in Help → About dialog

## Build Process

### Step-by-Step
1. Run `buildme_enhanced.bat`
2. Script increments version (e.g., `2025.003` → `2025.004`)
3. PyInstaller creates executable with new version
4. Executable appears in `dist\Neight.exe`

### Output
- **Build artifacts**: `build\` directory
- **Executable**: `dist\Neight.exe`
- **Spec file**: `Neight.spec`

## Testing the Build

After building, test the version:
1. Run `dist\Neight.exe`
2. Go to Help → About
3. Verify the version number matches the incremented value

## Troubleshooting

### Version not incrementing
- Ensure `increment_version.py` runs without errors
- Check that `neight.py` has the correct VERSION format
- Verify Python is in your PATH

### Build fails
- Ensure PyInstaller is installed: `pip install pyinstaller`
- Check that `neight.ico` exists in the project root
- Verify all dependencies in `requirements.txt` are installed

### Wrong version displayed
- The About dialog reads from `VERSION` variable in `neight.py`
- If version seems wrong, check line 19 in `neight.py`

## Reverting to Previous Build System

If you prefer manual version control:
1. Use `buildme.bat` instead of `buildme_enhanced.bat`
2. Manually edit `VERSION = "YYYY.NNN"` in `neight.py` before building

## Version History Tracking

Remember to:
1. Update `CHANGELOG.md` with changes for each version
2. Update `README.md` current version header when releasing
3. Commit the version change to git after building
4. Tag releases in git: `git tag v2025.003`

## Example Workflow

```batch
# 1. Make your code changes
# (edit neight.py)

# 2. Run enhanced build (auto-increments version)
buildme_enhanced.bat

# 3. Test the executable
dist\Neight.exe

# 4. Update documentation
# (edit CHANGELOG.md and README.md)

# 5. Commit changes
git add .
git commit -m "Release v2025.004: Added new feature"
git tag v2025.004
git push origin main --tags
```

## Files in Build System

- `buildme_enhanced.bat` - Enhanced build script with auto-versioning
- `increment_version.py` - Version incrementer utility
- `buildme.bat` - Legacy build script (no auto-versioning)
- `Neight.spec` - PyInstaller specification file
- `neight.ico` - Application icon
- `requirements.txt` - Python dependencies

## Notes

- The version incrementer modifies `neight.py` directly
- Always commit the version change after building
- Version changes are permanent unless manually reverted
- Build numbers are local to your development environment
