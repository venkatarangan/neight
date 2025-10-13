"""
Version Incrementer for Neight
Automatically increments the build number in neight.py before building.
Format: YYYY.NNN where NNN is a 3-digit build number (e.g., 2025.002 -> 2025.003)
"""

import re
import sys
from pathlib import Path
from datetime import datetime


def increment_version(version_str: str) -> str:
    """
    Increment the version number.
    Format: YYYY.NNN (e.g., 2025.002 -> 2025.003)
    If the year changes, reset to .001
    """
    match = re.match(r'(\d{4})\.(\d{3})', version_str)
    if not match:
        print(f"Error: Invalid version format: {version_str}")
        print("Expected format: YYYY.NNN (e.g., 2025.002)")
        sys.exit(1)
    
    year = int(match.group(1))
    build = int(match.group(2))
    current_year = datetime.now().year
    
    # If year is different from current year, reset to .001
    if year != current_year:
        new_version = f"{current_year}.001"
        print(f"Year changed: Resetting version to {new_version}")
    else:
        # Increment build number
        new_build = build + 1
        if new_build > 999:
            print("Warning: Build number exceeds 999. Consider resetting for new year.")
        new_version = f"{year}.{new_build:03d}"
    
    return new_version


def update_version_in_file(file_path: Path) -> tuple[str, str]:
    """
    Update the VERSION variable in neight.py
    Returns: (old_version, new_version)
    """
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    # Read the file
    content = file_path.read_text(encoding='utf-8')
    
    # Find the VERSION line
    version_pattern = r'^VERSION = "(\d{4}\.\d{3})"'
    match = re.search(version_pattern, content, re.MULTILINE)
    
    if not match:
        print("Error: Could not find VERSION variable in neight.py")
        print("Expected format: VERSION = \"YYYY.NNN\"")
        sys.exit(1)
    
    old_version = match.group(1)
    new_version = increment_version(old_version)
    
    # Replace the version
    new_content = re.sub(
        version_pattern,
        f'VERSION = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE
    )
    
    # Write back to file
    file_path.write_text(new_content, encoding='utf-8')
    
    return old_version, new_version


def main():
    script_dir = Path(__file__).parent
    neight_file = script_dir / "neight.py"
    
    print("Incrementing version number...")
    print(f"File: {neight_file}")
    print()
    
    try:
        old_version, new_version = update_version_in_file(neight_file)
        print(f"✓ Version updated: {old_version} → {new_version}")
        print()
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
