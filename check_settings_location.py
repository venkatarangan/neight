"""
Quick reference for settings.json locations in Neight

Run this to see where your settings file will be saved based on your environment.
"""
import sys
from pathlib import Path

print("=" * 80)
print("NEIGHT - Settings File Location Reference")
print("=" * 80)

# Determine paths using same logic as SettingsManager
try:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
        mode = "EXECUTABLE"
    else:
        base_dir = Path(__file__).resolve().parent
        mode = "SOURCE"
except Exception:
    base_dir = Path.cwd()
    mode = "FALLBACK"

primary_path = base_dir / "settings.json"

if sys.platform == "win32":
    appdata = Path.home() / "AppData" / "Local" / "Neight"
else:
    appdata = Path.home() / ".config" / "Neight"
fallback_path = appdata / "settings.json"

print(f"\nRunning Mode: {mode}")
print(f"\nPrimary Location (Executable Folder):")
print(f"  {primary_path}")

# Check if writable
try:
    test_file = primary_path.parent / ".write_test_temp"
    test_file.write_text("test")
    test_file.unlink()
    writable = True
except Exception:
    writable = False

print(f"  Writable: {'✓ Yes' if writable else '✗ No (will use fallback)'}")

print(f"\nFallback Location (AppData):")
print(f"  {fallback_path}")

if primary_path.exists():
    print(f"\n✓ Settings file exists in primary location")
elif fallback_path.exists():
    print(f"\n✓ Settings file exists in fallback location")
else:
    print(f"\nℹ No settings file found yet (will be created on app close)")

print(f"\nActive Location:")
if writable and (primary_path.exists() or not fallback_path.exists()):
    print(f"  → {primary_path}")
else:
    print(f"  → {fallback_path}")

print("\n" + "=" * 80)
