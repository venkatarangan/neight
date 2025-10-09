# python -m pip install --upgrade pip
# python -m pip install PySide6
# python -m pip install pyinstaller

import sys
import json
import re
import time
import webbrowser
import ctypes
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus


try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QPlainTextEdit, QFileDialog, QMessageBox,
        QStatusBar, QWidget, QLabel, QFontDialog, QInputDialog
    )
    # In Qt6 / PySide6 QAction and QShortcut live in QtGui (not QtWidgets)
    from PySide6.QtGui import QKeySequence, QPainter, QFont, QTextCursor, QAction, QShortcut
    from PySide6.QtCore import Qt, QRect, QFileInfo, QTimer
    QT_LIB = "PySide6"
except Exception:  # Fallback to PyQt5 if PySide6 is unavailable
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QPlainTextEdit, QFileDialog, QMessageBox,
        QAction, QStatusBar, QWidget, QLabel, QFontDialog, QInputDialog, QShortcut
    )
    from PyQt5.QtGui import QKeySequence, QPainter, QFont, QTextCursor
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
        try:
            if getattr(sys, "frozen", False):  # PyInstaller executable
                base_dir = Path(sys.executable).resolve().parent
            else:
                base_dir = Path(__file__).resolve().parent
        except Exception:
            base_dir = Path.cwd()
        self.path = base_dir / filename
        self.legacy_paths = tuple((base_dir / legacy) for legacy in legacy_files)

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
        data = self._load_file(self.path)
        if data is not None:
            return data

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

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self.palette().mid().color())
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


# ---------------------
# Main window
# ---------------------
class Notepad(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Untitled - Neight")
        self.resize(1000, 650)

        self.settings = SettingsManager()
        self.default_directory = Path.home()
        self._restore_maximized = False

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
        file_menu.addAction(self.exit_act)

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

    # --- Core features ---
    def new_file(self):
        if not self._maybe_save_changes():
            return
        self.editor.clear()
        self.current_path = None
        self.editor.document().setModified(False)
        self._update_title()
        self._update_status_bar()
        self.status.showMessage("New document", 2000)

    def open_file(self):
        if not self._maybe_save_changes():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Text File",
            str(self.default_directory),
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                self.editor.setPlainText(text)
                self.current_path = path
                self.editor.document().setModified(False)
                self._update_default_directory(Path(path).parent)
                self._update_title()
                self._update_status_bar()
                self.status.showMessage(f"Opened: {path}", 2000)
            except UnicodeDecodeError:
                QMessageBox.critical(self, "Encoding Error", "File is not valid UTF-8.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")

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
            "Text Files (*.txt);;All Files (*)",
        )
        if not path:
            return False
        self.current_path = path
        self._update_default_directory(Path(path).parent)
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
            start.movePosition(start.Start)
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
        cursor.movePosition(cursor.Start)
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

    def show_about(self):
        QMessageBox.information(
            self,
            "About",
            f"Neight (Using {QT_LIB})\nA lightweight UTF-8 text editor with advanced features, word count, line numbers and more.\nGenerated by Github Copilot for venkatarangan.com."
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
            last_path = Path(last_file)
            if last_path.exists() and last_path.is_file():
                try:
                    with open(last_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    self.editor.setPlainText(text)
                    self.current_path = str(last_path)
                    self.editor.document().setModified(False)
                    self._update_title()
                    if not self.autosave_enabled:
                        self._start_autosave()
                except Exception:
                    pass

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
        font, ok = QFontDialog.getFont(self.editor.font(), self, "Choose Font")
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
    window = Notepad()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
