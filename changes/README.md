# Changes & Documentation Folder

This folder contains build system documentation and version history for Neight.

## Files in This Folder

### Build System Documentation
- **`BUILD_SYSTEM.md`** - Complete technical documentation for the build system
- **`BUILDING.md`** - Quick start guide for building Neight
- **`VERSION_SUMMARY.md`** - Summary of the enhanced build system changes

### Version History
- **`CHANGELOG.md`** - Complete changelog with all version history

## Quick Links

### Building Neight
To build Neight with automatic version incrementing:
```batch
cd ..
buildme.bat
```

See `BUILDING.md` for detailed instructions.

### Version Information
- Current build uses automatic version incrementing
- Version format: `YYYY.NNN` (e.g., 2025.004)
- Each build automatically increments the build number
- Version increment script: `../increment_version.py`

### Documentation
- **Quick Start**: Read `BUILDING.md`
- **Technical Details**: Read `BUILD_SYSTEM.md`
- **Changes Summary**: Read `VERSION_SUMMARY.md`
- **Version History**: Read `CHANGELOG.md`

## Related Files (in parent directory)
- `../buildme.bat` - Build script with auto-increment
- `../increment_version.py` - Version incrementer utility
- `../neight.py` - Main application (contains VERSION variable)
