# Settings File Location - AppData Fallback Implementation

## Problem
When Neight is installed in `Program Files (x86)` on Windows, the application doesn't have write permissions to save `settings.json` in the same folder as the executable.

## Solution
Implemented a smart fallback mechanism in the `SettingsManager` class:

### Primary Location (Preferred)
- Same folder as the executable (or script during development)
- Used when write permissions are available

### Fallback Location (AppData)
- Windows: `%LOCALAPPDATA%\Neight\settings.json`
  - Typical path: `C:\Users\<Username>\AppData\Local\Neight\settings.json`
- Linux/Mac: `~/.config/Neight/settings.json`

## How It Works

### On First Launch
1. Checks if primary location (executable folder) is writable
2. If writable: saves `settings.json` there
3. If not writable: saves to AppData fallback location

### On Subsequent Launches
1. Checks if `settings.json` exists in primary location
2. If yes and readable: loads from there
3. If no or not readable: checks AppData location
4. Automatically migrates settings from primary to AppData if write permission is lost

### Auto-Migration
- If settings exist in primary location but app is using fallback location
- Settings are automatically copied to AppData on next save
- Ensures user preferences are preserved when permissions change

## Code Changes

### Key Methods in SettingsManager:

1. **`_determine_active_path()`**
   - Tests write permissions
   - Returns appropriate path (primary or fallback)

2. **`load()`**
   - Checks both locations
   - Handles migration automatically

3. **`save()`**
   - Tries primary location first
   - Falls back to AppData on permission error
   - Creates directories as needed

## Testing

### Test Results:
✓ Normal operation uses executable folder
✓ Falls back to AppData when write permission denied  
✓ Automatically migrates existing settings to AppData
✓ Handles both fresh installs and updates gracefully

### Test Scenarios Covered:
1. Development environment (writable)
2. Program Files installation (read-only)
3. Migration from Program Files to AppData
4. Fresh install in Program Files

## Benefits
- ✓ No permission errors
- ✓ Settings persist across app updates
- ✓ Works in both development and production
- ✓ Automatic migration of existing settings
- ✓ Cross-platform compatible
