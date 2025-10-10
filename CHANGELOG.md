# Changelog

All notable changes to Neight will be documented in this file.

## [2025.001] - 2025-01-XX

### Added
- **Complete Markdown Support**
  - Insert menu (Alt+N) with all markdown elements
  - Headings 1-6 with keyboard shortcuts (Ctrl+1 through Ctrl+6)
  - Text formatting: Bold (Ctrl+B), Italic (Ctrl+I), Bold Italic (Ctrl+Shift+B)
  - Lists: Unordered, Ordered, and Checkboxes
  - Special elements: Quotes, Code blocks (Ctrl+Shift+K), Strikethrough, Highlights
  - Images and Hyperlinks (Ctrl+K) with URL validation
  - Horizontal rules and table templates
  - File support for .md (Markdown) files

- **Smart Tag Replacement**
  - Automatically removes conflicting markdown tags when inserting new ones
  - Heading changes (e.g., H3 → H2) remove old tags before adding new
  - Formatting changes (e.g., italic → bold) clean existing formatting
  - Prevents tag duplication (no more `#####` when you want `##`)

- **PDF Export**
  - Export Text to PDF for .txt files with filename header and A4 formatting
  - Export Markdown to PDF for .md files with full rendering
  - Professional styling with proper margins (15mm left/right, 20mm top/bottom)
  - CSS-styled markdown elements in PDF output
  - Contextual menu display (export options appear based on file type)
  - Font preservation in PDF output

- **Version Display**
  - Version number now shown in Help > About dialog

### Changed
- Updated file dialogs to support both .txt and .md extensions
- Menu items now appear contextually based on current file type

### Dependencies
- Added `markdown>=3.0.0` for markdown to PDF conversion

## [Initial Release] - 2025-01-XX

### Added
- Basic text editing functionality (New, Open, Save, Save As)
- Line numbers and column tracking
- Word and character count in status bar
- Auto-save with configurable intervals (2, 5, 15, 30 minutes)
- Find and Replace functionality
- Go To Line feature
- Time/Date insertion (F5)
- Google Search integration (Ctrl+E)
- Tamil Anjal keyboard layout switching
  - Double Ctrl press to toggle
  - Ctrl+, for English (India)
  - Ctrl+. for Tamil Anjal
- Font customization
- Word wrap toggle
- Dark mode support
- Settings persistence (last file, window size, font, etc.)
- Zoom in/out (Ctrl+Plus/Minus)

### Technical
- Built with PySide6 (Qt6)
- Single Python file architecture
- Portable settings with automatic location detection
- Windows keyboard layout API integration via ctypes
