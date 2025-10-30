# python -m pip install --upgrade pip
# python -m pip install PySide6
# python -m pip install pyinstaller

import sys
import json
import re
import time
import webbrowser
import ctypes
import urllib.request
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

# Version information
VERSION = "2025.006"


try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QPlainTextEdit, QFileDialog, QMessageBox,
        QStatusBar, QWidget, QLabel, QFontDialog, QInputDialog
    )
    # In Qt6 / PySide6 QAction and QShortcut live in QtGui (not QtWidgets)
    from PySide6.QtGui import QKeySequence, QPainter, QFont, QTextCursor, QAction, QShortcut, QColor, QGuiApplication
    from PySide6.QtCore import Qt, QRect, QFileInfo, QTimer
    QT_LIB = "PySide6"
except Exception:  # Fallback to PyQt5 if PySide6 is unavailable
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QPlainTextEdit, QFileDialog, QMessageBox,
        QAction, QStatusBar, QWidget, QLabel, QFontDialog, QInputDialog, QShortcut
    )
    from PyQt5.QtGui import QKeySequence, QPainter, QFont, QTextCursor, QColor, QGuiApplication
    from PyQt5.QtCore import Qt, QRect, QFileInfo, QTimer
    QT_LIB = "PyQt5"

# ------------------------------------
# Keyboard layout switching (Windows)
# ------------------------------------
if sys.platform == "win32":
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    KLF_ACTIVATE = 0x00000001
    KLF_REORDER = 0x00000008
    KLF_SETFORPROCESS = 0x00000100
    HKL_NEXT = 1
    HKL_PREV = 0

    def load_hkl(klid: str) -> int:
        """Load a keyboard layout by its identifier string."""
        hkl = user32.LoadKeyboardLayoutW(ctypes.c_wchar_p(klid), KLF_ACTIVATE | KLF_REORDER)
        if not hkl:
            error = ctypes.get_last_error()
            raise OSError(f"LoadKeyboardLayoutW failed with error {error}")
        return hkl

    def activate_hkl(hkl: int) -> None:
        """Activate a keyboard layout."""
        # Use KLF_SETFORPROCESS to set for the entire process
        # Note: ActivateKeyboardLayout returns the previous HKL, not an error code
        result = user32.ActivateKeyboardLayout(hkl, KLF_SETFORPROCESS)
        # The function returns the previously active HKL, so result could be any value
        # We don't check for error here as the function typically succeeds

    # Tamil Anjal keyboard layout identifier
    # 0x0449 = Tamil language, 0003 = Tamil Anjal input method
    TAMIL_ANJAL = "00030449"
    
    # English India keyboard layout identifier
    # 0x4009 = English (India)
    EN_IN = "00004009"

    def switch_to_tamil_anjal():
        """Switch to Tamil Anjal keyboard layout."""
        hkl = load_hkl(TAMIL_ANJAL)
        activate_hkl(hkl)

    def switch_to_english_india():
        """Switch to English India keyboard layout."""
        hkl = load_hkl(EN_IN)
        activate_hkl(hkl)
else:
    def switch_to_tamil_anjal():
        pass

    def switch_to_english_india():
        pass


# ---------------------
# Settings persistence
# ---------------------
class SettingsManager:
    def __init__(self, filename: str = "settings.json", legacy_files: tuple[str, ...] = ("config.json",)):
        # Determine the executable/script directory
        try:
            if getattr(sys, "frozen", False):  # PyInstaller executable
                base_dir = Path(sys.executable).resolve().parent
            else:
                base_dir = Path(__file__).resolve().parent
        except Exception:
            base_dir = Path.cwd()
        
        # Primary path (same folder as executable/script)
        self.primary_path = base_dir / filename
        
        # Fallback path (AppData\Local\Neight)
        if sys.platform == "win32":
            appdata = Path.home() / "AppData" / "Local" / "Neight"
        else:
            # For non-Windows systems, use appropriate config directory
            appdata = Path.home() / ".config" / "Neight"
        self.fallback_path = appdata / filename
        
        # Legacy paths for migration
        self.legacy_paths = tuple((base_dir / legacy) for legacy in legacy_files)
        
        # Determine which path to use
        self.path = self._determine_active_path()

    def _determine_active_path(self) -> Path:
        """Determine which path to use for settings (primary or fallback)."""
        # If primary path exists and is readable, use it
        if self.primary_path.exists():
            try:
                # Test if we can read it
                self.primary_path.read_text(encoding="utf-8")
                return self.primary_path
            except Exception:
                pass
        
        # If fallback path exists, use it
        if self.fallback_path.exists():
            return self.fallback_path
        
        # Neither exists - try to determine which one we can write to
        # Try primary first
        try:
            self.primary_path.parent.mkdir(parents=True, exist_ok=True)
            # Test write permission by creating a temporary file
            test_file = self.primary_path.parent / ".write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            return self.primary_path
        except Exception:
            pass
        
        # Fall back to AppData
        return self.fallback_path

    def _load_file(self, path: Path) -> Optional[dict]:
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return None

    def load(self) -> dict:
        # Try to load from the active path
        data = self._load_file(self.path)
        if data is not None:
            return data

        # If active path is fallback, also check primary path
        if self.path == self.fallback_path:
            primary_data = self._load_file(self.primary_path)
            if primary_data is not None:
                # Migrate to fallback location
                self.save(primary_data)
                return primary_data
        
        # Check legacy paths for migration
        for legacy_path in self.legacy_paths:
            legacy_data = self._load_file(legacy_path)
            if legacy_data is not None:
                self.save(legacy_data)
                try:
                    legacy_path.unlink()
                except Exception:
                    pass
                return legacy_data

        return {}

    def save(self, data: dict) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            # If save fails and we're using primary path, try fallback
            if self.path == self.primary_path:
                try:
                    self.path = self.fallback_path
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass  # Non-fatal


# -------------------------------------
# Text editor with line-number sidebar
# -------------------------------------
class LineNumberArea(QWidget):
    def __init__(self, editor: 'CodeEditor'):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return self.editor.lineNumberAreaSizeHint()

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Flags first so slots can use them safely
        self._highlight_current_line = True
        self._wrap_enabled = True
        self._click_count = 0
        self._last_click_ts = 0.0

        self.lineNumberArea = LineNumberArea(self)

        # Signals to keep the number area in sync
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.updateCurrentLineHighlight)

        self.updateLineNumberAreaWidth(0)
        self.setWordWrap(True)
        self.updateCurrentLineHighlight()

    # ----- Word wrap -----
    def setWordWrap(self, enabled: bool):
        self._wrap_enabled = bool(enabled)
        mode = QPlainTextEdit.WidgetWidth if self._wrap_enabled else QPlainTextEdit.NoWrap
        self.setLineWrapMode(mode)
        self.updateLineNumberAreaWidth(0)

    def isWordWrap(self) -> bool:
        return self._wrap_enabled

    # ----- Line numbers plumbing -----
    def lineNumberAreaWidth(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        space = 6 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def lineNumberAreaSizeHint(self):
        return self.sizeHint().expandedTo(self.viewport().size())

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), self.palette().alternateBase())

        # Determine if we're in dark mode by checking the background lightness
        bg_color = self.palette().window().color()
        is_dark_mode = bg_color.lightness() < 128
        
        # Use white text for dark mode, black for light mode
        text_color = QColor(Qt.white if is_dark_mode else Qt.black)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(text_color)
                painter.drawText(0, int(top), self.lineNumberArea.width() - 6, self.fontMetrics().height(),
                                 Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def updateCurrentLineHighlight(self):
        if not getattr(self, "_highlight_current_line", True):
            return
        # Keep simple; rely on palette for current line appearance.
        pass

    @staticmethod
    def _normalize_search_text(text: str) -> str:
        if not text:
            return ""
        cleaned = text.replace("\u2029", "\n")
        return " ".join(cleaned.split())

    def _trigger_search(self, query: str):
        cleaned = self._normalize_search_text(query)
        if not cleaned:
            return
        handler = getattr(self.window(), "launch_web_search", None)
        if callable(handler):
            handler(cleaned)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            app = QApplication.instance()
            interval_ms = app.doubleClickInterval() if app else QApplication.doubleClickInterval()
            interval = interval_ms / 1000.0
            now = time.monotonic()
            if now - self._last_click_ts <= interval:
                self._click_count += 1
            else:
                self._click_count = 1
            self._last_click_ts = now

            if self._click_count == 3:
                if self._handle_triple_click(event):
                    event.accept()
                    self._click_count = 0
                    return
                self._click_count = 0
        else:
            self._click_count = 0

        super().mousePressEvent(event)

    def _handle_triple_click(self, event) -> bool:
        cursor = self.cursorForPosition(event.pos())
        if cursor.isNull():
            return False
        cursor.select(QTextCursor.WordUnderCursor)
        text = self._normalize_search_text(cursor.selectedText())
        if not text:
            return False

        self.setTextCursor(cursor)
        self._trigger_search(text)
        return True

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu(event.pos())
        selected_text = self._normalize_search_text(self.textCursor().selectedText())
        if selected_text:
            display_text = selected_text if len(selected_text) <= 48 else f"{selected_text[:45]}..."
            search_action = QAction(f'Search Google for "{display_text}"', menu)
            search_action.triggered.connect(
                lambda checked=False, text=selected_text: self._trigger_search(text)
            )
            before_action = menu.actions()[0] if menu.actions() else None
            menu.insertAction(before_action, search_action)
            if before_action is not None:
                menu.insertSeparator(before_action)
        menu.exec(event.globalPos())
        menu.deleteLater()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            steps = int(delta / 120) if delta else 0
            if steps == 0 and not delta:
                pixel_delta = event.pixelDelta().y()
                steps = 1 if pixel_delta > 0 else -1 if pixel_delta < 0 else 0
            handler = getattr(self.window(), "_change_font_size", None)
            if callable(handler) and steps != 0:
                direction = 1 if steps > 0 else -1
                for _ in range(abs(steps)):
                    handler(direction)
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            key = event.key()
            plus_keys = [Qt.Key_Plus, Qt.Key_Equal]
            minus_keys = [Qt.Key_Minus, Qt.Key_Underscore]
            for attr in ("Key_KP_Add", "KeypadPlus"):
                extra = getattr(Qt, attr, None)
                if extra is not None:
                    plus_keys.append(extra)
            for attr in ("Key_KP_Subtract", "KeypadMinus"):
                extra = getattr(Qt, attr, None)
                if extra is not None:
                    minus_keys.append(extra)

            if key in tuple(plus_keys):
                handler = getattr(self.window(), "_change_font_size", None)
                if callable(handler):
                    handler(1)
                    event.accept()
                    return
            elif key in tuple(minus_keys):
                handler = getattr(self.window(), "_change_font_size", None)
                if callable(handler):
                    handler(-1)
                    event.accept()
                    return
        super().keyPressEvent(event)

    def paste_plain_text(self):
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return
        mime = clipboard.mimeData()
        if mime and mime.hasText():
            text = mime.text()
            if text:
                self.insertPlainText(text)

    def insertFromMimeData(self, source):
        if source is not None:
            if QGuiApplication.keyboardModifiers() & Qt.ShiftModifier:
                if source.hasText():
                    text = source.text()
                    if text:
                        self.insertPlainText(text)
                        return
        super().insertFromMimeData(source)


# ---------------------
# Main window
# ---------------------
class Notepad(QMainWindow):
    def __init__(self, initial_file: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("Untitled - Neight")
        self.resize(1000, 650)

        self.settings = SettingsManager()
        self.default_directory = Path.home()
        self._restore_maximized = False
        self._initial_file = initial_file
        self._last_session_file = None

        self.editor = CodeEditor(self)
        self.setCentralWidget(self.editor)

        self.status = QStatusBar(self)
        self.setStatusBar(self.status)

        # Status widgets
        self.count_label = QLabel("Words: 0 | Chars: 0", self)
        self.pos_label = QLabel("Ln 1, Col 1", self)
        self.layout_label = QLabel("Keyboard: English India", self)
        self.status.addPermanentWidget(self.count_label)
        self.status.addPermanentWidget(self.pos_label)
        self.status.addPermanentWidget(self.layout_label)

        self.current_path = None
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_enabled = False
        
        # Keyboard layout switching state
        self._current_layout = 0  # 0 = English India, 1 = Tamil Anjal
        self._ctrl_press_time = 0  # For double Ctrl detection
        self._ctrl_press_timer = QTimer(self)
        self._ctrl_press_timer.setSingleShot(True)
        self._ctrl_press_timer.timeout.connect(self._reset_ctrl_press)
        
        self._create_actions()
        self._create_menus()
        self._connect_signals()
        self._install_shortcuts()
        self._install_layout_shortcuts()

        self._load_preferences()
        self._update_status_bar()
        self._update_export_menu_visibility()

        if initial_file:
            self._load_initial_path(initial_file)

    # --- UI setup ---
    def _create_actions(self):
        # File
        self.new_act = QAction("New", self)
        self.new_act.setShortcut(QKeySequence.New)  # Ctrl+N / Cmd+N

        self.open_act = QAction("Open…", self)
        self.open_act.setShortcut(QKeySequence.Open)  # Ctrl+O / Cmd+O

        self.save_act = QAction("&Save", self)
        self.save_act.setShortcut(QKeySequence.Save)  # Ctrl+S / Cmd+S

        self.save_as_act = QAction("Save &As…", self)
        self.save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))

        self.export_text_pdf_act = QAction("Export Text to PDF…", self)
        self.export_md_pdf_act = QAction("Export Markdown to PDF…", self)

        self.exit_act = QAction("E&xit", self)
        self.exit_act.setShortcut(QKeySequence.Quit)

        # Edit
        self.undo_act = QAction("Undo", self)
        self.undo_act.setShortcut(QKeySequence.Undo)  # Ctrl+Z / Cmd+Z

        self.redo_act = QAction("Redo", self)
        self.redo_act.setShortcut(QKeySequence.Redo)  # Ctrl+Y / Shift+Cmd+Z

        self.cut_act = QAction("Cut", self)
        self.cut_act.setShortcut(QKeySequence.Cut)

        self.copy_act = QAction("Copy", self)
        self.copy_act.setShortcut(QKeySequence.Copy)

        self.paste_act = QAction("Paste", self)
        self.paste_act.setShortcut(QKeySequence.Paste)

        self.select_all_act = QAction("Select All", self)
        self.select_all_act.setShortcut(QKeySequence.SelectAll)

        # Find / Replace / Go To / Time-Date
        self.find_act = QAction("Find…", self)
        self.find_act.setShortcut(QKeySequence.Find)  # Ctrl+F / Cmd+F

        self.find_next_act = QAction("Find Next", self)
        self.find_next_act.setShortcut(QKeySequence("F3"))  # F3

        self.replace_act = QAction("Replace…", self)
        self.replace_act.setShortcut(QKeySequence.Replace)  # Ctrl+H

        self.replace_all_act = QAction("Replace All…", self)

        self.goto_act = QAction("Go To…", self)
        self.goto_act.setShortcut(QKeySequence("Ctrl+G"))

        self.time_date_act = QAction("Time/Date", self)
        self.time_date_act.setShortcut(QKeySequence("F5"))

        self.search_web_act = QAction("Search with Google", self)
        self.search_web_act.setShortcut(QKeySequence("Ctrl+E"))

        self.collapse_blank_lines_act = QAction("Collapse Blank Lines", self)

        # Insert - Markdown heading actions
        self.insert_h1_act = QAction("Heading 1", self)
        self.insert_h1_act.setShortcut(QKeySequence("Ctrl+1"))
        
        self.insert_h2_act = QAction("Heading 2", self)
        self.insert_h2_act.setShortcut(QKeySequence("Ctrl+2"))
        
        self.insert_h3_act = QAction("Heading 3", self)
        self.insert_h3_act.setShortcut(QKeySequence("Ctrl+3"))
        
        self.insert_h4_act = QAction("Heading 4", self)
        self.insert_h4_act.setShortcut(QKeySequence("Ctrl+4"))
        
        self.insert_h5_act = QAction("Heading 5", self)
        self.insert_h5_act.setShortcut(QKeySequence("Ctrl+5"))
        
        self.insert_h6_act = QAction("Heading 6", self)
        self.insert_h6_act.setShortcut(QKeySequence("Ctrl+6"))
        
        self.insert_ul_act = QAction("Unordered List", self)
        self.insert_ol_act = QAction("Ordered List", self)
        self.insert_checkbox_act = QAction("Checkbox", self)
        
        # Insert - Text formatting actions
        self.insert_emphasis_act = QAction("Emphasis (Italic)", self)
        self.insert_emphasis_act.setShortcut(QKeySequence("Ctrl+I"))
        
        self.insert_strong_act = QAction("Strong (Bold)", self)
        self.insert_strong_act.setShortcut(QKeySequence("Ctrl+B"))
        
        self.insert_strong_emphasis_act = QAction("Strong Emphasis (Bold Italic)", self)
        self.insert_strong_emphasis_act.setShortcut(QKeySequence("Ctrl+Shift+B"))
        
        self.insert_highlight_act = QAction("Highlight", self)
        self.insert_strikethrough_act = QAction("Strikethrough", self)
        self.insert_quote_act = QAction("Quote", self)
        self.insert_code_block_act = QAction("Code Block", self)
        self.insert_code_block_act.setShortcut(QKeySequence("Ctrl+Shift+K"))
        
        # Insert - Special insertions
        self.insert_image_act = QAction("Image...", self)
        self.insert_hyperlink_act = QAction("Hyperlink...", self)
        self.insert_hyperlink_act.setShortcut(QKeySequence("Ctrl+K"))
        
        # Insert - Other markdown features
        self.insert_hr_act = QAction("Horizontal Rule", self)
        self.insert_table_act = QAction("Table Template", self)

        # Format
        self.wrap_act = QAction("Word Wrap", self, checkable=True)
        self.wrap_act.setChecked(True)

        self.font_act = QAction("Font…", self)

        # Auto-save
        self.autosave_disabled_act = QAction("Disabled", self, checkable=True)
        self.autosave_2min_act = QAction("Every 2 minutes", self, checkable=True)
        self.autosave_5min_act = QAction("Every 5 minutes", self, checkable=True)
        self.autosave_15min_act = QAction("Every 15 minutes", self, checkable=True)
        self.autosave_30min_act = QAction("Every 30 minutes", self, checkable=True)

        # Help
        self.about_act = QAction("About", self)

    def _create_menus(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.new_act)
        file_menu.addAction(self.open_act)
        file_menu.addSeparator()
        file_menu.addAction(self.save_act)
        file_menu.addAction(self.save_as_act)
        file_menu.addSeparator()
        file_menu.addAction(self.export_text_pdf_act)
        file_menu.addAction(self.export_md_pdf_act)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_act)
        
        # Store file menu for later updates
        self.file_menu = file_menu

        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction(self.undo_act)
        edit_menu.addAction(self.redo_act)
        edit_menu.addSeparator()
        edit_menu.addAction(self.cut_act)
        edit_menu.addAction(self.copy_act)
        edit_menu.addAction(self.paste_act)
        edit_menu.addSeparator()
        edit_menu.addAction(self.find_act)
        edit_menu.addAction(self.find_next_act)
        edit_menu.addAction(self.replace_act)
        edit_menu.addAction(self.replace_all_act)
        edit_menu.addAction(self.goto_act)
        edit_menu.addSeparator()
        edit_menu.addAction(self.search_web_act)
        edit_menu.addSeparator()
        edit_menu.addAction(self.select_all_act)
        edit_menu.addAction(self.time_date_act)
        edit_menu.addSeparator()
        edit_menu.addAction(self.collapse_blank_lines_act)

        # Insert menu (Alt+N is handled by the & in "I&nsert")
        insert_menu = menubar.addMenu("I&nsert")
        
        # Headings submenu
        headings_menu = insert_menu.addMenu("Heading")
        headings_menu.addAction(self.insert_h1_act)
        headings_menu.addAction(self.insert_h2_act)
        headings_menu.addAction(self.insert_h3_act)
        headings_menu.addAction(self.insert_h4_act)
        headings_menu.addAction(self.insert_h5_act)
        headings_menu.addAction(self.insert_h6_act)
        
        insert_menu.addSeparator()
        insert_menu.addAction(self.insert_ul_act)
        insert_menu.addAction(self.insert_ol_act)
        insert_menu.addAction(self.insert_checkbox_act)
        
        insert_menu.addSeparator()
        insert_menu.addAction(self.insert_emphasis_act)
        insert_menu.addAction(self.insert_strong_act)
        insert_menu.addAction(self.insert_strong_emphasis_act)
        insert_menu.addAction(self.insert_highlight_act)
        insert_menu.addAction(self.insert_strikethrough_act)
        
        insert_menu.addSeparator()
        insert_menu.addAction(self.insert_quote_act)
        insert_menu.addAction(self.insert_code_block_act)
        
        insert_menu.addSeparator()
        insert_menu.addAction(self.insert_image_act)
        insert_menu.addAction(self.insert_hyperlink_act)
        
        insert_menu.addSeparator()
        insert_menu.addAction(self.insert_hr_act)
        insert_menu.addAction(self.insert_table_act)

        format_menu = menubar.addMenu("F&ormat")
        format_menu.addAction(self.wrap_act)
        format_menu.addAction(self.font_act)

        autosave_menu = format_menu.addMenu("Auto-save")
        autosave_menu.addAction(self.autosave_disabled_act)
        autosave_menu.addAction(self.autosave_2min_act)
        autosave_menu.addAction(self.autosave_5min_act)
        autosave_menu.addAction(self.autosave_15min_act)
        autosave_menu.addAction(self.autosave_30min_act)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self.about_act)

    def _connect_signals(self):
        # File
        self.new_act.triggered.connect(self.new_file)
        self.open_act.triggered.connect(self.open_file)
        self.save_act.triggered.connect(self.save_file)
        self.save_as_act.triggered.connect(self.save_file_as)
        self.export_text_pdf_act.triggered.connect(self._export_text_to_pdf)
        self.export_md_pdf_act.triggered.connect(self._export_markdown_to_pdf)
        self.exit_act.triggered.connect(self.close)

        # Edit
        self.undo_act.triggered.connect(self.editor.undo)
        self.redo_act.triggered.connect(self.editor.redo)
        self.cut_act.triggered.connect(self.editor.cut)
        self.copy_act.triggered.connect(self.editor.copy)
        self.paste_act.triggered.connect(self.editor.paste)
        self.select_all_act.triggered.connect(self.editor.selectAll)
        self.find_act.triggered.connect(self.find_text)
        self.find_next_act.triggered.connect(self.find_next)
        self.replace_act.triggered.connect(self.replace_text)
        self.replace_all_act.triggered.connect(self.replace_all)
        self.goto_act.triggered.connect(self.goto_line)
        self.search_web_act.triggered.connect(self._search_web_shortcut)
        self.collapse_blank_lines_act.triggered.connect(self.collapse_blank_lines)

        # Format
        self.wrap_act.toggled.connect(self._toggle_wrap)
        self.font_act.triggered.connect(self.change_font)

        # Auto-save
        self.autosave_disabled_act.triggered.connect(lambda: self._set_autosave_interval(0))
        self.autosave_2min_act.triggered.connect(lambda: self._set_autosave_interval(2))
        self.autosave_5min_act.triggered.connect(lambda: self._set_autosave_interval(5))
        self.autosave_15min_act.triggered.connect(lambda: self._set_autosave_interval(15))
        self.autosave_30min_act.triggered.connect(lambda: self._set_autosave_interval(30))

        # Time/Date
        self.time_date_act.triggered.connect(self.insert_time_date)

        # Insert - Headings
        self.insert_h1_act.triggered.connect(lambda: self._insert_heading(1))
        self.insert_h2_act.triggered.connect(lambda: self._insert_heading(2))
        self.insert_h3_act.triggered.connect(lambda: self._insert_heading(3))
        self.insert_h4_act.triggered.connect(lambda: self._insert_heading(4))
        self.insert_h5_act.triggered.connect(lambda: self._insert_heading(5))
        self.insert_h6_act.triggered.connect(lambda: self._insert_heading(6))
        
        # Insert - Lists
        self.insert_ul_act.triggered.connect(self._insert_unordered_list)
        self.insert_ol_act.triggered.connect(self._insert_ordered_list)
        self.insert_checkbox_act.triggered.connect(self._insert_checkbox)
        
        # Insert - Text formatting
        self.insert_emphasis_act.triggered.connect(self._insert_emphasis)
        self.insert_strong_act.triggered.connect(self._insert_strong)
        self.insert_strong_emphasis_act.triggered.connect(self._insert_strong_emphasis)
        self.insert_highlight_act.triggered.connect(self._insert_highlight)
        self.insert_strikethrough_act.triggered.connect(self._insert_strikethrough)
        self.insert_quote_act.triggered.connect(self._insert_quote)
        self.insert_code_block_act.triggered.connect(self._insert_code_block)
        
        # Insert - Special
        self.insert_image_act.triggered.connect(self._insert_image)
        self.insert_hyperlink_act.triggered.connect(self._insert_hyperlink)
        
        # Insert - Other
        self.insert_hr_act.triggered.connect(self._insert_horizontal_rule)
        self.insert_table_act.triggered.connect(self._insert_table)

        # Help
        self.about_act.triggered.connect(self.show_about)

        # Status updates
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.cursorPositionChanged.connect(self._update_status_bar)

        # Update window title on modification
        self.editor.modificationChanged.connect(self._update_title)

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_restore_maximized", False):
            self.setWindowState(self.windowState() | Qt.WindowMaximized)
            self._restore_maximized = False

    def keyReleaseEvent(self, event):
        """Detect double Ctrl press to toggle keyboard layout."""
        if sys.platform != "win32":
            super().keyReleaseEvent(event)
            return
        
        # Check if Ctrl key was released
        if event.key() in (Qt.Key_Control, Qt.Key_Meta):
            current_time = time.time()
            
            # If this is the second Ctrl press within 500ms, toggle layout
            if self._ctrl_press_time > 0 and (current_time - self._ctrl_press_time) < 0.5:
                # Toggle to the other layout
                new_layout = 1 - self._current_layout
                self._toggle_keyboard_layout(new_layout)
                self._ctrl_press_time = 0  # Reset
                self._ctrl_press_timer.stop()
            else:
                # First Ctrl press - start timer
                self._ctrl_press_time = current_time
                self._ctrl_press_timer.start(500)  # 500ms timeout
        
        super().keyReleaseEvent(event)

    def _install_shortcuts(self):
        sequences = (
            (QKeySequence.ZoomIn, 1),
            (QKeySequence(Qt.CTRL | Qt.Key_Plus), 1),
            (QKeySequence(Qt.CTRL | Qt.Key_Equal), 1),
            (QKeySequence("Ctrl++"), 1),
            (QKeySequence("Ctrl+="), 1),
            (QKeySequence.ZoomOut, -1),
            (QKeySequence(Qt.CTRL | Qt.Key_Minus), -1),
            (QKeySequence(Qt.CTRL | Qt.Key_Underscore), -1),
            (QKeySequence("Ctrl+-"), -1),
            (QKeySequence("Ctrl+_"), -1),
        )

        self._font_shortcuts = []
        for sequence, delta in sequences:
            shortcut = QShortcut(sequence, self.editor)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda d=delta: self._change_font_size(d))
            self._font_shortcuts.append(shortcut)

        plain_paste_sequences = (
            QKeySequence("Shift+Ctrl+V"),
            QKeySequence("Shift+Insert"),
        )
        self._plain_paste_shortcuts = []
        for sequence in plain_paste_sequences:
            shortcut = QShortcut(sequence, self.editor)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(self.editor.paste_plain_text)
            self._plain_paste_shortcuts.append(shortcut)

    def _install_layout_shortcuts(self):
        """Install Ctrl+, and Ctrl+. for keyboard layout switching."""
        if sys.platform != "win32":
            return
        
        # Ctrl+, (comma) -> switch to English India
        shortcut_comma = QShortcut(QKeySequence("Ctrl+,"), self)
        shortcut_comma.setContext(Qt.ApplicationShortcut)
        shortcut_comma.activated.connect(lambda: self._toggle_keyboard_layout(0))
        
        # Ctrl+. (period/fullstop) -> switch to Tamil Anjal
        shortcut_period = QShortcut(QKeySequence("Ctrl+."), self)
        shortcut_period.setContext(Qt.ApplicationShortcut)
        shortcut_period.activated.connect(lambda: self._toggle_keyboard_layout(1))

    def _toggle_keyboard_layout(self, target_layout):
        """Toggle keyboard layout: 0 = English India, 1 = Tamil Anjal."""
        if sys.platform != "win32":
            return
        
        self._current_layout = target_layout
        try:
            if target_layout == 0:
                switch_to_english_india()
                self.layout_label.setText("Keyboard: English India")
                print("DEBUG: Switched to English India")  # Debug output
            else:
                switch_to_tamil_anjal()
                self.layout_label.setText("Keyboard: Tamil Anjal")
                print("DEBUG: Switched to Tamil Anjal")  # Debug output
        except Exception as e:
            error_msg = f"Layout switch failed: {e}"
            self.layout_label.setText(f"Keyboard: Error")
            print(f"DEBUG: {error_msg}")  # Debug output
    
    def _reset_ctrl_press(self):
        """Reset the Ctrl press counter."""
        self._ctrl_press_time = 0

    def _update_export_menu_visibility(self):
        """Update export menu item visibility based on current file extension."""
        if self.current_path:
            ext = Path(self.current_path).suffix.lower()
            # Show "Export Text to PDF" only for .txt files
            self.export_text_pdf_act.setVisible(ext == '.txt' or ext == '')
            # Show "Export Markdown to PDF" only for .md files
            self.export_md_pdf_act.setVisible(ext in ['.md', '.markdown'])
        else:
            # No file saved yet - hide both export options
            self.export_text_pdf_act.setVisible(False)
            self.export_md_pdf_act.setVisible(False)

    # --- Core features ---
    def new_file(self):
        if not self._maybe_save_changes():
            return
        self.editor.clear()
        self.current_path = None
        self.editor.document().setModified(False)
        self._update_title()
        self._update_status_bar()
        self._update_export_menu_visibility()
        self.status.showMessage("New document", 2000)

    def _open_file_path(self, path: Path | str, *, notify_errors: bool = True, show_status: bool = True) -> bool:
        try:
            path_obj = Path(path).expanduser()
        except Exception:
            if notify_errors:
                QMessageBox.critical(self, "Error", f"Invalid file path:\n{path}")
            return False

        if not path_obj.exists() or not path_obj.is_file():
            if notify_errors:
                QMessageBox.warning(self, "File Not Found", f"File not found:\n{path_obj}")
            return False

        try:
            text = path_obj.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            if notify_errors:
                QMessageBox.critical(self, "Encoding Error", "File is not valid UTF-8.")
            return False
        except Exception as e:
            if notify_errors:
                QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")
            return False

        self.editor.setPlainText(text)
        self.current_path = str(path_obj)
        self.editor.document().setModified(False)
        self._update_default_directory(path_obj.parent)
        self._update_title()
        self._update_status_bar()
        self._update_export_menu_visibility()
        if show_status:
            self.status.showMessage(f"Opened: {path_obj}", 2000)
        if not self.autosave_enabled:
            self._start_autosave()
        return True

    def _load_initial_path(self, path: str) -> None:
        if not path:
            return
        success = self._open_file_path(path, notify_errors=True, show_status=True)
        if success:
            self._last_session_file = None
        else:
            self.status.showMessage(f"Could not open {path}", 3000)
            if self._last_session_file:
                fallback = self._last_session_file
                self._last_session_file = None
                if self._open_file_path(fallback, notify_errors=False, show_status=False):
                    self.status.showMessage(f"Opened last session file: {fallback}", 3000)

    def open_file(self):
        if not self._maybe_save_changes():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Text File",
            str(self.default_directory),
            "Text Files (*.txt);;Markdown Files (*.md);;All Files (*)",
        )
        if path:
            self._open_file_path(path)

    def save_file(self):
        if self.current_path is None:
            return self.save_file_as()
        return self._write_to_path(self.current_path)

    def save_file_as(self):
        initial_path = self.current_path or str(self.default_directory / "Untitled.txt")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            initial_path,
            "Text Files (*.txt);;Markdown Files (*.md);;All Files (*)",
        )
        if not path:
            return False
        self.current_path = path
        self._update_default_directory(Path(path).parent)
        self._update_export_menu_visibility()
        return self._write_to_path(path)

    def _write_to_path(self, path: str) -> bool:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.editor.document().setModified(False)
            self._update_default_directory(Path(path).parent)
            self._update_title()
            self.status.showMessage(f"Saved: {path}", 2000)
            
            if not self.autosave_enabled:
                self._start_autosave()
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")
            return False

    def _autosave(self):
        if self.current_path and self.editor.document().isModified():
            try:
                with open(self.current_path, "w", encoding="utf-8") as f:
                    f.write(self.editor.toPlainText())
                self.editor.document().setModified(False)
                self._update_title()
                self.status.showMessage("Auto-saved", 1500)
            except Exception:
                pass

    def _start_autosave(self):
        interval = self.settings.load().get("autosave_interval", 5)
        if interval > 0:
            self.autosave_timer.start(interval * 60 * 1000)
            self.autosave_enabled = True

    def _stop_autosave(self):
        self.autosave_timer.stop()
        self.autosave_enabled = False

    # --- Edit helpers ---
    def find_text(self):
        text, ok = QInputDialog.getText(self, "Find", "Find what:")
        if not ok or not text:
            return
        self._last_find = text
        self._find_forward(text)

    def find_next(self):
        text = getattr(self, "_last_find", "")
        if text:
            self._find_forward(text)
        else:
            self.find_text()

    def _find_forward(self, text: str):
        cs = self.editor.textCursor()
        doc = self.editor.document()
        m = doc.find(text, cs)
        if m.isNull():
            # Wrap search from top
            start = self.editor.textCursor()
            start.movePosition(QTextCursor.Start)
            m = doc.find(text, start)
        if not m.isNull():
            self.editor.setTextCursor(m)
            self.editor.centerCursor()
        else:
            self.status.showMessage("Text not found", 2000)

    def replace_text(self):
        find_text, ok1 = QInputDialog.getText(self, "Replace", "Find what:")
        if not ok1 or not find_text:
            return
        replace_with, ok2 = QInputDialog.getText(self, "Replace", "Replace with:")
        if not ok2:
            return
        
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            if selected == find_text:
                cursor.insertText(replace_with)
                self._find_forward(find_text)
                return
        
        self._find_forward(find_text)

    def replace_all(self):
        find_text, ok1 = QInputDialog.getText(self, "Replace All", "Find what:")
        if not ok1 or not find_text:
            return
        replace_with, ok2 = QInputDialog.getText(self, "Replace All", "Replace with:")
        if not ok2:
            return
        
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.Start)
        self.editor.setTextCursor(cursor)
        
        count = 0
        doc = self.editor.document()
        
        while True:
            found = doc.find(find_text, cursor)
            if found.isNull():
                break
            found.insertText(replace_with)
            cursor = found
            count += 1
            if count % 10 == 0:
                self.status.showMessage(f"Replaced {count} occurrences...", 500)
                QApplication.processEvents()
        
        cursor.endEditBlock()
        self.status.showMessage(f"Replaced {count} occurrence(s)", 3000)

    def collapse_blank_lines(self):
        text = self.editor.toPlainText()
        if not text:
            self.status.showMessage("Document is empty", 1500)
            return

        newline = "\r\n" if "\r\n" in text else "\n"
        pattern = re.compile(r'(?:\r\n|\r|\n){2,}')
        matches = list(pattern.finditer(text))
        if not matches:
            self.status.showMessage("No extra blank lines found", 2000)
            return

        collapsed = pattern.sub(newline, text)
        replacement_length = len(newline)
        adjustments = []
        for match in matches:
            start, end = match.span()
            diff = (end - start) - replacement_length
            if diff > 0:
                adjustments.append((start, end, diff))

        cursor = self.editor.textCursor()
        old_pos = cursor.position()
        old_anchor = cursor.anchor()

        def adjust_position(pos: int) -> int:
            for start, end, diff in adjustments:
                if pos > end:
                    pos -= diff
                elif start < pos <= end:
                    pos = start + replacement_length
                    break
            return pos

        new_pos = adjust_position(old_pos)
        new_anchor = adjust_position(old_anchor)

        doc_cursor = self.editor.textCursor()
        doc_cursor.beginEditBlock()
        doc_cursor.movePosition(QTextCursor.Start)
        doc_cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        doc_cursor.insertText(collapsed)
        doc_cursor.endEditBlock()

        restored_cursor = self.editor.textCursor()
        restored_cursor.setPosition(new_anchor)
        mode = QTextCursor.KeepAnchor if new_anchor != new_pos else QTextCursor.MoveAnchor
        restored_cursor.setPosition(new_pos, mode)
        self.editor.setTextCursor(restored_cursor)

        blocks_collapsed = len(matches)
        self.status.showMessage(f"Collapsed {blocks_collapsed} blank block(s)", 3000)

    def goto_line(self):
        line_str, ok = QInputDialog.getText(self, "Go To", "Line number:")
        if not ok or not line_str.strip().isdigit():
            return
        line = max(1, int(line_str.strip()))
        block = self.editor.document().findBlockByNumber(line - 1)
        if block.isValid():
            cursor = self.editor.textCursor()
            cursor.setPosition(block.position())
            self.editor.setTextCursor(cursor)
            self.editor.centerCursor()

    def insert_time_date(self):
        now = datetime.now().strftime("%H:%M %d-%m-%Y")  # similar to Notepad style
        self.editor.insertPlainText(now)

    # --- Markdown insertion methods ---
    def _remove_line_start_markdown(self, cursor):
        """Remove existing markdown tags at the start of the line."""
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        line_text = cursor.selectedText()
        
        # Patterns to remove: headings (#), lists (-, 1.), checkboxes (- [ ])
        import re
        # Remove heading markers (1-6 # symbols followed by space)
        cleaned = re.sub(r'^#{1,6}\s+', '', line_text)
        # Remove unordered list marker (- followed by space)
        cleaned = re.sub(r'^-\s+', '', cleaned)
        # Remove ordered list marker (number followed by . and space)
        cleaned = re.sub(r'^\d+\.\s+', '', cleaned)
        # Remove checkbox marker (- [ ] or - [x])
        cleaned = re.sub(r'^-\s+\[[xX\s]\]\s+', '', cleaned)
        
        return cleaned
    
    def _insert_heading(self, level: int):
        """Insert markdown heading at the start of current line, removing existing tags."""
        cursor = self.editor.textCursor()
        cleaned_text = self._remove_line_start_markdown(cursor)
        
        # Replace entire line with new heading
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        heading_prefix = "#" * level + " "
        cursor.insertText(heading_prefix + cleaned_text)
        self.editor.setTextCursor(cursor)

    def _insert_unordered_list(self):
        """Insert unordered list marker at the start of current line, removing existing tags."""
        cursor = self.editor.textCursor()
        cleaned_text = self._remove_line_start_markdown(cursor)
        
        # Replace entire line with unordered list
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        cursor.insertText("- " + cleaned_text)
        self.editor.setTextCursor(cursor)

    def _insert_ordered_list(self):
        """Insert ordered list marker at the start of current line, removing existing tags."""
        cursor = self.editor.textCursor()
        cleaned_text = self._remove_line_start_markdown(cursor)
        
        # Replace entire line with ordered list
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        cursor.insertText("1. " + cleaned_text)
        self.editor.setTextCursor(cursor)

    def _insert_checkbox(self):
        """Insert checkbox at the start of current line, removing existing tags."""
        cursor = self.editor.textCursor()
        cleaned_text = self._remove_line_start_markdown(cursor)
        
        # Replace entire line with checkbox
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        cursor.insertText("- [ ] " + cleaned_text)
        self.editor.setTextCursor(cursor)

    def _remove_text_formatting(self, text: str) -> str:
        """Remove existing markdown formatting from text."""
        import re
        # Remove in order from most specific to least specific
        # Remove triple asterisks (strong emphasis)
        cleaned = re.sub(r'\*\*\*(.*?)\*\*\*', r'\1', text)
        # Remove double asterisks (strong/bold)
        cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned)
        # Remove single asterisks (emphasis/italic)
        cleaned = re.sub(r'\*(.*?)\*', r'\1', cleaned)
        # Remove double equals (highlight)
        cleaned = re.sub(r'==(.*?)==', r'\1', cleaned)
        # Remove double tildes (strikethrough)
        cleaned = re.sub(r'~~(.*?)~~', r'\1', cleaned)
        # Remove triple backticks (code blocks)
        cleaned = re.sub(r'```(.*?)```', r'\1', cleaned, flags=re.DOTALL)
        # Remove single backticks (inline code)
        cleaned = re.sub(r'`(.*?)`', r'\1', cleaned)
        return cleaned
    
    def _wrap_selection(self, prefix: str, suffix: str = None):
        """Wrap selected text with markdown formatting, removing existing formatting."""
        if suffix is None:
            suffix = prefix
        
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            # Remove existing formatting before applying new one
            cleaned_text = self._remove_text_formatting(selected_text)
            wrapped_text = f"{prefix}{cleaned_text}{suffix}"
            cursor.insertText(wrapped_text)
        else:
            # No selection - insert markers and place cursor between them
            cursor.insertText(f"{prefix}{suffix}")
            # Move cursor back by suffix length
            for _ in range(len(suffix)):
                cursor.movePosition(QTextCursor.Left)
            self.editor.setTextCursor(cursor)

    def _insert_emphasis(self):
        """Insert emphasis (italic) markdown."""
        self._wrap_selection("*")

    def _insert_strong(self):
        """Insert strong (bold) markdown."""
        self._wrap_selection("**")

    def _insert_strong_emphasis(self):
        """Insert strong emphasis (bold italic) markdown."""
        self._wrap_selection("***")

    def _insert_highlight(self):
        """Insert highlight markdown."""
        self._wrap_selection("==")

    def _insert_strikethrough(self):
        """Insert strikethrough markdown."""
        self._wrap_selection("~~")

    def _insert_quote(self):
        """Insert quote markdown at the start of current line or selected lines."""
        cursor = self.editor.textCursor()
        
        if cursor.hasSelection():
            # Handle multiple lines
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.StartOfBlock)
            start_block = cursor.blockNumber()
            
            cursor.setPosition(end)
            end_block = cursor.blockNumber()
            
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.beginEditBlock()
            
            for _ in range(end_block - start_block + 1):
                cursor.insertText("> ")
                cursor.movePosition(QTextCursor.NextBlock)
            
            cursor.endEditBlock()
        else:
            # Single line
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.insertText("> ")
        
        self.editor.setTextCursor(cursor)

    def _insert_code_block(self):
        """Insert code block markdown."""
        cursor = self.editor.textCursor()
        
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            # Replace paragraph separator with newline
            selected_text = selected_text.replace("\u2029", "\n")
            code_block = f"```\n{selected_text}\n```"
            cursor.insertText(code_block)
        else:
            cursor.insertText("```\n\n```")
            # Move cursor to the middle line
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 4)
            self.editor.setTextCursor(cursor)

    def _validate_url(self, url: str) -> tuple[bool, str]:
        """Validate URL by attempting to connect to it.
        
        Returns:
            tuple: (is_valid, normalized_url or error_message)
        """
        # Normalize URL
        url = url.strip()
        if not url:
            return False, "URL cannot be empty"
        
        # Add https:// if no scheme specified
        if not url.startswith(("http://", "https://", "ftp://")):
            url = "https://" + url
        
        # Basic URL validation
        try:
            # Try to parse the URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if not parsed.netloc:
                return False, "Invalid URL format"
            
            # Try to connect
            req = urllib.request.Request(url, method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200 or response.status == 301 or response.status == 302:
                        return True, url
                    else:
                        return False, f"Server returned status code: {response.status}"
            except urllib.error.HTTPError as e:
                if e.code in (200, 301, 302, 403):  # 403 might still be a valid URL
                    return True, url
                return False, f"HTTP Error: {e.code} - {e.reason}"
            except urllib.error.URLError as e:
                return False, f"Connection failed: {e.reason}"
            except Exception as e:
                return False, f"Connection error: {str(e)}"
        except Exception as e:
            return False, f"Invalid URL: {str(e)}"

    def _insert_image(self):
        """Insert image with URL validation."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Insert Image")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # URL input
        url_label = QLabel("Image URL:", dialog)
        url_input = QLineEdit(dialog)
        url_input.setPlaceholderText("https://example.com/image.png")
        
        # Alt text input
        alt_label = QLabel("Image description (alt text):", dialog)
        alt_input = QLineEdit(dialog)
        alt_input.setPlaceholderText("Image description")
        
        # Status label
        status_label = QLabel("", dialog)
        status_label.setStyleSheet("color: red;")
        
        # Buttons
        button_layout = QHBoxLayout()
        insert_btn = QPushButton("Insert", dialog)
        cancel_btn = QPushButton("Cancel", dialog)
        validate_btn = QPushButton("Validate URL", dialog)
        
        button_layout.addWidget(validate_btn)
        button_layout.addStretch()
        button_layout.addWidget(insert_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(url_label)
        layout.addWidget(url_input)
        layout.addWidget(alt_label)
        layout.addWidget(alt_input)
        layout.addWidget(status_label)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        validated_url = [None]  # Use list to store in closure
        
        def validate():
            url = url_input.text().strip()
            if not url:
                status_label.setText("Please enter a URL")
                status_label.setStyleSheet("color: red;")
                return
            
            status_label.setText("Validating...")
            status_label.setStyleSheet("color: blue;")
            QApplication.processEvents()
            
            is_valid, result = self._validate_url(url)
            if is_valid:
                validated_url[0] = result
                status_label.setText("✓ URL is valid")
                status_label.setStyleSheet("color: green;")
                insert_btn.setEnabled(True)
            else:
                validated_url[0] = None
                status_label.setText(f"✗ {result}")
                status_label.setStyleSheet("color: red;")
        
        def insert():
            url = url_input.text().strip()
            alt = alt_input.text().strip()
            
            if not url:
                status_label.setText("Please enter a URL")
                status_label.setStyleSheet("color: red;")
                return
            
            # If not validated yet, validate now
            if validated_url[0] is None:
                is_valid, result = self._validate_url(url)
                if is_valid:
                    validated_url[0] = result
                else:
                    reply = QMessageBox.question(
                        dialog,
                        "URL Validation Failed",
                        f"{result}\n\nDo you want to insert anyway?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
                    validated_url[0] = url if not url.startswith(("http://", "https://")) else url
                    if not validated_url[0].startswith(("http://", "https://")):
                        validated_url[0] = "https://" + validated_url[0]
            
            # Insert markdown
            markdown = f"![{alt}]({validated_url[0]})"
            self.editor.insertPlainText(markdown)
            dialog.accept()
        
        validate_btn.clicked.connect(validate)
        insert_btn.clicked.connect(insert)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec()

    def _insert_hyperlink(self):
        """Insert hyperlink with URL validation."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Insert Hyperlink")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Text input
        text_label = QLabel("Link text:", dialog)
        text_input = QLineEdit(dialog)
        text_input.setPlaceholderText("Click here")
        
        # URL input
        url_label = QLabel("URL:", dialog)
        url_input = QLineEdit(dialog)
        url_input.setPlaceholderText("https://example.com")
        
        # Pre-fill with selection if any
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            text_input.setText(cursor.selectedText())
        
        # Status label
        status_label = QLabel("", dialog)
        status_label.setStyleSheet("color: red;")
        
        # Buttons
        button_layout = QHBoxLayout()
        insert_btn = QPushButton("Insert", dialog)
        cancel_btn = QPushButton("Cancel", dialog)
        validate_btn = QPushButton("Validate URL", dialog)
        
        button_layout.addWidget(validate_btn)
        button_layout.addStretch()
        button_layout.addWidget(insert_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(text_label)
        layout.addWidget(text_input)
        layout.addWidget(url_label)
        layout.addWidget(url_input)
        layout.addWidget(status_label)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        validated_url = [None]  # Use list to store in closure
        
        def validate():
            url = url_input.text().strip()
            if not url:
                status_label.setText("Please enter a URL")
                status_label.setStyleSheet("color: red;")
                return
            
            status_label.setText("Validating...")
            status_label.setStyleSheet("color: blue;")
            QApplication.processEvents()
            
            is_valid, result = self._validate_url(url)
            if is_valid:
                validated_url[0] = result
                status_label.setText("✓ URL is valid")
                status_label.setStyleSheet("color: green;")
                insert_btn.setEnabled(True)
            else:
                validated_url[0] = None
                status_label.setText(f"✗ {result}")
                status_label.setStyleSheet("color: red;")
        
        def insert():
            text = text_input.text().strip()
            url = url_input.text().strip()
            
            if not url:
                status_label.setText("Please enter a URL")
                status_label.setStyleSheet("color: red;")
                return
            
            if not text:
                text = url
            
            # If not validated yet, validate now
            if validated_url[0] is None:
                is_valid, result = self._validate_url(url)
                if is_valid:
                    validated_url[0] = result
                else:
                    reply = QMessageBox.question(
                        dialog,
                        "URL Validation Failed",
                        f"{result}\n\nDo you want to insert anyway?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
                    validated_url[0] = url if url.startswith(("http://", "https://")) else ("https://" + url)
            
            # Insert markdown - replace selection or insert at cursor
            markdown = f"[{text}]({validated_url[0]})"
            cursor = self.editor.textCursor()
            cursor.insertText(markdown)
            dialog.accept()
        
        validate_btn.clicked.connect(validate)
        insert_btn.clicked.connect(insert)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec()

    def _insert_horizontal_rule(self):
        """Insert horizontal rule markdown."""
        cursor = self.editor.textCursor()
        cursor.insertText("\n---\n")

    def _insert_table(self):
        """Insert a basic markdown table template."""
        table = """| Header 1 | Header 2 | Header 3 |
| -------- | -------- | -------- |
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
"""
        cursor = self.editor.textCursor()
        cursor.insertText(table)

    # --- PDF Export methods ---
    def _export_text_to_pdf(self):
        """Export plain text file to PDF with filename header and page numbers."""
        # Check if current file is .txt
        if self.current_path:
            ext = Path(self.current_path).suffix.lower()
            if ext not in ['.txt', '']:
                QMessageBox.information(
                    self,
                    "Export Text to PDF",
                    "This feature is for plain text files (.txt).\nFor Markdown files (.md), use 'Export Markdown to PDF'."
                )
                return
        
        # Get save location
        default_name = "Untitled.pdf"
        if self.current_path:
            default_name = Path(self.current_path).stem + ".pdf"
        
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Text to PDF",
            str(self.default_directory / default_name),
            "PDF Files (*.pdf)"
        )
        
        if not save_path:
            return
        
        try:
            from PySide6.QtPrintSupport import QPrinter
            from PySide6.QtGui import QPageSize, QPageLayout, QTextDocument, QTextCursor as QTC
            from PySide6.QtCore import QSizeF, QMarginsF
            
            # Create printer
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(save_path)
            printer.setPageSize(QPageSize(QPageSize.A4))
            # Set margins: left, top, right, bottom in millimeters
            margins = QMarginsF(15, 20, 15, 20)
            printer.setPageMargins(margins, QPageLayout.Unit.Millimeter)
            
            # Create document
            doc = QTextDocument()
            doc.setDefaultFont(self.editor.font())
            
            # Build content with header
            content = ""
            if self.current_path:
                filename = Path(self.current_path).name
                content = f"{filename}\n{'─' * 80}\n\n"
            
            content += self.editor.toPlainText()
            doc.setPlainText(content)
            
            # Print to PDF
            doc.print_(printer)
            
            self.status.showMessage(f"Exported to: {save_path}", 3000)
            QMessageBox.information(
                self,
                "Export Successful",
                f"Text file exported to:\n{save_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Could not export to PDF:\n{str(e)}"
            )

    def _export_markdown_to_pdf(self):
        """Export markdown file to PDF with proper rendering."""
        # Check if current file is .md
        if self.current_path:
            ext = Path(self.current_path).suffix.lower()
            if ext not in ['.md', '.markdown']:
                QMessageBox.information(
                    self,
                    "Export Markdown to PDF",
                    "This feature is for Markdown files (.md).\nFor plain text files (.txt), use 'Export Text to PDF'."
                )
                return
        
        # Get save location
        default_name = "Untitled.pdf"
        if self.current_path:
            default_name = Path(self.current_path).stem + ".pdf"
        
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Markdown to PDF",
            str(self.default_directory / default_name),
            "PDF Files (*.pdf)"
        )
        
        if not save_path:
            return
        
        try:
            # Try to import markdown library
            try:
                import markdown
                has_markdown = True
            except ImportError:
                has_markdown = False
            
            from PySide6.QtPrintSupport import QPrinter
            from PySide6.QtGui import QPageSize, QPageLayout, QTextDocument
            from PySide6.QtCore import QMarginsF
            
            # Create printer
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(save_path)
            printer.setPageSize(QPageSize(QPageSize.A4))
            # Set margins: left, top, right, bottom in millimeters
            margins = QMarginsF(15, 20, 15, 20)
            printer.setPageMargins(margins, QPageLayout.Unit.Millimeter)
            
            # Create document
            doc = QTextDocument()
            doc.setDefaultFont(self.editor.font())
            
            markdown_text = self.editor.toPlainText()
            
            if has_markdown:
                # Convert markdown to HTML
                html = markdown.markdown(
                    markdown_text,
                    extensions=['extra', 'codehilite', 'tables', 'toc']
                )
                
                # Add basic CSS styling
                styled_html = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: {self.editor.font().family()}; font-size: {self.editor.font().pointSize()}pt; }}
                        h1 {{ font-size: 2em; margin-top: 0.67em; margin-bottom: 0.67em; }}
                        h2 {{ font-size: 1.5em; margin-top: 0.83em; margin-bottom: 0.83em; }}
                        h3 {{ font-size: 1.17em; margin-top: 1em; margin-bottom: 1em; }}
                        code {{ background-color: #f4f4f4; padding: 2px 4px; font-family: monospace; }}
                        pre {{ background-color: #f4f4f4; padding: 10px; overflow-x: auto; }}
                        blockquote {{ border-left: 3px solid #ccc; margin-left: 0; padding-left: 10px; color: #666; }}
                        table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                    </style>
                </head>
                <body>
                    {html}
                </body>
                </html>
                """
                doc.setHtml(styled_html)
            else:
                # Fallback: simple text with basic markdown rendering
                # This is a simplified version if markdown library is not available
                lines = markdown_text.split('\n')
                html_lines = []
                
                for line in lines:
                    # Headers
                    if line.startswith('######'):
                        html_lines.append(f'<h6>{line[6:].strip()}</h6>')
                    elif line.startswith('#####'):
                        html_lines.append(f'<h5>{line[5:].strip()}</h5>')
                    elif line.startswith('####'):
                        html_lines.append(f'<h4>{line[4:].strip()}</h4>')
                    elif line.startswith('###'):
                        html_lines.append(f'<h3>{line[3:].strip()}</h3>')
                    elif line.startswith('##'):
                        html_lines.append(f'<h2>{line[2:].strip()}</h2>')
                    elif line.startswith('#'):
                        html_lines.append(f'<h1>{line[1:].strip()}</h1>')
                    # Horizontal rule
                    elif line.strip() in ['---', '***', '___']:
                        html_lines.append('<hr>')
                    # Lists
                    elif line.strip().startswith('- '):
                        html_lines.append(f'<li>{line.strip()[2:]}</li>')
                    # Bold italic
                    elif '***' in line:
                        line = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', line)
                        html_lines.append(f'<p>{line}</p>')
                    # Bold
                    elif '**' in line:
                        line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
                        html_lines.append(f'<p>{line}</p>')
                    # Italic
                    elif '*' in line:
                        line = re.sub(r'\*(.*?)\*', r'<em>\1</em>', line)
                        html_lines.append(f'<p>{line}</p>')
                    else:
                        if line.strip():
                            html_lines.append(f'<p>{line}</p>')
                        else:
                            html_lines.append('<br>')
                
                basic_html = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: {self.editor.font().family()}; font-size: {self.editor.font().pointSize()}pt; }}
                        h1 {{ font-size: 2em; }}
                        h2 {{ font-size: 1.5em; }}
                        h3 {{ font-size: 1.17em; }}
                    </style>
                </head>
                <body>
                    {''.join(html_lines)}
                </body>
                </html>
                """
                doc.setHtml(basic_html)
            
            # Print to PDF
            doc.print_(printer)
            
            self.status.showMessage(f"Exported to: {save_path}", 3000)
            
            msg = f"Markdown file exported to:\n{save_path}"
            if not has_markdown:
                msg += "\n\nNote: For better markdown rendering, install the 'markdown' package:\npip install markdown"
            
            QMessageBox.information(
                self,
                "Export Successful",
                msg
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Could not export to PDF:\n{str(e)}"
            )

    def show_about(self):
        QMessageBox.information(
            self,
            "About",
            f"Neight v{VERSION} (Using {QT_LIB})\nA lightweight UTF-8 text editor with advanced features, word count, line numbers and more.\nGenerated by Github Copilot for venkatarangan.com."
        )

    # --- Preferences ---
    def _load_preferences(self):
        data = self.settings.load()
        default_dir = data.get("default_directory")
        if isinstance(default_dir, str) and default_dir:
            try:
                self.default_directory = Path(default_dir).expanduser()
            except Exception:
                try:
                    self.default_directory = Path(default_dir)
                except Exception:
                    self.default_directory = Path.home()
        else:
            self.default_directory = Path.home()

        size_info = data.get("window_size") if isinstance(data, dict) else None
        if isinstance(size_info, dict):
            width = size_info.get("width")
            height = size_info.get("height")
            try:
                width = int(width)
                height = int(height)
            except (TypeError, ValueError):
                width = height = None
            if width and height and width >= 300 and height >= 200:
                self.resize(width, height)

        self._restore_maximized = bool(data.get("window_maximized", False))
        
        # Auto-save interval
        autosave_interval = data.get("autosave_interval", 5)
        self._update_autosave_menu(autosave_interval)
        
        # Word wrap
        wrap = data.get("word_wrap", True)
        self.wrap_act.setChecked(bool(wrap))
        self.editor.setWordWrap(bool(wrap))

        # Font
        family = data.get("font_family")
        size = data.get("font_size")
        if family and isinstance(size, int) and size > 0:
            try:
                font = QFont(family, size)
                self.editor.setFont(font)
            except Exception:
                pass
        
        # Last opened file
        last_file = data.get("last_opened_file")
        if isinstance(last_file, str) and last_file:
            if getattr(self, "_initial_file", None):
                self._last_session_file = last_file
            else:
                self._open_file_path(last_file, notify_errors=False, show_status=False)

    def _save_preferences(self):
        try:
            font = self.editor.font()
            data = self.settings.load()
            if self.isMinimized():
                normal_geom = self.normalGeometry()
                size_obj = normal_geom.size() if normal_geom.isValid() else self.size()
            else:
                size_obj = self.size()
            width = int(size_obj.width()) if size_obj.width() > 0 else 1000
            height = int(size_obj.height()) if size_obj.height() > 0 else 650
            width = max(width, 300)
            height = max(height, 200)
            autosave_interval = data.get("autosave_interval", 5)
            data.update({
                "word_wrap": self.editor.isWordWrap(),
                "font_family": font.family(),
                "font_size": int(font.pointSize()) if font.pointSize() > 0 else 12,
                "default_directory": str(self.default_directory),
                "window_size": {"width": width, "height": height},
                "window_maximized": bool(self.isMaximized()),
                "autosave_interval": autosave_interval,
                "last_opened_file": self.current_path if self.current_path else "",
            })
            self.settings.save(data)
        except Exception:
            pass

    def change_font(self):
        current_font = self.editor.font()
        ok, font = QFontDialog.getFont(current_font, self, "Choose Font")
        if ok:
            self.editor.setFont(font)
            self._save_preferences()

 

    def _toggle_wrap(self, enabled: bool):
        self.editor.setWordWrap(bool(enabled))
        self._save_preferences()

    def _update_default_directory(self, directory: Path | str):
        if directory is None:
            return
        try:
            candidate = Path(directory)
        except Exception:
            return
        if candidate.is_file():
            candidate = candidate.parent
        try:
            candidate = candidate.expanduser()
        except Exception:
            pass
        if getattr(self, "default_directory", None) is not None:
            if str(candidate) == str(self.default_directory):
                self.default_directory = candidate
                return
        self.default_directory = candidate
        self._save_preferences()

    def _set_autosave_interval(self, minutes: int):
        data = self.settings.load()
        data["autosave_interval"] = minutes
        self.settings.save(data)
        self._update_autosave_menu(minutes)
        
        if minutes > 0 and self.current_path:
            self.autosave_timer.start(minutes * 60 * 1000)
            self.autosave_enabled = True
            self.status.showMessage(f"Auto-save enabled ({minutes} min)", 2000)
        else:
            self._stop_autosave()
            self.status.showMessage("Auto-save disabled", 2000)

    def _update_autosave_menu(self, minutes: int):
        self.autosave_disabled_act.setChecked(minutes == 0)
        self.autosave_2min_act.setChecked(minutes == 2)
        self.autosave_5min_act.setChecked(minutes == 5)
        self.autosave_15min_act.setChecked(minutes == 15)
        self.autosave_30min_act.setChecked(minutes == 30)

    def _search_web_shortcut(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
        else:
            cursor.select(QTextCursor.WordUnderCursor)
            text = cursor.selectedText()
        
        cleaned = CodeEditor._normalize_search_text(text)
        if cleaned:
            self.launch_web_search(cleaned)
        else:
            self.status.showMessage("No text selected for search", 1500)

    def launch_web_search(self, query: str):
        cleaned = CodeEditor._normalize_search_text(query)
        if not cleaned:
            self.status.showMessage("No text selected for search", 1500)
            return

        url = f"https://www.google.com/search?q={quote_plus(cleaned)}"
        try:
            webbrowser.open(url)
            self.status.showMessage(f'Google search: "{cleaned}"', 2000)
        except Exception as exc:
            QMessageBox.warning(self, "Search Failed", f"Could not launch browser:\n{exc}")

    def _change_font_size(self, step: int):
        font = self.editor.font()
        current_size = font.pointSize()
        if current_size <= 0:
            current_size = 12

        new_size = max(6, min(100, current_size + step))
        if new_size == current_size:
            self.status.showMessage("Font size limit reached", 1500)
            return

        font.setPointSize(new_size)
        self.editor.setFont(font)
        self._save_preferences()
        self.status.showMessage(f"Font size: {new_size}pt", 1500)

    # --- Helpers ---
    def _maybe_save_changes(self) -> bool:
        if not self.editor.document().isModified():
            return True
        ret = QMessageBox.question(
            self,
            "Unsaved Changes",
            "The document has unsaved changes. Do you want to save them?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if ret == QMessageBox.Cancel:
            return False
        if ret == QMessageBox.Yes:
            return self.save_file()
        return True

    def _update_title(self, *_):
        name = "Untitled" if self.current_path is None else QFileInfo(self.current_path).fileName()
        modified = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"{name}{modified} - Neight")

    def _on_text_changed(self):
        self._update_status_bar()

    def _update_status_bar(self):
        text = self.editor.toPlainText()
        words = len(re.findall(r"\S+", text))
        chars = len(text)
        self.count_label.setText(f"Words: {words} | Chars: {chars}")

        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        self.pos_label.setText(f"Ln {line}, Col {col}")

    # Confirm close with save prompt and persist settings
    def closeEvent(self, event):
        if self._maybe_save_changes():
            self._save_preferences()
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    initial_file = next((arg for arg in sys.argv[1:] if not arg.startswith("-")), None)
    window = Notepad(initial_file=initial_file)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
