# python -m pip install --upgrade pip
# python -m pip install PySide6
# python -m pip install pyinstaller
# ./venv/bin/activate    

import sys
import os
import subprocess
import json
import re
import math
import time
import webbrowser
import unicodedata
import ctypes
import urllib.request
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

# Version information
VERSION = "2026.023"

DEFAULT_GOOGLE_SEARCH_URL_PREFIX = "https://www.google.com/search?q="
DEFAULT_SORKUVAI_SEARCH_URL_PREFIX = "https://sorkuvai.tn.gov.in/?q="


from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QFileDialog, QMessageBox,
    QStatusBar, QWidget, QLabel, QFontDialog, QInputDialog, QDialog,
    QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
    QProgressBar, QDialogButtonBox, QButtonGroup, QRadioButton, QTextEdit, QComboBox,
    QMenu, QCheckBox, QStyle, QSpinBox, QColorDialog, QPlainTextDocumentLayout, QToolTip
)
# In Qt6/PySide6, QAction and QShortcut live in QtGui (moved from QtWidgets in Qt5)
from PySide6.QtGui import QKeySequence, QPainter, QFont, QTextCursor, QTextBlockFormat, QAction, QShortcut, QColor, QGuiApplication, QTextDocument, QDesktopServices, QIcon
from PySide6.QtCore import Qt, QRect, QFileInfo, QTimer, Signal, QUrl, QRectF, QPoint
QT_LIB = "PySide6"

# PDF print-support imports (optional — export features require QtPrintSupport)
try:
    from PySide6.QtPrintSupport import QPrinter
    from PySide6.QtGui import QPageSize, QPageLayout
    from PySide6.QtCore import QMarginsF
    HAS_PRINT_SUPPORT = True
except ImportError:
    HAS_PRINT_SUPPORT = False

# Qt6/PySide6 uses scoped enum QPageLayout.Unit.Millimeter
if HAS_PRINT_SUPPORT:
    _MARGIN_UNIT_MM = QPageLayout.Unit.Millimeter

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

    def switch_to_tamil_anjal():
        """Switch to the detected Tamil keyboard layout."""
        if TAMIL_CHOICE:
            hkl = load_hkl(TAMIL_CHOICE)
            activate_hkl(hkl)

    def switch_to_english_india():
        """Switch to the detected English keyboard layout."""
        if ENGLISH_CHOICE:
            hkl = load_hkl(ENGLISH_CHOICE)
            activate_hkl(hkl)

    def get_current_layout() -> int:
        """Return 1 if the active keyboard layout matches the detected Tamil choice, else 0.
        Does NOT switch anything — read-only."""
        if not TAMIL_CHOICE:
            return 0
        buf = ctypes.create_unicode_buffer(9)  # KL_NAMELENGTH = 9
        if user32.GetKeyboardLayoutNameW(buf):
            return 1 if buf.value.upper().zfill(8) == TAMIL_CHOICE else 0
        return 0

    def get_current_layout_label() -> str:
        """Return a display string for the currently active keyboard layout."""
        buf = ctypes.create_unicode_buffer(9)  # KL_NAMELENGTH = 9
        if user32.GetKeyboardLayoutNameW(buf):
            klid = buf.value.upper().zfill(8)
            if TAMIL_CHOICE and klid == TAMIL_CHOICE:
                return f"Keyboard: {TAMIL_CHOICE_NAME}"
            if ENGLISH_CHOICE and klid == ENGLISH_CHOICE:
                return f"Keyboard: {ENGLISH_CHOICE_NAME}"
        return "Keyboard: System Default"

    def get_installed_ime_list() -> list:
        """Return list of (klid, name) for all keyboard layouts installed for the current user.
        Reads from the registry without activating or changing any layout."""
        import winreg
        results = []
        try:
            # Resolve substitutes: some preload entries point to a substitute KLID (e.g. IMEs)
            substitutes: dict[str, str] = {}
            try:
                sub_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Keyboard Layout\Substitutes")
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(sub_key, i)
                        substitutes[name.upper().zfill(8)] = value.upper().zfill(8)
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(sub_key)
            except Exception:
                pass

            # Enumerate preloaded layouts for the current user
            preload_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Keyboard Layout\Preload")
            i = 0
            while True:
                try:
                    _, klid_raw, _ = winreg.EnumValue(preload_key, i)
                    klid = klid_raw.upper().zfill(8)
                    actual_klid = substitutes.get(klid, klid)
                    # Look up display name in HKLM
                    try:
                        layout_key = winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE,
                            rf"SYSTEM\CurrentControlSet\Control\Keyboard Layouts\{actual_klid}"
                        )
                        layout_name, _ = winreg.QueryValueEx(layout_key, "Layout Text")
                        winreg.CloseKey(layout_key)
                    except Exception:
                        layout_name = "Unknown"
                    results.append((actual_klid, layout_name))
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(preload_key)
        except Exception:
            pass
        return results

elif sys.platform == "darwin":
    # ------------------------------------
    # Keyboard layout switching (macOS)
    # Uses Text Input Services (TIS) via Carbon framework through ctypes.
    # No extra packages required.
    # ------------------------------------

    _kCFStringEncodingUTF8 = 0x08000100
    _macos_cf = None
    _macos_carbon = None

    def _macos_libs():
        """Lazily load and cache CoreFoundation and Carbon frameworks."""
        global _macos_cf, _macos_carbon
        if _macos_cf is not None:
            return _macos_cf, _macos_carbon
        try:
            import ctypes.util
            _cf_path = ctypes.util.find_library('CoreFoundation')
            _carbon_path = ctypes.util.find_library('Carbon')
        except Exception:
            _cf_path = None
            _carbon_path = None
        cf = ctypes.CDLL(
            _cf_path or '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'
        )
        carbon = ctypes.CDLL(
            _carbon_path or '/System/Library/Frameworks/Carbon.framework/Carbon'
        )
        cf.CFArrayGetCount.restype = ctypes.c_long
        cf.CFArrayGetCount.argtypes = [ctypes.c_void_p]
        cf.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
        cf.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
        cf.CFStringGetCString.restype = ctypes.c_bool
        cf.CFStringGetCString.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32
        ]
        cf.CFRelease.restype = None
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        carbon.TISCreateInputSourceList.restype = ctypes.c_void_p
        carbon.TISCreateInputSourceList.argtypes = [ctypes.c_void_p, ctypes.c_bool]
        carbon.TISSelectInputSource.restype = ctypes.c_int32
        carbon.TISSelectInputSource.argtypes = [ctypes.c_void_p]
        carbon.TISGetInputSourceProperty.restype = ctypes.c_void_p
        carbon.TISGetInputSourceProperty.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        carbon.TISCopyCurrentKeyboardInputSource.restype = ctypes.c_void_p
        carbon.TISCopyCurrentKeyboardInputSource.argtypes = []
        _macos_cf = cf
        _macos_carbon = carbon
        return cf, carbon

    def _macos_cfstr_to_str(cf, cfstr) -> str:
        """Convert a CFStringRef (integer/pointer) to a Python str."""
        if not cfstr:
            return ""
        buf = ctypes.create_string_buffer(512)
        if cf.CFStringGetCString(cfstr, buf, 512, _kCFStringEncodingUTF8):
            return buf.value.decode('utf-8', errors='replace')
        return ""

    def _macos_get_source_prop(cf, carbon, source, prop_name: str) -> str:
        """Read a TIS input source string property by its exported symbol name."""
        try:
            key = ctypes.c_void_p.in_dll(carbon, prop_name).value
            if not key:
                return ""
            val = carbon.TISGetInputSourceProperty(source, key)
            return _macos_cfstr_to_str(cf, val)
        except Exception:
            return ""

    def _macos_select_source(source_id: str) -> bool:
        """Find and activate a macOS input source by its bundle ID."""
        try:
            cf, carbon = _macos_libs()
            sources = carbon.TISCreateInputSourceList(None, True)
            if not sources:
                return False
            count = cf.CFArrayGetCount(sources)
            ok = False
            for i in range(count):
                src = cf.CFArrayGetValueAtIndex(sources, i)
                if not src:
                    continue
                sid = _macos_get_source_prop(cf, carbon, src, 'kTISPropertyInputSourceID')
                if sid == source_id:
                    carbon.TISSelectInputSource(src)
                    ok = True
                    break
            cf.CFRelease(sources)
            return ok
        except Exception:
            return False

    def _macos_current_source_id() -> str:
        """Return the bundle ID of the currently active macOS input source."""
        try:
            cf, carbon = _macos_libs()
            src = carbon.TISCopyCurrentKeyboardInputSource()
            if not src:
                return ""
            sid = _macos_get_source_prop(cf, carbon, src, 'kTISPropertyInputSourceID')
            cf.CFRelease(src)
            return sid
        except Exception:
            return ""

    def switch_to_tamil_anjal():
        """Switch to the detected Tamil input source."""
        if TAMIL_CHOICE:
            _macos_select_source(TAMIL_CHOICE)

    def switch_to_english_india():
        """Switch to the detected English input source."""
        if ENGLISH_CHOICE:
            _macos_select_source(ENGLISH_CHOICE)

    def get_current_layout() -> int:
        sid = _macos_current_source_id()
        return 1 if (TAMIL_CHOICE and sid == TAMIL_CHOICE) else 0

    def get_current_layout_label() -> str:
        sid = _macos_current_source_id()
        if TAMIL_CHOICE and sid == TAMIL_CHOICE:
            return f"Keyboard: {TAMIL_CHOICE_NAME}"
        if ENGLISH_CHOICE and sid == ENGLISH_CHOICE:
            return f"Keyboard: {ENGLISH_CHOICE_NAME}"
        return "Keyboard: System Default"

    def get_installed_ime_list() -> list:
        """Return list of (source_id, name) for all enabled macOS input sources."""
        try:
            cf, carbon = _macos_libs()
            # includeAllInstalled=False → only user-enabled (menu-visible) sources
            sources = carbon.TISCreateInputSourceList(None, False)
            if not sources:
                return []
            count = cf.CFArrayGetCount(sources)
            results = []
            for i in range(count):
                src = cf.CFArrayGetValueAtIndex(sources, i)
                if not src:
                    continue
                sid = _macos_get_source_prop(cf, carbon, src, 'kTISPropertyInputSourceID')
                name = _macos_get_source_prop(
                    cf, carbon, src, 'kTISPropertyLocalizedName'
                )
                if sid:
                    results.append((sid, name or sid))
            cf.CFRelease(sources)
            return results
        except Exception:
            return []

else:
    def switch_to_tamil_anjal():
        pass

    def switch_to_english_india():
        pass

    def get_current_layout() -> int:
        return 0

    def get_current_layout_label() -> str:
        return "Keyboard: System Default"

    def get_installed_ime_list() -> list:
        return []


# ------------------------------------
# Cross-platform keyboard helpers
# ------------------------------------

# Auto-detected keyboard choices — populated at startup by _init_keyboard_choices().
# Platform-native identifiers: KLID string on Windows, bundle-ID string on macOS.
TAMIL_CHOICE: Optional[str] = None
ENGLISH_CHOICE: Optional[str] = None
TAMIL_CHOICE_NAME: str = "Tamil"
ENGLISH_CHOICE_NAME: str = "English"


def _is_tamil_ime(klid: str) -> bool:
    """Return True if the given platform-native keyboard ID belongs to a Tamil layout."""
    if sys.platform == "darwin":
        return "tamil" in klid.lower()
    if sys.platform == "win32":
        try:
            # KLID format: 8 hex digits; last 4 are the LANGID.
            # Primary language bits (low 10 bits of LANGID): 0x049 = Tamil.
            return (int(klid[-4:], 16) & 0x3FF) == 0x049
        except Exception:
            return False
    return False


def _is_english_ime(klid: str) -> bool:
    """Return True if the given platform-native keyboard ID belongs to an English layout."""
    if sys.platform == "darwin":
        # Any non-Tamil layout is considered English-family for our purposes.
        return not _is_tamil_ime(klid)
    if sys.platform == "win32":
        try:
            # Primary language bits: 0x009 = English.
            return (int(klid[-4:], 16) & 0x3FF) == 0x009
        except Exception:
            return False
    return False


def _init_keyboard_choices(installed_imes: Optional[list] = None) -> None:
    """Scan installed IMEs and set TAMIL_CHOICE / ENGLISH_CHOICE module globals.

    Accepts an already-fetched list to avoid a second call to get_installed_ime_list().
    If omitted the list is fetched internally.
    """
    global TAMIL_CHOICE, ENGLISH_CHOICE, TAMIL_CHOICE_NAME, ENGLISH_CHOICE_NAME
    if installed_imes is None:
        try:
            installed_imes = get_installed_ime_list()
        except Exception:
            return
    tamil_id = tamil_name = english_id = english_name = None
    for klid, name in installed_imes:
        if tamil_id is None and _is_tamil_ime(klid):
            tamil_id, tamil_name = klid, name
        elif english_id is None and _is_english_ime(klid):
            english_id, english_name = klid, name
        if tamil_id and english_id:
            break
    if tamil_id:
        TAMIL_CHOICE = tamil_id
        TAMIL_CHOICE_NAME = tamil_name
    if english_id:
        ENGLISH_CHOICE = english_id
        ENGLISH_CHOICE_NAME = english_name


def _get_current_klid() -> str:
    """Return the active keyboard layout identifier in a platform-native format.

    Windows: 8-character uppercase hex KLID (e.g. "00030449")
    macOS:   bundle-ID string  (e.g. "com.apple.inputmethod.Tamil.AnjalIM")
    Other:   empty string
    """
    if sys.platform == "win32":
        try:
            buf = ctypes.create_unicode_buffer(9)
            return buf.value.upper().zfill(8) if user32.GetKeyboardLayoutNameW(buf) else ""
        except Exception:
            return ""
    if sys.platform == "darwin":
        return _macos_current_source_id()
    return ""


def _normalize_klid(klid: str) -> str:
    """Normalise a KLID for comparison.

    On Windows KLIDs are zero-padded to 8 uppercase hex digits.
    On macOS (and other platforms) the identifier is already canonical.
    """
    if sys.platform == "win32":
        return klid.upper().zfill(8)
    return klid


def _activate_klid(klid: str) -> None:
    """Activate a keyboard input source by its platform-native identifier."""
    if sys.platform == "win32":
        hkl = load_hkl(klid)
        activate_hkl(hkl)
    elif sys.platform == "darwin":
        _macos_select_source(klid)


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
        self.corrupted_settings_path: Optional[Path] = None
        self.corrupted_settings_reason: str = ""

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
                    if self.corrupted_settings_path == path:
                        self.corrupted_settings_path = None
                        self.corrupted_settings_reason = ""
                    return data
                self.corrupted_settings_path = path
                self.corrupted_settings_reason = "Top-level JSON value must be an object."
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.corrupted_settings_path = path
            self.corrupted_settings_reason = str(exc)
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


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class WordIndexOverlay(QWidget):
    def __init__(self, editor: 'CodeEditor'):
        super().__init__(editor)
        self.editor = editor
        self._adaptive_density = True
        self._backdrop_opacity_dark = 78
        self._backdrop_opacity_light = 70
        self._text_opacity = 255
        self._halo_opacity_dark = 230
        self._halo_opacity_light = 245
        self._text_color_name = "white"
        self._label_alignment_name = "right"
        self._cache_dirty = True
        self._block_word_cache = {}
        self._total_words = 0
        # Burst-mode flags set during typing; cleared by the flush timer.
        # _suppress_repaint: blocks per-keystroke partial repaints from updateRequest.
        # _skip_rebuild:     skips the expensive full-document block iteration in
        #                    _ensure_cache while the cache is known-dirty but the
        #                    burst hasn't ended yet (stale cache still used for paints
        #                    triggered by scroll/resize during the burst).
        self._suppress_repaint = False
        self._skip_rebuild = False

        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.hide()

    def setAdaptiveDensity(self, enabled: bool):
        value = bool(enabled)
        if self._adaptive_density == value:
            return
        self._adaptive_density = value
        if self.isVisible():
            self.update()

    def adaptiveDensity(self) -> bool:
        return self._adaptive_density

    def setVisualOpacities(
        self,
        backdrop_dark: int,
        backdrop_light: int,
        text_opacity: int,
        halo_dark: int,
        halo_light: int,
    ):
        values = (
            int(backdrop_dark),
            int(backdrop_light),
            int(text_opacity),
            int(halo_dark),
            int(halo_light),
        )
        if (
            self._backdrop_opacity_dark,
            self._backdrop_opacity_light,
            self._text_opacity,
            self._halo_opacity_dark,
            self._halo_opacity_light,
        ) == values:
            return
        (
            self._backdrop_opacity_dark,
            self._backdrop_opacity_light,
            self._text_opacity,
            self._halo_opacity_dark,
            self._halo_opacity_light,
        ) = values
        if self.isVisible():
            self.update()

    def setTextColorName(self, color_name: str):
        value = str(color_name).strip().lower()
        if not value:
            value = "yellow"
        if self._text_color_name == value:
            return
        self._text_color_name = value
        if self.isVisible():
            self.update()

    def setLabelAlignmentName(self, alignment_name: str):
        value = str(alignment_name).strip().lower()
        if value not in ("left", "center", "right"):
            value = "center"
        if self._label_alignment_name == value:
            return
        self._label_alignment_name = value
        if self.isVisible():
            self.update()

    @staticmethod
    def _color_for_name(name: str) -> QColor:
        palette = {
            "white": (255, 255, 255),
            "grey": (170, 170, 170),
            "black": (0, 0, 0),
            "yellow": (255, 226, 0),
            "green": (0, 204, 102),
            "blue": (61, 136, 255),
        }
        rgb = palette.get(name, palette["white"])
        return QColor(*rgb)

    def invalidate_cache(self):
        self._cache_dirty = True
        self._skip_rebuild = False   # deliberate invalidation always rebuilds on next paint
        self._suppress_repaint = False
        if self.isVisible():
            self.update()

    def total_words(self) -> int:
        self._ensure_cache()
        return self._total_words

    def sync_with_viewport(self, rect=None, dy: int = 0):
        viewport = self.editor.viewport()
        viewport_pos = viewport.pos()
        viewport_rect = viewport.rect()
        top_extra = max(0, int(getattr(self.editor, "_word_index_top_margin", 0)))
        self.setGeometry(
            viewport_pos.x(),
            viewport_pos.y() - top_extra,
            viewport_rect.width(),
            viewport_rect.height() + top_extra,
        )
        if not self.isVisible():
            return
        self.raise_()
        if dy:
            self.scroll(0, dy)
        # During a typing burst (_suppress_repaint=True), skip the per-keystroke
        # content-change partial repaints that Qt fires via updateRequest (rect!=None,
        # dy==0).  Scroll repaints (dy!=0) and full repaints (rect==None, from resize /
        # scrollbar / explicit flush) always proceed so the overlay never appears frozen
        # when the user scrolls or when the burst ends.
        if self._suppress_repaint and rect is not None and not dy:
            return
        if rect is None:
            self.update()
        else:
            self.update(QRect(rect.x(), rect.y() + top_extra, rect.width(), rect.height()))

    def _ensure_cache(self):
        if not self._cache_dirty:
            return
        if self._skip_rebuild:
            return  # typing burst active: reuse stale cache; flush timer will rebuild

        host = self.editor.window()
        extractor = getattr(host, "_extract_word_spans", None)
        if not callable(extractor):
            self._block_word_cache = {}
            self._total_words = 0
            self._cache_dirty = False
            return

        cache = {}
        next_word_index = 1
        block = self.editor.document().firstBlock()
        while block.isValid():
            spans = extractor(block.text())
            if spans:
                cache[block.blockNumber()] = (next_word_index, spans)
                next_word_index += len(spans)
            block = block.next()

        self._block_word_cache = cache
        self._total_words = next_word_index - 1
        self._cache_dirty = False

    def _build_draw_items(self, paint_rect) -> list[tuple[QRectF, str]]:
        self._ensure_cache()
        top_extra = float(max(0, int(getattr(self.editor, "_word_index_top_margin", 0))))
        viewport_rect = self.editor.viewport().rect()
        viewport_paint_top = float(paint_rect.top()) - top_extra
        viewport_paint_bottom = float(paint_rect.bottom()) - top_extra
        document = self.editor.document()
        block = self.editor.firstVisibleBlock()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()
        items = []
        cursor = QTextCursor(document)  # reused across all words — avoids 2 allocations per word
        fm = self.editor.fontMetrics()  # cached once per paint — avoids repeated object creation

        while block.isValid() and top <= viewport_paint_bottom:
            if block.isVisible() and bottom >= viewport_paint_top:
                cache_entry = self._block_word_cache.get(block.blockNumber())
                if cache_entry is not None:
                    block_start_index, spans = cache_entry
                    block_position = block.position()
                    block_text = block.text()
                    for offset, (start, end) in enumerate(spans):
                        cursor.setPosition(block_position + start)
                        start_rect = self.editor.cursorRect(cursor)
                        cursor.setPosition(block_position + end)
                        end_rect = self.editor.cursorRect(cursor)

                        if end_rect.y() != start_rect.y():
                            width = fm.horizontalAdvance(block_text[start:end])
                            end_rect = QRect(start_rect.x() + width, start_rect.y(), max(1, width), start_rect.height())

                        left = start_rect.x()
                        right = end_rect.x()
                        if right <= left:
                            width = fm.horizontalAdvance(block_text[start:end])
                            right = left + max(1, width)

                        if right < viewport_rect.left() or left > viewport_rect.right():
                            continue
                        if start_rect.bottom() < viewport_paint_top or start_rect.top() > viewport_paint_bottom:
                            continue

                        word_width = max(1.0, float(right - left))
                        draw_rect = QRectF(
                            float(left),
                            float(start_rect.y()) + top_extra - 8.0,
                            word_width,
                            float(start_rect.height()) * 0.52,
                        )
                        items.append((draw_rect, str(block_start_index + offset)))

            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()

        return items

    def _overlay_font(self, visible_items: int) -> QFont:
        font = QFont(self.editor.font())
        point_size = font.pointSizeF()
        if point_size <= 0:
            point_size = 12.0

        scale = 0.84
        if self._adaptive_density:
            if visible_items > 110:
                scale = 0.78
            if visible_items > 180:
                scale = 0.72
            if visible_items > 260:
                scale = 0.66

        font.setPointSizeF(max(7.0, point_size * scale))
        return font

    def paintEvent(self, event):
        if not self.isVisible():
            return

        items = self._build_draw_items(event.rect())
        if not items:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.Antialiasing, True)

        font = self._overlay_font(len(items))
        painter.setFont(font)

        base_color = self.editor.palette().base().color()
        text_base = self._color_for_name(self._text_color_name)
        text_color = QColor(text_base.red(), text_base.green(), text_base.blue(), self._text_opacity)
        if text_base.lightness() >= 128:
            halo_rgb = (0, 0, 0)
        else:
            halo_rgb = (255, 255, 255)
        if base_color.lightness() < 128:
            backdrop_color = QColor(255, 255, 255, self._backdrop_opacity_dark)
            halo_color = QColor(halo_rgb[0], halo_rgb[1], halo_rgb[2], self._halo_opacity_dark)
        else:
            backdrop_color = QColor(0, 0, 0, self._backdrop_opacity_light)
            halo_color = QColor(halo_rgb[0], halo_rgb[1], halo_rgb[2], self._halo_opacity_light)

        top_extra = max(0, int(getattr(self.editor, "_word_index_top_margin", 0)))
        painter.fillRect(
            QRectF(
                0.0,
                float(top_extra),
                float(self.editor.viewport().width()),
                float(self.editor.viewport().height()),
            ),
            backdrop_color,
        )

        if self._label_alignment_name == "left":
            text_alignment = Qt.AlignLeft | Qt.AlignVCenter
        elif self._label_alignment_name == "right":
            text_alignment = Qt.AlignRight | Qt.AlignVCenter
        else:
            text_alignment = Qt.AlignCenter

        halo_offsets = ((-1.0, 0.0), (1.0, 0.0), (0.0, -1.0), (0.0, 1.0))
        for draw_rect, label in items:
            for dx, dy in halo_offsets:
                painter.setPen(halo_color)
                painter.drawText(draw_rect.translated(dx, dy), text_alignment, label)
            painter.setPen(text_color)
            painter.drawText(draw_rect, text_alignment, label)


class SpacedPlainTextDocumentLayout(QPlainTextDocumentLayout):
    """Drop-in QPlainTextDocumentLayout replacement that adds configurable extra
    pixels after every block.  QPlainTextDocumentLayout hard-codes block height to
    font metrics and ignores QTextBlockFormat line-height/margin properties entirely,
    so the only way to change line spacing is to override blockBoundingRect()."""

    def __init__(self, doc):
        super().__init__(doc)
        self._extra_px = 0.0

    def setExtraPixels(self, px: float):
        self._extra_px = max(0.0, float(px))
        doc = self.document()
        if doc:
            self.documentChanged(0, 0, doc.characterCount())

    def extraPixels(self) -> float:
        return self._extra_px

    def blockBoundingRect(self, block):
        r = super().blockBoundingRect(block)
        if self._extra_px > 0.0 and block.isValid():
            return QRectF(r.x(), r.y(), r.width(), r.height() + self._extra_px)
        return r


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Flags first so slots can use them safely
        self._highlight_current_line = True
        self._wrap_enabled = True
        self._last_wrap_enabled = True
        self._last_wrap_viewport_width = -1
        self._refreshing_wrap_layout = False
        self._line_numbers_visible = True
        self._text_margin_percent = 0
        self._click_count = 0
        self._last_click_ts = 0.0
        self._word_index_visible = False
        self._word_index_top_margin = 20
        self._line_spacing_percent = 100.0

        self.lineNumberArea = LineNumberArea(self)
        self.wordIndexOverlay = WordIndexOverlay(self)

        # Install spacing-aware layout.  Must be done before any signal connections
        # that reference the document layout, and before setting any text.
        self._spacing_layout = SpacedPlainTextDocumentLayout(self.document())
        self.document().setDocumentLayout(self._spacing_layout)

        # Debounce timer: coalesces typing bursts into a single overlay repaint.
        # Fires 150 ms after the last content change — per-keystroke rebuilds avoided.
        self._overlay_dirty_timer = QTimer(self)
        self._overlay_dirty_timer.setSingleShot(True)
        self._overlay_dirty_timer.setInterval(150)
        self._overlay_dirty_timer.timeout.connect(self._flush_overlay_update)

        # Signals to keep the number area in sync
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.updateRequest.connect(self._sync_word_index_overlay)
        self.cursorPositionChanged.connect(self.updateCurrentLineHighlight)
        self.document().contentsChange.connect(self._on_document_contents_change)
        self.verticalScrollBar().valueChanged.connect(self._update_word_index_overlay)
        self.horizontalScrollBar().valueChanged.connect(self._update_word_index_overlay)

        self.updateLineNumberAreaWidth(0)
        self.setWordWrap(True)
        self.updateCurrentLineHighlight()
        self.wordIndexOverlay.sync_with_viewport()

    # ----- Word wrap -----
    def setWordWrap(self, enabled: bool):
        self._wrap_enabled = bool(enabled)
        self._refresh_wrap_layout(force=True)
        self.updateLineNumberAreaWidth(0)
        self._update_word_index_overlay()

    def isWordWrap(self) -> bool:
        return self._wrap_enabled

    def _refresh_wrap_layout(self, force: bool = False):
        if self._refreshing_wrap_layout:
            return

        viewport_width = int(self.viewport().width())
        wrap_enabled = bool(self._wrap_enabled)

        if (
            not force
            and viewport_width == self._last_wrap_viewport_width
            and wrap_enabled == self._last_wrap_enabled
        ):
            return

        self._last_wrap_viewport_width = viewport_width
        self._last_wrap_enabled = wrap_enabled

        self._refreshing_wrap_layout = True
        try:
            if wrap_enabled:
                # Re-apply wrap mode so QTextDocument recomputes line breaks against
                # the latest viewport width after margin/geometry changes.
                self.setLineWrapMode(QPlainTextEdit.NoWrap)
                self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
                self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            else:
                self.setLineWrapMode(QPlainTextEdit.NoWrap)
                self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        finally:
            self._refreshing_wrap_layout = False

    # ----- Line numbers plumbing -----
    def lineNumberAreaWidth(self) -> int:
        if not self._line_numbers_visible:
            return 0
        digits = max(2, len(str(max(1, self.blockCount()))))
        space = 6 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def _effective_text_margin_px(self) -> int:
        percent = max(0, int(getattr(self, "_text_margin_percent", 0)))
        if percent <= 0:
            return 0

        host = self.window()
        base_width = host.width() if host is not None else self.width()
        if base_width <= 0:
            base_width = self.width()

        requested_each = int(round(base_width * (percent / 100.0)))

        line_area = self.lineNumberAreaWidth()
        available = max(0, self.contentsRect().width() - line_area)
        min_text_width = 320
        max_each = max(0, (available - min_text_width) // 2)

        return min(requested_each, max_each)

    def _apply_viewport_margins(self):
        line_area = self.lineNumberAreaWidth()
        text_margin = self._effective_text_margin_px()
        top_margin = self._word_index_top_margin if self._word_index_visible else 0
        self.setViewportMargins(line_area + text_margin, top_margin, text_margin, 0)
        self.lineNumberArea.setVisible(self._line_numbers_visible)

    def lineNumberAreaSizeHint(self):
        return self.sizeHint().expandedTo(self.viewport().size())

    def updateLineNumberAreaWidth(self, _):
        self._apply_viewport_margins()
        self._update_word_index_overlay()

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_viewport_margins()
        cr = self.contentsRect()
        if self._line_numbers_visible:
            self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))
        self._refresh_wrap_layout()
        self._update_word_index_overlay()

    def lineNumberAreaPaintEvent(self, event):
        if not self._line_numbers_visible:
            return
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

    def setLineNumbersVisible(self, visible: bool):
        self._line_numbers_visible = bool(visible)
        self.updateLineNumberAreaWidth(0)
        self.viewport().update()
        self._update_word_index_overlay()

    def isLineNumbersVisible(self) -> bool:
        return self._line_numbers_visible

    def setTextMarginPercent(self, percent: int):
        value = int(percent)
        if value < 0:
            value = 0
        self._text_margin_percent = value
        self._apply_viewport_margins()
        self._refresh_wrap_layout()
        self.viewport().update()
        self._update_word_index_overlay()

    def textMarginPercent(self) -> int:
        return int(getattr(self, "_text_margin_percent", 0))

    def updateCurrentLineHighlight(self):
        if not getattr(self, "_highlight_current_line", True):
            return
        # Keep simple; rely on palette for current line appearance.
        pass

    def setFont(self, font):
        super().setFont(font)
        self._apply_layout_spacing()  # base px changes with font, recalculate
        self.wordIndexOverlay.invalidate_cache()
        self._update_word_index_overlay()

    def setWordIndexVisible(self, visible: bool):
        self._word_index_visible = bool(visible)
        self._apply_viewport_margins()
        if self._word_index_visible:
            self.wordIndexOverlay.invalidate_cache()
            self.wordIndexOverlay.show()
            self.wordIndexOverlay.sync_with_viewport()
        else:
            self.wordIndexOverlay.hide()
            self.viewport().update()

    def isWordIndexVisible(self) -> bool:
        return self._word_index_visible

    def setWordIndexAdaptiveDensity(self, enabled: bool):
        self.wordIndexOverlay.setAdaptiveDensity(enabled)

    def wordIndexAdaptiveDensity(self) -> bool:
        return self.wordIndexOverlay.adaptiveDensity()

    def setWordIndexVisualOpacities(
        self,
        backdrop_dark: int,
        backdrop_light: int,
        text_opacity: int,
        halo_dark: int,
        halo_light: int,
    ):
        self.wordIndexOverlay.setVisualOpacities(
            backdrop_dark,
            backdrop_light,
            text_opacity,
            halo_dark,
            halo_light,
        )

    def setWordIndexColorName(self, color_name: str):
        self.wordIndexOverlay.setTextColorName(color_name)

    def setWordIndexAlignmentName(self, alignment_name: str):
        self.wordIndexOverlay.setLabelAlignmentName(alignment_name)

    def setWordIndexTopMargin(self, px: int):
        value = max(0, min(60, int(px)))
        if self._word_index_top_margin == value:
            return
        self._word_index_top_margin = value
        self._apply_viewport_margins()
        self._update_word_index_overlay()

    # --- Line spacing ---
    def setLineSpacingPercent(self, percent: float):
        """Set line spacing as a percentage of the natural line height (100 = default)."""
        try:
            value = float(max(50.0, min(300.0, float(percent))))
        except Exception:
            value = 100.0
        self._line_spacing_percent = value
        self._apply_layout_spacing()

    def _apply_layout_spacing(self):
        """Convert stored percent to pixels and push to the spacing layout."""
        percent = getattr(self, '_line_spacing_percent', 100.0)
        extra_fraction = max(0.0, percent / 100.0 - 1.0)
        base_px = float(max(1, self.fontMetrics().height()))
        self._spacing_layout.setExtraPixels(extra_fraction * base_px)

    def _on_document_contents_change(self, pos: int, removed: int, added: int):
        # Always mark dirty + set burst flags, even when overlay is hidden, so the
        # overlay is immediately correct when it next becomes visible.
        self.wordIndexOverlay._cache_dirty = True
        self.wordIndexOverlay._suppress_repaint = True   # freeze visual during burst
        self.wordIndexOverlay._skip_rebuild = True       # skip block iteration during burst
        if not self.wordIndexOverlay.isVisible():
            return
        # Restart the debounce window; one clean repaint fires 150 ms after typing pauses.
        self._overlay_dirty_timer.start()

    def _flush_overlay_update(self):
        """Fires once, 150 ms after the last content change.  Clears burst flags and
        triggers one clean repaint.  _cache_dirty is still True from the last change,
        so _ensure_cache will do a full rebuild for this repaint."""
        self.wordIndexOverlay._suppress_repaint = False
        self.wordIndexOverlay._skip_rebuild = False
        if self.wordIndexOverlay.isVisible():
            self.wordIndexOverlay.update()

    def _sync_word_index_overlay(self, rect, dy):
        self.wordIndexOverlay.sync_with_viewport(rect, dy)

    def _update_word_index_overlay(self):
        self.wordIndexOverlay.sync_with_viewport()

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

    def _trigger_sorkuvai_search(self, query: str):
        cleaned = self._normalize_search_text(query)
        if not cleaned:
            return
        handler = getattr(self.window(), "launch_sorkuvai_search", None)
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
        if not selected_text:
            probe = self.cursorForPosition(event.pos())
            if not probe.isNull():
                probe.select(QTextCursor.WordUnderCursor)
                selected_text = self._normalize_search_text(probe.selectedText())
        if selected_text:
            display_text = selected_text if len(selected_text) <= 48 else f"{selected_text[:45]}..."
            search_action = QAction(f'Search Google for "{display_text}"', menu)
            search_action.triggered.connect(
                lambda checked=False, text=selected_text: self._trigger_search(text)
            )
            before_action = menu.actions()[0] if menu.actions() else None
            is_single_word = not re.search(r"\s", selected_text)
            if is_single_word:
                sorkuvai_action = QAction(f'Search Sorkuvai for "{display_text}"', menu)
                sorkuvai_action.triggered.connect(
                    lambda checked=False, text=selected_text: self._trigger_sorkuvai_search(text)
                )
                menu.insertAction(before_action, search_action)
                menu.insertAction(search_action, sorkuvai_action)
            else:
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

        nav_keys = {
            Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
            Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown
        }
        if event.key() in nav_keys:
            handler = getattr(self.window(), "_clear_word_highlight_on_navigation", None)
            if callable(handler):
                handler()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        handler = getattr(self.window(), "_clear_word_highlight_on_blur", None)
        if callable(handler):
            handler()

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
# Find / Replace dialog
# ---------------------
class FindReplaceDialog(QDialog):
    find_next = Signal(str)
    replace = Signal(str, str)
    replace_all = Signal(str, str)
    closed = Signal()

    def __init__(self, parent=None, *, replace_enabled: bool = False):
        super().__init__(parent)
        self._replace_enabled = bool(replace_enabled)
        self.setWindowTitle("Replace" if self._replace_enabled else "Find")
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(420)

        self.find_edit = QLineEdit(self)
        self.find_edit.returnPressed.connect(self._emit_find_next)

        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("Find what:"), 0, 0)
        form_layout.addWidget(self.find_edit, 0, 1)

        self.replace_edit = None
        if self._replace_enabled:
            self.replace_edit = QLineEdit(self)
            self.replace_edit.returnPressed.connect(self._emit_replace)
            form_layout.addWidget(QLabel("Replace with:"), 1, 0)
            form_layout.addWidget(self.replace_edit, 1, 1)

        tip_text = "ℹ️ <a href=\"#\">Escape sequences…</a>"
        self.tip_label = QLabel(tip_text, self)
        self.tip_label.setStyleSheet("color: #666666;")
        self.tip_label.setWordWrap(True)
        self.tip_label.setTextFormat(Qt.RichText)
        self.tip_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.tip_label.setOpenExternalLinks(False)
        self.tip_label.linkActivated.connect(self._show_escape_help)
        tip_row = 1 if not self._replace_enabled else 2
        form_layout.addWidget(self.tip_label, tip_row, 0, 1, 2)

        self.find_next_btn = QPushButton("Find Next", self)
        self.cancel_btn = QPushButton("Close", self)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.find_next_btn)

        self.replace_btn = None
        self.replace_all_btn = None
        if self._replace_enabled:
            self.replace_btn = QPushButton("Replace", self)
            self.replace_all_btn = QPushButton("Replace All", self)
            button_layout.addWidget(self.replace_btn)
            button_layout.addWidget(self.replace_all_btn)

        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch(1)

        main_layout = QHBoxLayout()
        main_layout.addLayout(form_layout, 1)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        self.find_next_btn.clicked.connect(self._emit_find_next)
        self.cancel_btn.clicked.connect(self.hide)
        if self._replace_enabled and self.replace_btn and self.replace_all_btn:
            self.replace_btn.clicked.connect(self._emit_replace)
            self.replace_all_btn.clicked.connect(self._emit_replace_all)

        self.find_next_btn.setDefault(True)

    def _show_escape_help(self, _link: str = "") -> None:
        sequences = [
            ("\\n", "newline"),
            ("\\r", "carriage return"),
            ("\\t", "tab"),
            ("\\f", "form feed"),
            ("\\v", "vertical tab"),
            ("\\0", "null character"),
            ("\\\\", "literal backslash"),
            ("\\xHH", "byte value (replace HH with two hex digits)"),
            ("\\u0000", "Unicode code point (replace digits with hex)")
        ]

        dialog = QDialog(self)
        dialog.setWindowTitle("Escape Sequences")
        dialog.setModal(True)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        info_label = QLabel("Click a sequence to insert it into the selected field.", dialog)
        layout.addWidget(info_label)

        target_layout = QHBoxLayout()
        target_label = QLabel("Insert into:", dialog)
        target_layout.addWidget(target_label)

        button_group = QButtonGroup(dialog)
        find_radio = QRadioButton("Find", dialog)
        button_group.addButton(find_radio)
        target_layout.addWidget(find_radio)

        replace_radio = None
        if self.replace_edit is not None:
            replace_radio = QRadioButton("Replace", dialog)
            button_group.addButton(replace_radio)
            target_layout.addWidget(replace_radio)

        target_layout.addStretch(1)
        layout.addLayout(target_layout)

        default_to_replace = bool(self.replace_edit and self.replace_edit.hasFocus())
        if replace_radio:
            replace_radio.setChecked(default_to_replace)
            find_radio.setChecked(not default_to_replace)
        else:
            find_radio.setChecked(True)

        grid = QGridLayout()
        layout.addLayout(grid)

        focus_target = [self.find_edit]

        def resolve_target() -> QLineEdit:
            if replace_radio and replace_radio.isChecked() and self.replace_edit is not None:
                return self.replace_edit
            return self.find_edit

        def handle_insert(seq: str) -> None:
            target = resolve_target()
            focus_target[0] = target
            self._insert_escape_sequence(seq, target)

        for row, (seq, description) in enumerate(sequences):
            button = QPushButton(seq, dialog)
            button.clicked.connect(lambda _checked=False, s=seq: handle_insert(s))
            grid.addWidget(button, row, 0)
            desc_label = QLabel(description, dialog)
            grid.addWidget(desc_label, row, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        button_box.rejected.connect(dialog.reject)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)

        dialog.exec()

        target = focus_target[0]
        if target is not None:
            target.setFocus()

    def _insert_escape_sequence(self, sequence: str, target: Optional[QLineEdit] = None) -> None:
        if target is None:
            target = self.find_edit
        text = target.text()
        if target.hasSelectedText():
            start = target.selectionStart()
            end = start + len(target.selectedText())
            new_text = text[:start] + sequence + text[end:]
            target.setText(new_text)
            target.setCursorPosition(start + len(sequence))
        else:
            pos = target.cursorPosition()
            new_text = text[:pos] + sequence + text[pos:]
            target.setText(new_text)
            target.setCursorPosition(pos + len(sequence))

    def set_find_text(self, text: str) -> None:
        self.find_edit.setText(text)
        self.find_edit.selectAll()

    def set_replace_text(self, text: str) -> None:
        if self.replace_edit is None:
            return
        self.replace_edit.setText(text)
        self.replace_edit.selectAll()

    def focus_find_field(self) -> None:
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def focus_replace_field(self) -> None:
        if self.replace_edit is None:
            return
        self.replace_edit.setFocus()
        self.replace_edit.selectAll()

    def set_default_action(self, action: str) -> None:
        buttons = [self.find_next_btn, self.replace_btn, self.replace_all_btn, self.cancel_btn]
        for btn in buttons:
            if btn is not None:
                btn.setDefault(False)

        if action == "replace" and self.replace_btn is not None:
            self.replace_btn.setDefault(True)
            self.replace_btn.setFocus()
        elif action == "replace_all" and self.replace_all_btn is not None:
            self.replace_all_btn.setDefault(True)
            self.replace_all_btn.setFocus()
        else:
            self.find_next_btn.setDefault(True)
            self.find_next_btn.setFocus()

    def _emit_find_next(self) -> None:
        self.find_next.emit(self.find_edit.text())

    def _emit_replace(self) -> None:
        if self.replace_edit is None:
            return
        self.replace.emit(self.find_edit.text(), self.replace_edit.text())

    def _emit_replace_all(self) -> None:
        if self.replace_edit is None:
            return
        self.replace_all.emit(self.find_edit.text(), self.replace_edit.text())

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.closed.emit()


# ---------------------
# Main window
# ---------------------
class Notepad(QMainWindow):
    def __init__(self, initial_file: Optional[str] = None, restore_last_session: bool = True):
        super().__init__()
        self.setWindowTitle("Untitled - Neight")
        self.resize(1000, 650)
        self.setMinimumWidth(520)  # Ensures the right-pinned Settings menu is never cut off

        self.settings = SettingsManager()
        self.default_directory = Path.home()
        self._restore_maximized = False
        self._initial_file = initial_file
        self._restore_last_session = bool(restore_last_session)
        self._last_session_file = None

        self.editor = CodeEditor(self)
        self.setCentralWidget(self.editor)

        self.status = QStatusBar(self)
        self.setStatusBar(self.status)

        # Status widgets — each has a fixed minimumWidth so toggling one never
        # shifts the others sideways.  Visibility is controlled by the Format ▸
        # Status Bar menu; widths are sized to their widest possible content.
        _fm = self.fontMetrics()
        self.word_match_label = QLabel("", self)
        self.word_match_label.setMinimumWidth(_fm.horizontalAdvance("Matches: 0000"))

        # Three separate labels so each can be hidden independently
        self.words_label = ClickableLabel("", self)
        self.words_label.setToolTip("Toggle Word Index overlay")
        self.words_label.setMinimumWidth(_fm.horizontalAdvance("Words: 000000"))
        self.sentences_label = QLabel("", self)
        self.sentences_label.setMinimumWidth(_fm.horizontalAdvance("Sentences: 00000"))
        self.chars_label = QLabel("", self)
        self.chars_label.setMinimumWidth(_fm.horizontalAdvance("Chars: 0000000"))

        self.line_label = QLabel("", self)
        self.line_label.setMinimumWidth(_fm.horizontalAdvance("Ln 000000"))
        self.col_label = QLabel("", self)
        self.col_label.setMinimumWidth(_fm.horizontalAdvance("Col 0000"))

        self.reading_time_label = QLabel("", self)
        self.reading_time_label.setMinimumWidth(_fm.horizontalAdvance("Read: 000 min | Ta 100% En 100%"))
        self.layout_label = QLabel(get_current_layout_label(), self)

        self.status.addPermanentWidget(self.reading_time_label)
        self.status.addPermanentWidget(self.word_match_label)
        self.status.addPermanentWidget(self.words_label)
        self.status.addPermanentWidget(self.sentences_label)
        self.status.addPermanentWidget(self.chars_label)
        self.status.addPermanentWidget(self.line_label)
        self.status.addPermanentWidget(self.col_label)
        self.status.addPermanentWidget(self.layout_label)

        # Legacy alias so existing code that references count_label still compiles
        self.count_label = self.words_label

        self._find_dialog = None
        self._replace_dialog = None
        self._last_find = ""
        self._last_find_raw = ""
        self._last_replace = ""
        self._last_replace_raw = ""
        self._progress_bar = None
        self._word_highlight_selections = []
        self._current_highlight_word = None
        self._base_extra_selections = []

        self.current_path = None
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_enabled = False
        
        # Keyboard layout switching state
        # Detect the current system layout without switching anything.
        self._current_layout = get_current_layout()  # 0 = English India, 1 = Tamil Anjal
        self._ctrl_press_time = 0  # For double Ctrl detection
        self._ctrl_press_timer = QTimer(self)
        self._ctrl_press_timer.setSingleShot(True)
        self._ctrl_press_timer.timeout.connect(self._reset_ctrl_press)

        # Keyboard quick switch settings (defaults; overridden properly in _load_preferences)
        self._quick_switch_enabled = True
        self._force_anjal_english = True
        self._installed_imes = []  # Populated in _load_preferences

        # Appearance (defaults; overridden in _load_preferences)
        self._appearance_theme_mode = "follow_os"
        self._appearance_custom_bg = "#202124"
        self._appearance_custom_fg = "#f1f3f4"
        self._line_spacing_preset = "normal"

        # Status bar item visibility (defaults; overridden in _load_preferences)
        self._status_show_words = True
        self._status_show_sentences = True
        self._status_show_chars = True
        self._status_show_line = True
        self._status_show_col = True

        # Experimental features (defaults; overridden in _load_preferences)
        self._unicode_substring_highlight = False
        self._reading_time_enabled = False
        self._word_index_enabled = False
        self._word_index_adaptive_density = True
        self._word_index_backdrop_opacity_dark = 78
        self._word_index_backdrop_opacity_light = 70
        self._word_index_text_opacity = 255
        self._word_index_halo_opacity_dark = 230
        self._word_index_halo_opacity_light = 245
        self._word_index_color = "white"
        self._word_index_alignment = "right"
        self._word_index_top_margin = 20
        self._tamil_reading_wpm = 150
        self._english_reading_wpm = 250
        self._google_search_url_prefix = DEFAULT_GOOGLE_SEARCH_URL_PREFIX
        self._sorkuvai_search_url_prefix = DEFAULT_SORKUVAI_SEARCH_URL_PREFIX

        # Debounce expensive status computations during rapid typing/deletions.
        self._status_update_timer = QTimer(self)
        self._status_update_timer.setSingleShot(True)
        self._status_update_timer.timeout.connect(self._update_status_bar)

        self._create_actions()
        self._create_menus()
        self._connect_signals()
        self._install_shortcuts()
        self._install_layout_shortcuts()

        self._startup_cancelled = False
        if not self._load_preferences():
            self._startup_cancelled = True
            return
        self._update_status_bar()
        self._update_export_menu_visibility()

        if initial_file:
            self._load_initial_path(initial_file)

    # --- UI setup ---
    def _create_actions(self):
        # File
        self.new_act = QAction("New", self)
        self.new_act.setShortcut(QKeySequence.New)  # Ctrl+N / Cmd+N

        self.new_window_act = QAction("New Window", self)
        if sys.platform == "darwin":
            self.new_window_act.setShortcut(QKeySequence("Meta+Shift+N"))
        else:
            self.new_window_act.setShortcut(QKeySequence("Ctrl+Shift+N"))

        self.open_act = QAction("Open…", self)
        self.open_act.setShortcut(QKeySequence.Open)  # Ctrl+O / Cmd+O

        self.save_act = QAction("&Save", self)
        self.save_act.setShortcut(QKeySequence.Save)  # Ctrl+S / Cmd+S

        self.save_as_act = QAction("Save &As…", self)
        self.save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))

        self.export_text_pdf_act = QAction("Export Text to PDF…", self)
        self.export_md_pdf_act = QAction("Export Markdown to PDF…", self)

        self.exit_act = QAction("E&xit", self)
        if sys.platform == "win32":
            self.exit_act.setShortcut(QKeySequence("Alt+F4"))
        else:
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
        self.insert_blank_lines_act = QAction("Insert Blank Lines", self)

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

        self.line_numbers_act = QAction("Line Numbers in Margin", self, checkable=True)
        self.line_numbers_act.setChecked(True)

        # Status bar item visibility
        self.status_words_act = QAction("Word Count", self, checkable=True)
        self.status_words_act.setChecked(True)
        self.status_sentences_act = QAction("Sentence Count", self, checkable=True)
        self.status_sentences_act.setChecked(True)
        self.status_chars_act = QAction("Character Count", self, checkable=True)
        self.status_chars_act.setChecked(True)
        self.status_line_act = QAction("Cursor Line", self, checkable=True)
        self.status_line_act.setChecked(True)
        self.status_col_act = QAction("Cursor Column", self, checkable=True)
        self.status_col_act.setChecked(True)

        self.line_spacing_extra_tight_act = QAction("Very Tight", self, checkable=True)
        self.line_spacing_tight_act = QAction("Tight", self, checkable=True)
        self.line_spacing_normal_act = QAction("Default", self, checkable=True)
        self.line_spacing_casual_act = QAction("Relaxed", self, checkable=True)
        self.line_spacing_extra_casual_act = QAction("Loose", self, checkable=True)

        self.margin_5_act = QAction("5%", self)
        self.margin_5_act.setCheckable(True)
        self.margin_10_act = QAction("10%", self)
        self.margin_10_act.setCheckable(True)
        self.margin_15_act = QAction("15%", self)
        self.margin_15_act.setCheckable(True)
        self.margin_20_act = QAction("20%", self)
        self.margin_20_act.setCheckable(True)
        self.margin_25_act = QAction("25%", self)
        self.margin_25_act.setCheckable(True)
        self.margin_reset_act = QAction("Reset Margin", self)

        self.font_act = QAction("Font…", self)

        # Auto-save
        self.autosave_disabled_act = QAction("Disabled", self, checkable=True)
        self.autosave_2min_act = QAction("Every 2 minutes", self, checkable=True)
        self.autosave_5min_act = QAction("Every 5 minutes", self, checkable=True)
        self.autosave_15min_act = QAction("Every 15 minutes", self, checkable=True)
        self.autosave_30min_act = QAction("Every 30 minutes", self, checkable=True)

        # Settings
        self.appearance_act = QAction("Appearance...", self)
        self.keyboards_act = QAction("Language Switch…", self)

        # Advanced (experimental features)
        self.unicode_substring_highlight_act = QAction("Highlight partial word selections", self, checkable=True)
        self.unicode_substring_highlight_act.setChecked(False)
        self.reading_time_act = QAction("Reading Time...", self)
        self.word_index_act = QAction("Word Index", self, checkable=True)
        self.word_index_act.setShortcut(QKeySequence("Ctrl+Shift+W"))
        self.normalize_unicode_act = QAction("Normalize Unicode (NFC)", self)

        # Help
        self.about_act = QAction("About", self)
        self.debug_info_act = QAction("Debug Info", self)

    def _create_menus(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.new_act)
        file_menu.addAction(self.new_window_act)
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
        edit_menu.addAction(self.insert_blank_lines_act)
        edit_menu.addSeparator()
        edit_menu.addAction(self.normalize_unicode_act)

        # Markdown menu
        insert_menu = menubar.addMenu("&Markdown")
        
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
        format_menu.addAction(self.font_act)
        line_spacing_menu = format_menu.addMenu("Line Spacing")
        line_spacing_menu.addAction(self.line_spacing_extra_tight_act)
        line_spacing_menu.addAction(self.line_spacing_tight_act)
        line_spacing_menu.addAction(self.line_spacing_normal_act)
        line_spacing_menu.addAction(self.line_spacing_casual_act)
        line_spacing_menu.addAction(self.line_spacing_extra_casual_act)
        margins_menu = format_menu.addMenu("Margins")
        margins_menu.addAction(self.margin_5_act)
        margins_menu.addAction(self.margin_10_act)
        margins_menu.addAction(self.margin_15_act)
        margins_menu.addAction(self.margin_20_act)
        margins_menu.addAction(self.margin_25_act)
        margins_menu.addSeparator()
        margins_menu.addAction(self.margin_reset_act)
        format_menu.addAction(self.wrap_act)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self.line_numbers_act)
        view_menu.addAction(self.word_index_act)
        view_menu.addAction(self.unicode_substring_highlight_act)
        view_menu.addSeparator()
        status_bar_menu = view_menu.addMenu("Status Bar")
        status_bar_menu.addAction(self.status_words_act)
        status_bar_menu.addAction(self.status_sentences_act)
        status_bar_menu.addAction(self.status_chars_act)
        status_bar_menu.addAction(self.reading_time_act)
        status_bar_menu.addSeparator()
        status_bar_menu.addAction(self.status_line_act)
        status_bar_menu.addAction(self.status_col_act)

        settings_menu = menubar.addMenu("&Settings")
        autosave_menu = settings_menu.addMenu("Auto-save")
        autosave_menu.addAction(self.autosave_disabled_act)
        autosave_menu.addAction(self.autosave_2min_act)
        autosave_menu.addAction(self.autosave_5min_act)
        autosave_menu.addAction(self.autosave_15min_act)
        autosave_menu.addAction(self.autosave_30min_act)
        settings_menu.addSeparator()
        settings_menu.addAction(self.appearance_act)
        settings_menu.addAction(self.keyboards_act)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self.about_act)
        help_menu.addSeparator()
        help_menu.addAction(self.debug_info_act)

    def _connect_signals(self):
        # File
        self.new_act.triggered.connect(self.new_file)
        self.new_window_act.triggered.connect(self.new_window)
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
        self.insert_blank_lines_act.triggered.connect(self.insert_blank_lines)

        # Format
        self.wrap_act.toggled.connect(self._toggle_wrap)
        self.line_numbers_act.toggled.connect(self._toggle_line_numbers)
        self.status_words_act.toggled.connect(lambda v: self._toggle_status_item("words", v))
        self.status_sentences_act.toggled.connect(lambda v: self._toggle_status_item("sentences", v))
        self.status_chars_act.toggled.connect(lambda v: self._toggle_status_item("chars", v))
        self.status_line_act.toggled.connect(lambda v: self._toggle_status_item("line", v))
        self.status_col_act.toggled.connect(lambda v: self._toggle_status_item("col", v))
        self.margin_5_act.triggered.connect(lambda: self._set_text_margin_percent(5))
        self.margin_10_act.triggered.connect(lambda: self._set_text_margin_percent(10))
        self.margin_15_act.triggered.connect(lambda: self._set_text_margin_percent(15))
        self.margin_20_act.triggered.connect(lambda: self._set_text_margin_percent(20))
        self.margin_25_act.triggered.connect(lambda: self._set_text_margin_percent(25))
        self.margin_reset_act.triggered.connect(lambda: self._set_text_margin_percent(0))
        self.line_spacing_extra_tight_act.triggered.connect(lambda: self._set_line_spacing_preset("extra_tight"))
        self.line_spacing_tight_act.triggered.connect(lambda: self._set_line_spacing_preset("tight"))
        self.line_spacing_normal_act.triggered.connect(lambda: self._set_line_spacing_preset("normal"))
        self.line_spacing_casual_act.triggered.connect(lambda: self._set_line_spacing_preset("casual"))
        self.line_spacing_extra_casual_act.triggered.connect(lambda: self._set_line_spacing_preset("extra_casual"))
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

        # Settings
        self.appearance_act.triggered.connect(self._show_appearance_dialog)
        self.keyboards_act.triggered.connect(self._show_keyboards_dialog)

        # Advanced (experimental features)
        self.reading_time_act.triggered.connect(self._show_reading_time_dialog)
        self.word_index_act.toggled.connect(self._toggle_word_index)
        self.normalize_unicode_act.triggered.connect(self._normalize_unicode_text)
        self.unicode_substring_highlight_act.toggled.connect(self._toggle_unicode_substring_highlight)

        # Help
        self.about_act.triggered.connect(self.show_about)
        self.debug_info_act.triggered.connect(self._show_debug_info)

        # Status updates
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.selectionChanged.connect(self._update_word_highlights)
        self.editor.cursorPositionChanged.connect(self._update_cursor_position_status)
        self.count_label.clicked.connect(self._toggle_word_index_from_status_label)

        # Update window title on modification
        self.editor.modificationChanged.connect(self._update_title)

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_restore_maximized", False):
            self.setWindowState(self.windowState() | Qt.WindowMaximized)
            self._restore_maximized = False

    def keyReleaseEvent(self, event):
        """Detect double Ctrl press to toggle keyboard layout."""
        if sys.platform not in ("win32", "darwin"):
            super().keyReleaseEvent(event)
            return

        # Only track double-Ctrl presses when quick switch is enabled
        if event.key() in (Qt.Key_Control, Qt.Key_Meta):
            if getattr(self, '_quick_switch_enabled', False):
                current_time = time.time()

                # Second Ctrl release within 500 ms — trigger the switch
                if self._ctrl_press_time > 0 and (current_time - self._ctrl_press_time) < 0.5:
                    self._quick_switch()
                    self._ctrl_press_time = 0  # Reset
                    self._ctrl_press_timer.stop()
                else:
                    # First Ctrl release — open the detection window
                    self._ctrl_press_time = current_time
                    self._ctrl_press_timer.start(500)  # 500 ms timeout

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
        if sys.platform not in ("win32", "darwin"):
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
        """Switch to the first (0) or second (1) keyboard layout.

        In force mode (_force_anjal_english=True): always uses the auto-detected
        English / Tamil pair (ENGLISH_CHOICE / TAMIL_CHOICE).
        In dynamic mode (_force_anjal_english=False): uses the first two entries
        in the user's installed keyboard layout list, matching the behaviour of
        the double-Ctrl quick switch.
        """
        if sys.platform not in ("win32", "darwin"):
            return

        self._current_layout = target_layout
        try:
            if getattr(self, '_force_anjal_english', True):
                # Force mode: use the auto-detected Tamil / English pair
                if target_layout == 0:
                    switch_to_english_india()
                    self.layout_label.setText(f"Keyboard: {ENGLISH_CHOICE_NAME}")
                else:
                    switch_to_tamil_anjal()
                    self.layout_label.setText(f"Keyboard: {TAMIL_CHOICE_NAME}")
            else:
                # Dynamic mode: use whatever the first two installed layouts are
                imes = getattr(self, '_installed_imes', [])
                if len(imes) > target_layout:
                    klid, name = imes[target_layout]
                    _activate_klid(klid)
                    self.layout_label.setText(f"Keyboard: {name}")
                else:
                    # Fallback: not enough layouts available — do nothing
                    pass
        except Exception:
            self.layout_label.setText("Keyboard: Error")

    def _quick_switch(self):
        """Execute the double-Ctrl quick language switch.

        In 'force' mode (force_anjal_english=True): always toggles between
        English India and Tamil Anjal, regardless of other installed layouts.
        In 'dynamic' mode (force_anjal_english=False): toggles between the
        first two layouts in the user's installed keyboard layout list.
        All errors are caught; the app never crashes from a failed switch.
        """
        if sys.platform not in ("win32", "darwin"):
            return
        if not getattr(self, '_quick_switch_enabled', False):
            return
        try:
            if getattr(self, '_force_anjal_english', True):
                # Force mode: toggle between English India (0) and Tamil Anjal (1)
                new_layout = 1 - self._current_layout
                self._toggle_keyboard_layout(new_layout)
            else:
                # Dynamic mode: toggle between the first two installed IMEs
                imes = getattr(self, '_installed_imes', [])
                if len(imes) < 2:
                    # Not enough layouts available — nothing to switch.
                    # (_quick_switch_enabled is always False at this point due to
                    # the startup check in _load_preferences, but guard explicitly
                    # here so no hardcoded Tamil/English layout is ever forced.)
                    return

                klid0, name0 = imes[0]
                klid1, name1 = imes[1]

                # Read the currently active layout identifier (platform-aware)
                current_klid = _get_current_klid()

                # Switch to the other layout in the pair
                if current_klid == _normalize_klid(klid0):
                    target_klid, target_name = klid1, name1
                    self._current_layout = 1
                else:
                    target_klid, target_name = klid0, name0
                    self._current_layout = 0

                try:
                    _activate_klid(target_klid)
                    self.layout_label.setText(f"Keyboard: {target_name}")
                except Exception:
                    self.layout_label.setText("Keyboard: Error")
        except Exception:
            # Safety net: never let a quick-switch failure crash the app
            pass

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
        self._set_line_spacing_preset(getattr(self, '_line_spacing_preset', 'normal'), save=False, show_status=False)
        self.current_path = None
        self.editor.document().setModified(False)
        self._update_title()
        self._update_status_bar()
        self._update_export_menu_visibility()
        self.status.showMessage("New document", 2000)

    def new_window(self):
        try:
            if getattr(sys, "frozen", False):
                cmd = [sys.executable, "--new-window-empty"]
            else:
                cmd = [sys.executable, str(Path(__file__).resolve()), "--new-window-empty"]

            popen_kwargs = {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "close_fds": True,
            }

            if sys.platform == "win32":
                creationflags = 0
                creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
                creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                if creationflags:
                    popen_kwargs["creationflags"] = creationflags
                popen_kwargs["close_fds"] = False
            else:
                popen_kwargs["start_new_session"] = True

            subprocess.Popen(cmd, **popen_kwargs)
            self.status.showMessage("Opened a new Neight window", 2000)
        except Exception as e:
            QMessageBox.critical(self, "New Window Failed", f"Could not open a new window:\n{e}")

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
        self._set_line_spacing_preset(getattr(self, '_line_spacing_preset', 'normal'), save=False, show_status=False)
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
        dialog = self._ensure_find_dialog()
        if self._replace_dialog is not None:
            self._replace_dialog.hide()
        selected = self._get_selected_text()
        if selected:
            dialog.set_find_text(self._encode_special_sequences(selected))
        elif self._last_find_raw:
            dialog.set_find_text(self._last_find_raw)
        dialog.set_default_action("find")
        dialog.show()
        dialog.focus_find_field()

    def find_next(self):
        if not self._last_find:
            selected = self._get_selected_text()
            if selected:
                self._on_find_request(self._encode_special_sequences(selected))
            else:
                self.find_text()
            return
        self._perform_find_with_progress(self._last_find)

    def _find_forward(self, text: str) -> bool:
        if not text:
            return False
        cursor = self.editor.textCursor()
        doc = self.editor.document()
        match = doc.find(text, cursor)
        if match.isNull():
            start = QTextCursor(doc)
            start.movePosition(QTextCursor.Start)
            match = doc.find(text, start)
        if match.isNull():
            return False
        self.editor.setTextCursor(match)
        self.editor.centerCursor()
        return True

    def replace_text(self):
        self._show_replace_dialog(preferred_action="replace")

    def replace_all(self):
        self._show_replace_dialog(preferred_action="replace_all")

    def _ensure_find_dialog(self) -> FindReplaceDialog:
        if self._find_dialog is None:
            self._find_dialog = FindReplaceDialog(self, replace_enabled=False)
            self._find_dialog.find_next.connect(self._on_find_request)
        return self._find_dialog

    def _ensure_replace_dialog(self) -> FindReplaceDialog:
        if self._replace_dialog is None:
            self._replace_dialog = FindReplaceDialog(self, replace_enabled=True)
            self._replace_dialog.find_next.connect(self._on_find_request)
            self._replace_dialog.replace.connect(self._on_replace_request)
            self._replace_dialog.replace_all.connect(self._on_replace_all_request)
        return self._replace_dialog

    def _show_replace_dialog(self, preferred_action: str) -> None:
        dialog = self._ensure_replace_dialog()
        if self._find_dialog is not None:
            self._find_dialog.hide()
        selected = self._get_selected_text()
        if selected:
            dialog.set_find_text(self._encode_special_sequences(selected))
        elif self._last_find_raw:
            dialog.set_find_text(self._last_find_raw)
        if self._last_replace_raw:
            dialog.set_replace_text(self._last_replace_raw)
        dialog.set_default_action(preferred_action)
        if preferred_action == "replace_all":
            dialog.focus_replace_field()
        else:
            dialog.focus_find_field()
        dialog.show()

    def _on_find_request(self, raw_query: str) -> None:
        query = self._decode_special_sequences(raw_query)
        if not query:
            self.status.showMessage("Enter text to find", 2000)
            return
        self._last_find_raw = raw_query
        self._last_find = query
        self._perform_find_with_progress(query, success_message="Match found")

    def _on_replace_request(self, raw_find: str, raw_replace: str) -> None:
        find_text = self._decode_special_sequences(raw_find)
        replace_text = self._decode_special_sequences(raw_replace)
        if not find_text:
            self.status.showMessage("Enter text to find", 2000)
            return
        self._last_find_raw = raw_find
        self._last_find = find_text
        self._last_replace_raw = raw_replace
        self._last_replace = replace_text

        cursor = self.editor.textCursor()
        current_selection = self._normalize_selected_text(cursor.selectedText())
        replaced = False

        if current_selection == find_text:
            cursor.insertText(replace_text)
            self.editor.setTextCursor(cursor)
            replaced = True
        else:
            if not self._perform_find_with_progress(find_text):
                return
            cursor = self.editor.textCursor()
            current_selection = self._normalize_selected_text(cursor.selectedText())
            if current_selection == find_text:
                cursor.insertText(replace_text)
                self.editor.setTextCursor(cursor)
                replaced = True

        if replaced:
            self.status.showMessage("Replaced 1 occurrence", 2000)
            if not self._find_forward(find_text):
                self.status.showMessage("No further matches", 2000)

    def _on_replace_all_request(self, raw_find: str, raw_replace: str) -> None:
        find_text = self._decode_special_sequences(raw_find)
        replace_text = self._decode_special_sequences(raw_replace)
        if not find_text:
            self.status.showMessage("Enter text to find", 2000)
            return
        self._last_find_raw = raw_find
        self._last_find = find_text
        self._last_replace_raw = raw_replace
        self._last_replace = replace_text

        self._show_progress_indicator("Replacing…")
        count = self._replace_all_occurrences(find_text, replace_text)
        if count == 0:
            self._hide_progress_indicator("No matches found", 2000)
        else:
            self._hide_progress_indicator(f"Replaced {count} occurrence(s)", 3000)

    def _perform_find_with_progress(self, text: str, success_message: Optional[str] = None) -> bool:
        if not text:
            return False
        self._show_progress_indicator("Searching…")
        QApplication.processEvents()
        found = self._find_forward(text)
        if found:
            if success_message:
                self._hide_progress_indicator(success_message, 1500)
            else:
                self._hide_progress_indicator()
        else:
            self._hide_progress_indicator("Text not found", 2000)
        return found

    def _replace_all_occurrences(self, find_text: str, replace_text: str) -> int:
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.Start)
        self.editor.setTextCursor(cursor)

        count = 0
        doc = self.editor.document()

        while True:
            match = doc.find(find_text, cursor)
            if match.isNull():
                break
            match.insertText(replace_text)
            cursor = match
            count += 1
            if count % 50 == 0:
                self.status.showMessage(f"Replacing… {count}", 0)
                QApplication.processEvents()

        cursor.endEditBlock()
        return count

    def _show_progress_indicator(self, message: str) -> None:
        self.status.showMessage(message)
        if self._progress_bar is None:
            bar = QProgressBar(self.status)
            bar.setMaximum(0)
            bar.setMinimum(0)
            bar.setTextVisible(False)
            bar.setFixedWidth(100)
            self.status.addPermanentWidget(bar)
            self._progress_bar = bar

    def _hide_progress_indicator(self, message: Optional[str] = None, timeout: int = 0) -> None:
        if self._progress_bar is not None:
            self.status.removeWidget(self._progress_bar)
            self._progress_bar.deleteLater()
            self._progress_bar = None
        if message:
            self.status.showMessage(message, timeout if timeout else 0)
        else:
            self.status.clearMessage()

    def _get_selected_text(self) -> str:
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            return ""
        return self._normalize_selected_text(cursor.selectedText())

    @staticmethod
    def _normalize_selected_text(text: str) -> str:
        if not text:
            return ""
        return text.replace("\u2029", "\n")

    @staticmethod
    def _encode_special_sequences(text: str) -> str:
        if not text:
            return ""
        replacements = (
            ("\\", "\\\\"),
            ("\r", "\\r"),
            ("\n", "\\n"),
            ("\t", "\\t"),
            ("\f", "\\f"),
            ("\v", "\\v"),
        )
        encoded = text
        for src, repl in replacements:
            encoded = encoded.replace(src, repl)
        return encoded

    @staticmethod
    def _decode_special_sequences(text: str) -> str:
        if not text:
            return ""
        pattern = re.compile(r"\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|[nrtfv0\\\\])")

        def replace(match: re.Match) -> str:
            seq = match.group(1)
            mapping = {
                "n": "\n",
                "r": "\r",
                "t": "\t",
                "f": "\f",
                "v": "\v",
                "0": "\0",
                "\\": "\\",
            }
            if seq.startswith("x") and len(seq) == 3:
                try:
                    return chr(int(seq[1:], 16))
                except ValueError:
                    return "\\" + seq
            if seq.startswith("u") and len(seq) == 5:
                try:
                    return chr(int(seq[1:], 16))
                except ValueError:
                    return "\\" + seq
            return mapping.get(seq, "\\" + seq)

        return pattern.sub(replace, text)

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

        replacement = newline * 2
        collapsed = pattern.sub(replacement, text)
        replacement_length = len(replacement)
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

        doc_len = self.editor.document().characterCount()
        # Clamp positions to valid range to avoid Qt "out of range" warnings.
        new_anchor = max(0, min(new_anchor, doc_len))
        new_pos = max(0, min(new_pos, doc_len))

        restored_cursor = self.editor.textCursor()
        restored_cursor.setPosition(new_anchor)
        mode = QTextCursor.KeepAnchor if new_anchor != new_pos else QTextCursor.MoveAnchor
        restored_cursor.setPosition(new_pos, mode)
        self.editor.setTextCursor(restored_cursor)

        blocks_collapsed = len(matches)
        self.status.showMessage(f"Collapsed {blocks_collapsed} blank block(s)", 3000)

    def insert_blank_lines(self):
        text = self.editor.toPlainText()
        if not text:
            self.status.showMessage("Document is empty", 1500)
            return

        newline = "\r\n" if "\r\n" in text else "\n"
        lines = text.splitlines()
        new_lines = []
        lines_added = 0
        for line in lines:
            new_lines.append(line)
            if line.strip():  # non-blank line — insert a blank line after it
                new_lines.append("")
                lines_added += 1

        if lines_added == 0:
            self.status.showMessage("No full lines found to add blank lines after", 2000)
            return

        result = newline.join(new_lines)
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.insertText(result)
        cursor.endEditBlock()
        self.status.showMessage(f"Inserted {lines_added} blank line(s)", 3000)

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

    def _create_url_validate_fn(self, url_input, status_label, validated_url, insert_btn):
        """Return a validate() closure shared by the image and hyperlink dialogs."""
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
        return validate

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
        validate = self._create_url_validate_fn(url_input, status_label, validated_url, insert_btn)
        
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
                    validated_url[0] = url if url.startswith(("http://", "https://")) else ("https://" + url)
            
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
        validate = self._create_url_validate_fn(url_input, status_label, validated_url, insert_btn)
        
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
        
        if not HAS_PRINT_SUPPORT:
            QMessageBox.critical(self, "Export Failed",
                                 "PDF export requires QtPrintSupport, which is not available.")
            return
        
        try:
            # Create printer
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(save_path)
            printer.setPageSize(QPageSize(QPageSize.A4))
            # Set margins: left, top, right, bottom in millimeters
            margins = QMarginsF(15, 20, 15, 20)
            printer.setPageMargins(margins, _MARGIN_UNIT_MM)
            
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
            self._show_export_success_dialog("Text file", save_path)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Could not export to PDF:\n{str(e)}"
            )

    def _show_export_success_dialog(self, export_label: str, save_path: str, note: str = ""):
        """Show export success dialog with quick path actions."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Export Successful")
        dialog.setMinimumWidth(560)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"{export_label} exported to:"))

        path_row = QHBoxLayout()
        path_edit = QLineEdit(save_path)
        path_edit.setReadOnly(True)
        path_edit.setCursorPosition(0)
        path_row.addWidget(path_edit)

        copy_btn = QPushButton()
        copy_icon = QIcon.fromTheme("edit-copy")
        if copy_icon.isNull():
            copy_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        else:
            copy_btn.setIcon(copy_icon)
        copy_btn.setToolTip("Copy path")
        copy_btn.setFixedWidth(34)

        open_btn = QPushButton()
        open_icon = QIcon.fromTheme("document-open")
        if open_icon.isNull():
            open_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        else:
            open_btn.setIcon(open_icon)
        open_btn.setToolTip("Open exported PDF")
        open_btn.setFixedWidth(34)

        path_row.addWidget(copy_btn)
        path_row.addWidget(open_btn)
        layout.addLayout(path_row)

        if note:
            note_label = QLabel(note)
            note_label.setWordWrap(True)
            layout.addWidget(note_label)

        button_box = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        layout.addWidget(button_box)

        def copy_path_to_clipboard():
            QApplication.clipboard().setText(save_path)
            self.status.showMessage("Export path copied to clipboard", 2500)

        def open_exported_pdf():
            file_url = QUrl.fromLocalFile(str(Path(save_path).resolve()))
            if not QDesktopServices.openUrl(file_url):
                QMessageBox.warning(dialog, "Open Failed", f"Could not open:\n{save_path}")

        copy_btn.clicked.connect(copy_path_to_clipboard)
        open_btn.clicked.connect(open_exported_pdf)
        button_box.rejected.connect(dialog.reject)

        dialog.exec()

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
            
            if not HAS_PRINT_SUPPORT:
                QMessageBox.critical(self, "Export Failed",
                                     "PDF export requires QtPrintSupport, which is not available.")
                return
            
            # Create printer
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(save_path)
            printer.setPageSize(QPageSize(QPageSize.A4))
            # Set margins: left, top, right, bottom in millimeters
            margins = QMarginsF(15, 20, 15, 20)
            printer.setPageMargins(margins, _MARGIN_UNIT_MM)
            
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
            
            msg = ""
            if not has_markdown:
                msg = "Note: For better markdown rendering, install the 'markdown' package:\npip install markdown"

            self._show_export_success_dialog("Markdown file", save_path, msg)
            
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
            f"""
            <b>Neight v{VERSION}</b> (Using {QT_LIB})<br>
            A lightweight UTF-8 text editor with advanced features, word count, line numbers and more.<br>
            Generated by Github Copilot for venkatarangan.com.<br><br>
            <span style='color:#666;'>Provided AS IS. No warranty of performance, accuracy, or fitness for a particular purpose.</span><br>
            <span style='color:#666;'>Full details: <a href='https://github.com/venkatarangan/neight/blob/main/README.md'>README</a> | <a href='https://github.com/venkatarangan/neight/blob/main/PRIVACY.md'>Privacy</a></span>
            """
        )

    def _show_debug_info(self):
        """Show a dialog with diagnostic information useful for bug reports."""
        lines = []

        # Neight version
        try:
            lines.append(f"Neight Version      : {VERSION}")
        except Exception:
            lines.append("Neight Version      : N/A")

        # OS version (Windows, macOS, or generic)
        try:
            if sys.platform == "win32":
                release, ver, csd, ptype = platform.win32_ver()
                lines.append(f"Windows Version     : {release}  (Build {ver})")
            elif sys.platform == "darwin":
                release, versioninfo, machine = platform.mac_ver()
                lines.append(f"macOS Version       : {release}  ({machine})")
            else:
                lines.append(f"OS Version          : {platform.platform()}")
        except Exception:
            try:
                lines.append(f"OS Version          : {platform.platform()}")
            except Exception:
                lines.append("OS Version          : N/A")

        # Screen resolution
        try:
            screen = QGuiApplication.primaryScreen()
            sz = screen.size()
            dpr = screen.devicePixelRatio()
            lines.append(f"Screen Resolution   : {sz.width()} x {sz.height()} px  (DPR {dpr:.1f})")
        except Exception:
            lines.append("Screen Resolution   : N/A")

        # Python version
        try:
            lines.append(f"Python Version      : {sys.version}")
        except Exception:
            lines.append("Python Version      : N/A")

        # Qt / binding version
        try:
            import PySide6.QtCore as _qtcore
            import PySide6 as _ps6
            lines.append(f"Qt Runtime          : PySide6 {_ps6.__version__}  (Qt {_qtcore.qVersion()})")
        except Exception:
            lines.append("Qt Runtime          : PySide6 (version unavailable)")

        # Installed keyboard layouts / IMEs
        lines.append("")
        lines.append("Installed Keyboard Layouts / IMEs:")
        try:
            ime_list = get_installed_ime_list()
            if ime_list:
                for klid, name in ime_list:
                    lines.append(f"  [{klid}]  {name}")
            else:
                lines.append("  (none found)")
        except Exception:
            lines.append("  N/A")

        text = "\n".join(lines)

        dialog = QDialog(self)
        dialog.setWindowTitle("Debug Info")
        dialog.setMinimumSize(560, 420)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)

        layout = QVBoxLayout(dialog)

        intro = QLabel(
            "The information below describes your system environment. "
            "You can copy and paste it when reporting issues or bugs.",
            dialog
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        text_box = QTextEdit(dialog)
        text_box.setReadOnly(True)
        text_box.setPlainText(text)
        text_box.setFont(QFont("Consolas", 9))
        layout.addWidget(text_box)

        btn_box = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        dialog.exec()

    def _show_keyboards_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Language Switch")
        dialog.setMinimumWidth(520)

        outer = QVBoxLayout(dialog)
        outer.setSpacing(10)
        outer.setContentsMargins(16, 16, 16, 16)

        def _hint(text: str) -> QLabel:
            lbl = QLabel(text, dialog)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: gray; margin-left: 20px; margin-bottom: 2px;")
            return lbl

        def _separator() -> QWidget:
            line = QWidget(dialog)
            line.setFixedHeight(1)
            line.setStyleSheet("background: #aaaaaa;")
            return line

        _ctrl_name = "\u2303 Control" if sys.platform == "darwin" else "Ctrl"
        # ── Intro ──────────────────────────────────────────────────────────
        intro = QLabel(
            "<b>Switch between two keyboard languages instantly</b><br><br>"
            "If you write in more than one language \u2014 for example, mixing Tamil and English \u2014 "
            f"you can press the <b>{_ctrl_name} key twice in quick succession</b> to toggle your keyboard "
            "layout without leaving the editor. No need to open System Settings or click the menu bar.",
            dialog
        )
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.RichText)
        outer.addWidget(intro)
        outer.addWidget(_separator())

        installed_imes = getattr(self, '_installed_imes', [])
        ime_count = len(installed_imes)

        try:
            saved = self.settings.load()
        except Exception:
            saved = {}
        saved_qs = bool(saved.get("quick_switch_enabled", True))
        saved_force = bool(saved.get("force_anjal_english", True))

        # ── Master toggle ─────────────────────────────────────────────────
        quick_switch_cb = QCheckBox("Enable double-Ctrl language switch", dialog)
        quick_switch_cb.setChecked(saved_qs)
        outer.addWidget(quick_switch_cb)
        qs_hint_lbl = _hint(f"Tap {_ctrl_name} twice quickly to cycle between two keyboard layouts.")
        outer.addWidget(qs_hint_lbl)

        if ime_count < 2:
            quick_switch_cb.setChecked(False)
            quick_switch_cb.setEnabled(False)
            unavail_label = QLabel(
                "\u26a0  Only one keyboard layout is installed on this system. "
                "Add a second layout in System Settings \u2192 Keyboard to enable this feature.",
                dialog
            )
            unavail_label.setWordWrap(True)
            unavail_label.setStyleSheet("color: #b05010; margin-left: 20px;")
            outer.addWidget(unavail_label)

        # ── >2 IMEs warning ───────────────────────────────────────────────
        info_label = QLabel(dialog)
        info_label.setWordWrap(True)
        if ime_count > 2 and len(installed_imes) >= 2:
            first_name = installed_imes[0][1]
            second_name = installed_imes[1][1]
            if TAMIL_CHOICE and ENGLISH_CHOICE:
                pair_desc = f"\u201c{TAMIL_CHOICE_NAME}\u201d and \u201c{ENGLISH_CHOICE_NAME}\u201d"
                force_hint = f"To always switch between the detected Tamil and English keyboards ({pair_desc}) instead, enable the option below."
            else:
                force_hint = "No Tamil/English keyboard pair could be auto-detected on this system."
            info_label.setText(
                f"\u26a0\u202f You have more than two keyboard layouts installed. "
                f"The quick switch will toggle between the first two in your system list \u2014 "
                f"currently \u201c{first_name}\u201d and \u201c{second_name}\u201d. "
                f"{force_hint}"
            )
            info_label.setStyleSheet(
                "color: #8B6914; background: #FFF8DC; "
                "border: 1px solid #DEB887; border-radius: 4px; "
                "padding: 6px; margin-left: 20px;"
            )
        outer.addWidget(info_label)

        # ── Force Tamil/English pair ───────────────────────────────────────
        if TAMIL_CHOICE and ENGLISH_CHOICE:
            force_label = (
                f"Always switch between {TAMIL_CHOICE_NAME} and {ENGLISH_CHOICE_NAME} "
                f"(auto-detected Tamil \u2194 English pair)"
            )
            force_cb_enabled = True
        else:
            missing = "Tamil" if not TAMIL_CHOICE else "English"
            force_label = (
                f"Always switch between auto-detected Tamil and English keyboards "
                f"(no {missing} keyboard detected \u2014 option unavailable)"
            )
            force_cb_enabled = False

        force_cb = QCheckBox(force_label, dialog)
        force_cb.setChecked(saved_force and force_cb_enabled)
        if not force_cb_enabled:
            force_cb.setEnabled(False)
        outer.addWidget(force_cb)
        force_hint_lbl = _hint(
            "Useful when you have other layouts installed alongside Tamil and English. "
            "This keeps the switch always between Tamil and English, ignoring everything else."
        )
        outer.addWidget(force_hint_lbl)

        # ── Dynamic visibility ────────────────────────────────────────────
        def _refresh_visibility():
            enabled = quick_switch_cb.isEnabled() and quick_switch_cb.isChecked()
            info_label.setVisible(enabled and ime_count > 2)
            force_cb.setVisible(enabled)
            force_hint_lbl.setVisible(enabled)
            force_cb.setEnabled(enabled and force_cb_enabled)

        quick_switch_cb.toggled.connect(lambda _checked: _refresh_visibility())
        _refresh_visibility()

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        outer.addWidget(btn_box)

        if dialog.exec():
            new_qs = bool(quick_switch_cb.isChecked() and quick_switch_cb.isEnabled())
            new_force = bool(force_cb.isChecked())

            self._quick_switch_enabled = new_qs
            self._force_anjal_english = new_force

            if not new_qs:
                self._ctrl_press_time = 0
                try:
                    self._ctrl_press_timer.stop()
                except Exception:
                    pass

            try:
                data = self.settings.load()
                data["quick_switch_enabled"] = new_qs
                data["force_anjal_english"] = new_force
                self.settings.save(data)
            except Exception:
                pass

    def _show_reading_time_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Reading Time")
        dialog.setMinimumWidth(560)

        outer = QVBoxLayout(dialog)
        outer.setSpacing(10)

        enabled_cb = QCheckBox("Enable reading time estimate in the status bar", dialog)
        enabled_cb.setChecked(bool(getattr(self, "_reading_time_enabled", False)))
        outer.addWidget(enabled_cb)

        tamil_row = QHBoxLayout()
        tamil_label = QLabel("Tamil Reading Speed:", dialog)
        tamil_combo = QComboBox(dialog)
        for value in range(50, 401, 50):
            tamil_combo.addItem(f"{value} words per minute", value)
        tamil_value = self._normalize_reading_speed(getattr(self, "_tamil_reading_wpm", 150), 150)
        tamil_combo.setCurrentText(f"{tamil_value} words per minute")
        tamil_row.addWidget(tamil_label)
        tamil_row.addWidget(tamil_combo)
        outer.addLayout(tamil_row)

        english_row = QHBoxLayout()
        english_label = QLabel("English Reading Speed:", dialog)
        english_combo = QComboBox(dialog)
        for value in range(50, 401, 50):
            english_combo.addItem(f"{value} words per minute", value)
        english_value = self._normalize_reading_speed(getattr(self, "_english_reading_wpm", 250), 250)
        english_combo.setCurrentText(f"{english_value} words per minute")
        english_row.addWidget(english_label)
        english_row.addWidget(english_combo)
        outer.addLayout(english_row)

        explanation = QLabel(
            "How this is calculated: Each word is classified as Tamil, English, or Other. "
            "We then compute weighted reading time using T = (W_t / R_t) + (W_e / R_e) + (W_o / R_o), "
            "where W = word counts and R = reading speeds in words per minute. "
            "For Other words, R_o is fixed at 180 wpm. This handles mixed Tamil-English text naturally.",
            dialog,
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: gray;")
        outer.addWidget(explanation)

        def _refresh_enabled_state():
            enabled = enabled_cb.isChecked()
            tamil_label.setVisible(enabled)
            tamil_combo.setVisible(enabled)
            english_label.setVisible(enabled)
            english_combo.setVisible(enabled)
            tamil_label.setEnabled(enabled)
            tamil_combo.setEnabled(enabled)
            english_label.setEnabled(enabled)
            english_combo.setEnabled(enabled)

        enabled_cb.toggled.connect(lambda _checked: _refresh_enabled_state())
        _refresh_enabled_state()

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        outer.addWidget(btn_box)

        if dialog.exec():
            self._reading_time_enabled = bool(enabled_cb.isChecked())
            self._tamil_reading_wpm = self._normalize_reading_speed(tamil_combo.currentData(), 150)
            self._english_reading_wpm = self._normalize_reading_speed(english_combo.currentData(), 250)
            self._save_preferences()
            self._update_status_bar()

    def _show_appearance_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Appearance")
        dialog.setMinimumWidth(520)

        outer = QVBoxLayout(dialog)
        outer.setSpacing(8)
        outer.setContentsMargins(16, 16, 16, 16)

        def _separator() -> QWidget:
            line = QWidget(dialog)
            line.setFixedHeight(1)
            line.setStyleSheet("background: #aaaaaa;")
            return line

        def _info_btn(hint_text: str) -> QPushButton:
            btn = QPushButton("\u24d8", dialog)
            btn.setFixedSize(22, 22)
            btn.setFlat(True)
            btn.setStyleSheet("color: #0078d4; font-size: 14px; padding: 0; border: none;")
            btn.setToolTip(hint_text)
            btn.clicked.connect(lambda: QToolTip.showText(
                btn.mapToGlobal(QPoint(0, btn.height())), hint_text, btn
            ))
            return btn

        # ── THEME ─────────────────────────────────────────────────────────
        theme_header_row = QHBoxLayout()
        theme_hdr = QLabel("Theme", dialog)
        theme_hdr.setStyleSheet("font-weight: 600; margin-top: 4px;")
        theme_header_row.addWidget(theme_hdr)
        theme_header_row.addStretch(1)
        reset_theme_btn = QPushButton("Reset to defaults", dialog)
        reset_theme_btn.setFixedWidth(130)
        theme_header_row.addWidget(reset_theme_btn)
        outer.addLayout(theme_header_row)

        _mode_hint = (
            "Follow OS adapts automatically to your system Light or Dark mode.\n"
            "Force modes lock the editor regardless of system settings.\n"
            "Custom Colors lets you pick exact background and text colors."
        )
        mode_row = QHBoxLayout()
        mode_label = QLabel("Color mode:", dialog)
        mode_combo = QComboBox(dialog)
        mode_combo.addItem("Follow OS", "follow_os")
        mode_combo.addItem("Force Dark", "dark")
        mode_combo.addItem("Force Light", "light")
        mode_combo.addItem("Custom Colors", "custom")
        current_mode = self._normalize_theme_mode(getattr(self, "_appearance_theme_mode", "follow_os"))
        mode_index = mode_combo.findData(current_mode)
        mode_combo.setCurrentIndex(mode_index if mode_index >= 0 else 0)
        mode_combo.setToolTip(_mode_hint)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(mode_combo)
        mode_row.addWidget(_info_btn(_mode_hint))
        outer.addLayout(mode_row)

        chosen_bg = self._normalize_hex_color(getattr(self, "_appearance_custom_bg", "#202124"), "#202124")
        chosen_fg = self._normalize_hex_color(getattr(self, "_appearance_custom_fg", "#f1f3f4"), "#f1f3f4")

        def _refresh_color_preview(preview: QLabel, hex_color: str):
            text_color = "#000000" if QColor(hex_color).lightness() > 140 else "#ffffff"
            preview.setText(hex_color.upper())
            preview.setStyleSheet(
                f"background: {hex_color}; color: {text_color}; border: 1px solid #888; padding: 2px;"
            )

        def _pick_color(current_hex: str) -> Optional[str]:
            selected = QColorDialog.getColor(QColor(current_hex), dialog, "Choose Color")
            if not selected.isValid():
                return None
            return selected.name(QColor.HexRgb)

        _bg_hint = "The writing area color behind your text. Only applies in Custom Colors mode."
        _fg_hint = "The color of the text you type. Only applies in Custom Colors mode."
        custom_grid = QGridLayout()
        bg_label = QLabel("Background color:", dialog)
        fg_label = QLabel("Text color:", dialog)
        bg_button = QPushButton("Choose\u2026", dialog)
        fg_button = QPushButton("Choose\u2026", dialog)
        bg_preview = QLabel(dialog)
        fg_preview = QLabel(dialog)
        bg_info = _info_btn(_bg_hint)
        fg_info = _info_btn(_fg_hint)
        bg_button.setToolTip(_bg_hint)
        fg_button.setToolTip(_fg_hint)
        for preview in (bg_preview, fg_preview):
            preview.setFixedWidth(78)
            preview.setAlignment(Qt.AlignCenter)

        def _pick_background():
            nonlocal chosen_bg
            selected = _pick_color(chosen_bg)
            if selected:
                chosen_bg = selected
                _refresh_color_preview(bg_preview, chosen_bg)

        def _pick_foreground():
            nonlocal chosen_fg
            selected = _pick_color(chosen_fg)
            if selected:
                chosen_fg = selected
                _refresh_color_preview(fg_preview, chosen_fg)

        bg_button.clicked.connect(_pick_background)
        fg_button.clicked.connect(_pick_foreground)
        _refresh_color_preview(bg_preview, chosen_bg)
        _refresh_color_preview(fg_preview, chosen_fg)

        custom_grid.addWidget(bg_label, 0, 0)
        custom_grid.addWidget(bg_button, 0, 1)
        custom_grid.addWidget(bg_preview, 0, 2)
        custom_grid.addWidget(bg_info, 0, 3)
        custom_grid.addWidget(fg_label, 1, 0)
        custom_grid.addWidget(fg_button, 1, 1)
        custom_grid.addWidget(fg_preview, 1, 2)
        custom_grid.addWidget(fg_info, 1, 3)
        outer.addLayout(custom_grid)

        outer.addWidget(_separator())

        # ── WORD INDEX OVERLAY ────────────────────────────────────────────
        overlay_header_row = QHBoxLayout()
        overlay_hdr = QLabel("Word Index Overlay", dialog)
        overlay_hdr.setStyleSheet("font-weight: 600; margin-top: 4px;")
        overlay_header_row.addWidget(overlay_hdr)
        overlay_header_row.addStretch(1)
        reset_overlay_btn = QPushButton("Reset to defaults", dialog)
        reset_overlay_btn.setFixedWidth(130)
        overlay_header_row.addWidget(reset_overlay_btn)
        outer.addLayout(overlay_header_row)

        _density_hint = (
            "When many words are on screen at once, numbers scale down slightly to avoid crowding.\n"
            "Turn off to keep numbers at a fixed size at all times."
        )
        density_row = QHBoxLayout()
        overlay_density_cb = QCheckBox("Shrink numbers when many words are visible", dialog)
        overlay_density_cb.setChecked(bool(getattr(self, "_word_index_adaptive_density", True)))
        overlay_density_cb.setToolTip(_density_hint)
        density_row.addWidget(overlay_density_cb)
        density_row.addWidget(_info_btn(_density_hint))
        density_row.addStretch(1)
        outer.addLayout(density_row)

        _color_hint = "Color of the word number labels. Pick one that stands out against your current theme."
        overlay_color_row = QHBoxLayout()
        overlay_color_label = QLabel("Number color:", dialog)
        overlay_color_combo = QComboBox(dialog)
        for value in ("white", "grey", "black", "yellow", "green", "blue"):
            overlay_color_combo.addItem(value.capitalize(), value)
        current_overlay_color = self._normalize_word_index_color(getattr(self, "_word_index_color", "white"))
        color_index = overlay_color_combo.findData(current_overlay_color)
        overlay_color_combo.setCurrentIndex(color_index if color_index >= 0 else 0)
        overlay_color_combo.setToolTip(_color_hint)
        overlay_color_row.addWidget(overlay_color_label)
        overlay_color_row.addWidget(overlay_color_combo)
        overlay_color_row.addWidget(_info_btn(_color_hint))
        outer.addLayout(overlay_color_row)

        _align_hint = "Where each number appears relative to its word."
        overlay_align_row = QHBoxLayout()
        overlay_align_label = QLabel("Number position:", dialog)
        overlay_align_combo = QComboBox(dialog)
        overlay_align_combo.addItem("Left of word", "left")
        overlay_align_combo.addItem("Centered above word", "center")
        overlay_align_combo.addItem("Right of word", "right")
        current_alignment = self._normalize_word_index_alignment(
            getattr(self, "_word_index_alignment", "right")
        )
        align_index = overlay_align_combo.findData(current_alignment)
        overlay_align_combo.setCurrentIndex(align_index if align_index >= 0 else 1)
        overlay_align_combo.setToolTip(_align_hint)
        overlay_align_row.addWidget(overlay_align_label)
        overlay_align_row.addWidget(overlay_align_combo)
        overlay_align_row.addWidget(_info_btn(_align_hint))
        outer.addLayout(overlay_align_row)

        _top_margin_hint = "Leaves this many pixels at the top of the editor uncovered, so the first line stays clean."
        overlay_top_margin_row = QHBoxLayout()
        overlay_top_margin_label = QLabel("Clear space at top (px):", dialog)
        overlay_top_margin_spin = QSpinBox(dialog)
        overlay_top_margin_spin.setRange(0, 60)
        overlay_top_margin_spin.setValue(max(0, min(60, int(getattr(self, "_word_index_top_margin", 20)))))
        overlay_top_margin_spin.setToolTip(_top_margin_hint)
        overlay_top_margin_row.addWidget(overlay_top_margin_label)
        overlay_top_margin_row.addWidget(overlay_top_margin_spin)
        overlay_top_margin_row.addWidget(_info_btn(_top_margin_hint))
        outer.addLayout(overlay_top_margin_row)

        opacity_section_lbl = QLabel("Opacity fine-tuning  (0 = invisible  \u00b7  255 = fully solid)", dialog)
        opacity_section_lbl.setStyleSheet("font-weight: 500; margin-top: 6px;")
        outer.addWidget(opacity_section_lbl)

        def _make_spin(value: int) -> QSpinBox:
            spin = QSpinBox(dialog)
            spin.setRange(0, 255)
            spin.setValue(value)
            return spin

        overlay_grid = QGridLayout()
        _bd_dark_hint = "A faint semi-transparent wash over the writing area that makes numbers easier to read (dark theme)."
        backdrop_dark_spin = _make_spin(self._normalize_opacity(getattr(self, "_word_index_backdrop_opacity_dark", 72), 72))
        backdrop_dark_spin.setToolTip(_bd_dark_hint)
        overlay_grid.addWidget(QLabel("Backdrop \u2014 dark background:", dialog), 0, 0)
        overlay_grid.addWidget(backdrop_dark_spin, 0, 1)
        overlay_grid.addWidget(_info_btn(_bd_dark_hint), 0, 2)
        _bd_light_hint = "Same backdrop wash, for light theme."
        backdrop_light_spin = _make_spin(self._normalize_opacity(getattr(self, "_word_index_backdrop_opacity_light", 64), 64))
        backdrop_light_spin.setToolTip(_bd_light_hint)
        overlay_grid.addWidget(QLabel("Backdrop \u2014 light background:", dialog), 1, 0)
        overlay_grid.addWidget(backdrop_light_spin, 1, 1)
        overlay_grid.addWidget(_info_btn(_bd_light_hint), 1, 2)
        _text_hint = "How opaque the word numbers themselves are."
        text_spin = _make_spin(self._normalize_opacity(getattr(self, "_word_index_text_opacity", 255), 255))
        text_spin.setToolTip(_text_hint)
        overlay_grid.addWidget(QLabel("Number text:", dialog), 2, 0)
        overlay_grid.addWidget(text_spin, 2, 1)
        overlay_grid.addWidget(_info_btn(_text_hint), 2, 2)
        _halo_dark_hint = "A soft contrasting aura around each number so it stays legible against any text beneath it (dark theme)."
        halo_dark_spin = _make_spin(self._normalize_opacity(getattr(self, "_word_index_halo_opacity_dark", 220), 220))
        halo_dark_spin.setToolTip(_halo_dark_hint)
        overlay_grid.addWidget(QLabel("Glow \u2014 dark background:", dialog), 3, 0)
        overlay_grid.addWidget(halo_dark_spin, 3, 1)
        overlay_grid.addWidget(_info_btn(_halo_dark_hint), 3, 2)
        _halo_light_hint = "Same glow, for light theme."
        halo_light_spin = _make_spin(self._normalize_opacity(getattr(self, "_word_index_halo_opacity_light", 230), 230))
        halo_light_spin.setToolTip(_halo_light_hint)
        overlay_grid.addWidget(QLabel("Glow \u2014 light background:", dialog), 4, 0)
        overlay_grid.addWidget(halo_light_spin, 4, 1)
        overlay_grid.addWidget(_info_btn(_halo_light_hint), 4, 2)
        outer.addLayout(overlay_grid)

        def _apply_overlay_preset_for_selected_color():
            preset = self._word_index_visual_preset_for_color(overlay_color_combo.currentData())
            backdrop_dark_spin.setValue(preset["backdrop_dark"])
            backdrop_light_spin.setValue(preset["backdrop_light"])
            text_spin.setValue(preset["text"])
            halo_dark_spin.setValue(preset["halo_dark"])
            halo_light_spin.setValue(preset["halo_light"])

        def _refresh_custom_controls():
            is_custom = mode_combo.currentData() == "custom"
            for widget in (bg_label, fg_label, bg_button, fg_button, bg_preview, fg_preview,
                           bg_info, fg_info):
                widget.setVisible(is_custom)

        def _reset_theme_section():
            nonlocal chosen_bg, chosen_fg
            default_mode = "follow_os"
            mode_idx = mode_combo.findData(default_mode)
            if mode_idx >= 0:
                mode_combo.setCurrentIndex(mode_idx)
            chosen_bg = "#202124"
            chosen_fg = "#f1f3f4"
            _refresh_color_preview(bg_preview, chosen_bg)
            _refresh_color_preview(fg_preview, chosen_fg)
            _refresh_custom_controls()

        def _reset_overlay_section():
            overlay_density_cb.setChecked(True)
            overlay_top_margin_spin.setValue(20)
            default_color = "white"
            color_idx = overlay_color_combo.findData(default_color)
            if color_idx >= 0:
                overlay_color_combo.setCurrentIndex(color_idx)
            default_align = "right"
            align_idx = overlay_align_combo.findData(default_align)
            if align_idx >= 0:
                overlay_align_combo.setCurrentIndex(align_idx)
            _apply_overlay_preset_for_selected_color()

        reset_theme_btn.clicked.connect(_reset_theme_section)
        reset_overlay_btn.clicked.connect(_reset_overlay_section)
        overlay_color_combo.currentIndexChanged.connect(lambda _idx: _apply_overlay_preset_for_selected_color())

        mode_combo.currentIndexChanged.connect(lambda _idx: _refresh_custom_controls())
        _refresh_custom_controls()

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        outer.addWidget(btn_box)

        if dialog.exec():
            self._appearance_theme_mode = self._normalize_theme_mode(mode_combo.currentData())
            self._appearance_custom_bg = self._normalize_hex_color(chosen_bg, "#202124")
            self._appearance_custom_fg = self._normalize_hex_color(chosen_fg, "#f1f3f4")

            self._word_index_adaptive_density = bool(overlay_density_cb.isChecked())
            self._word_index_color = self._normalize_word_index_color(overlay_color_combo.currentData())
            self._word_index_alignment = self._normalize_word_index_alignment(overlay_align_combo.currentData())
            self._word_index_top_margin = max(0, min(60, int(overlay_top_margin_spin.value())))
            self._word_index_backdrop_opacity_dark = self._normalize_opacity(backdrop_dark_spin.value(), 72)
            self._word_index_backdrop_opacity_light = self._normalize_opacity(backdrop_light_spin.value(), 64)
            self._word_index_text_opacity = self._normalize_opacity(text_spin.value(), 255)
            self._word_index_halo_opacity_dark = self._normalize_opacity(halo_dark_spin.value(), 220)
            self._word_index_halo_opacity_light = self._normalize_opacity(halo_light_spin.value(), 230)

            self._apply_theme_preferences()
            self._apply_word_index_preferences()
            self._save_preferences()

    def _is_os_dark_mode(self) -> bool:
        app = QApplication.instance()
        if app is None:
            return False
        return app.palette().window().color().lightness() < 128

    def _apply_theme_preferences(self):
        mode = self._normalize_theme_mode(getattr(self, "_appearance_theme_mode", "follow_os"))
        if mode == "follow_os":
            mode = "dark" if self._is_os_dark_mode() else "light"

        app = QApplication.instance()
        if app is None:
            return

        if mode == "dark":
            bg = QColor("#1e1f22")
            fg = QColor("#f1f3f4")
        elif mode == "light":
            bg = QColor("#ffffff")
            fg = QColor("#1f1f1f")
        else:
            bg = QColor(self._normalize_hex_color(getattr(self, "_appearance_custom_bg", "#202124"), "#202124"))
            fg = QColor(self._normalize_hex_color(getattr(self, "_appearance_custom_fg", "#f1f3f4"), "#f1f3f4"))

        palette = app.palette()

        # Qt6 (PySide6) uses scoped enums: QPalette.ColorRole.Window, etc.
        # Qt5 also exposes flat aliases, so support both forms safely.
        color_role_enum = getattr(type(palette), "ColorRole", None)

        def _role(name: str):
            if color_role_enum is not None and hasattr(color_role_enum, name):
                return getattr(color_role_enum, name)
            return getattr(type(palette), name)

        palette.setColor(_role("Window"), bg)
        palette.setColor(_role("Base"), bg)
        if bg.lightness() < 128:
            alt_base = bg.lighter(118)
        else:
            alt_base = bg.darker(104)
        palette.setColor(_role("AlternateBase"), alt_base)
        palette.setColor(_role("Text"), fg)
        palette.setColor(_role("WindowText"), fg)
        palette.setColor(_role("ButtonText"), fg)
        app.setPalette(palette)
        self.editor.viewport().update()
        self.editor.lineNumberArea.update()

    def _apply_word_index_preferences(self):
        self.editor.setWordIndexVisualOpacities(
            self._word_index_backdrop_opacity_dark,
            self._word_index_backdrop_opacity_light,
            self._word_index_text_opacity,
            self._word_index_halo_opacity_dark,
            self._word_index_halo_opacity_light,
        )
        self.editor.setWordIndexColorName(self._word_index_color)
        self.editor.setWordIndexAlignmentName(self._word_index_alignment)
        self.editor.setWordIndexAdaptiveDensity(self._word_index_adaptive_density)
        self.editor.setWordIndexTopMargin(self._word_index_top_margin)

    # --- Preferences ---
    def _load_preferences(self):
        data = self.settings.load()

        if self.settings.corrupted_settings_path is not None:
            bad_path = str(self.settings.corrupted_settings_path)
            prompt = QMessageBox(self)
            prompt.setIcon(QMessageBox.Warning)
            prompt.setWindowTitle("Corrupted Settings")
            prompt.setText(
                "The settings file below is corrupted.\n\n"
                f"{bad_path}\n\n"
                "Do you want to reset settings to defaults, or exit and fix the file manually?"
            )
            reset_btn = prompt.addButton("Reset to Defaults", QMessageBox.AcceptRole)
            exit_btn = prompt.addButton("Exit", QMessageBox.RejectRole)
            copy_btn = prompt.addButton("Copy Path", QMessageBox.ActionRole)
            copy_icon = QIcon.fromTheme("edit-copy")
            if copy_icon.isNull():
                copy_icon = self.style().standardIcon(QStyle.SP_FileDialogDetailedView)
            copy_btn.setIcon(copy_icon)
            prompt.setDefaultButton(reset_btn)
            while True:
                prompt.exec()
                clicked = prompt.clickedButton()
                if clicked == copy_btn:
                    clipboard = QApplication.clipboard()
                    if clipboard is not None:
                        clipboard.setText(bad_path)
                    self.status.showMessage("Settings path copied to clipboard", 2500)
                    continue
                if clicked == exit_btn:
                    return False
                break

            try:
                self.settings.save({})
                self.settings.corrupted_settings_path = None
                self.settings.corrupted_settings_reason = ""
                data = self.settings.load()
                self.status.showMessage("Settings reset to defaults", 2500)
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Reset Failed",
                    "Could not reset settings. Please fix or remove the settings file manually.\n\n"
                    f"{bad_path}\n\n"
                    f"Error: {exc}",
                )
                return False

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

        # Line numbers
        line_numbers_visible = data.get("line_numbers_visible", True)
        self.line_numbers_act.setChecked(bool(line_numbers_visible))
        self.editor.setLineNumbersVisible(bool(line_numbers_visible))

        # Status bar item visibility
        self._status_show_words = bool(data.get("status_show_words", True))
        self._status_show_sentences = bool(data.get("status_show_sentences", True))
        self._status_show_chars = bool(data.get("status_show_chars", True))
        self._status_show_line = bool(data.get("status_show_line", True))
        self._status_show_col = bool(data.get("status_show_col", True))
        self.status_words_act.setChecked(self._status_show_words)
        self.status_sentences_act.setChecked(self._status_show_sentences)
        self.status_chars_act.setChecked(self._status_show_chars)
        self.status_line_act.setChecked(self._status_show_line)
        self.status_col_act.setChecked(self._status_show_col)
        self.words_label.setVisible(self._status_show_words)
        self.sentences_label.setVisible(self._status_show_sentences)
        self.chars_label.setVisible(self._status_show_chars)
        self.line_label.setVisible(self._status_show_line)
        self.col_label.setVisible(self._status_show_col)

        # Text margins
        margin_percent = data.get("text_margin_percent", 0)
        self._set_text_margin_percent(margin_percent, save=False, show_status=False)

        line_spacing_preset = data.get("line_spacing_preset", "normal")
        self._set_line_spacing_preset(line_spacing_preset, save=False, show_status=False)

        # Font
        family = data.get("font_family")
        size = data.get("font_size")
        if family and isinstance(size, int) and size > 0:
            try:
                font = QFont(family, size)
                self.editor.setFont(font)
            except Exception:
                pass

        # Keyboard quick switch settings
        try:
            self._installed_imes = get_installed_ime_list()
        except Exception:
            self._installed_imes = []
        # Detect first Tamil and first English from installed layouts
        _init_keyboard_choices(self._installed_imes)
        ime_count = len(self._installed_imes)
        # If fewer than two layouts are installed, quick switch is impossible
        if ime_count < 2:
            self._quick_switch_enabled = False
        else:
            self._quick_switch_enabled = bool(data.get("quick_switch_enabled", True))
        self._force_anjal_english = bool(data.get("force_anjal_english", True))

        # Appearance
        raw_theme_mode = data.get("appearance_theme_mode", "follow_os")
        raw_custom_bg = data.get("appearance_custom_bg", "#202124")
        raw_custom_fg = data.get("appearance_custom_fg", "#f1f3f4")
        self._appearance_theme_mode = self._normalize_theme_mode(raw_theme_mode)
        self._appearance_custom_bg = self._normalize_hex_color(raw_custom_bg, "#202124")
        self._appearance_custom_fg = self._normalize_hex_color(raw_custom_fg, "#f1f3f4")
        self._apply_theme_preferences()

        # Experimental features
        self._unicode_substring_highlight = bool(data.get("unicode_substring_highlight", False))
        self.unicode_substring_highlight_act.setChecked(self._unicode_substring_highlight)
        self._reading_time_enabled = bool(data.get("reading_time_enabled", False))
        self._word_index_enabled = bool(data.get("word_index_enabled", False))
        self._word_index_adaptive_density = bool(data.get("word_index_adaptive_density", True))
        raw_word_index_color = data.get("word_index_color", "white")
        overlay_defaults = self._word_index_visual_preset_for_color(raw_word_index_color)
        raw_backdrop_dark = data.get("word_index_backdrop_opacity_dark", overlay_defaults["backdrop_dark"])
        raw_backdrop_light = data.get("word_index_backdrop_opacity_light", overlay_defaults["backdrop_light"])
        raw_text_opacity = data.get("word_index_text_opacity", overlay_defaults["text"])
        raw_halo_dark = data.get("word_index_halo_opacity_dark", overlay_defaults["halo_dark"])
        raw_halo_light = data.get("word_index_halo_opacity_light", overlay_defaults["halo_light"])
        raw_word_index_alignment = data.get("word_index_alignment", "right")
        raw_word_index_top_margin = data.get("word_index_top_margin", 20)
        self._word_index_backdrop_opacity_dark = self._normalize_opacity(
            raw_backdrop_dark, 72
        )
        self._word_index_backdrop_opacity_light = self._normalize_opacity(
            raw_backdrop_light, 64
        )
        self._word_index_text_opacity = self._normalize_opacity(
            raw_text_opacity, 255
        )
        self._word_index_halo_opacity_dark = self._normalize_opacity(
            raw_halo_dark, 220
        )
        self._word_index_halo_opacity_light = self._normalize_opacity(
            raw_halo_light, 230
        )
        self._word_index_color = self._normalize_word_index_color(raw_word_index_color)
        self._word_index_alignment = self._normalize_word_index_alignment(raw_word_index_alignment)
        self._word_index_top_margin = max(0, min(60, int(raw_word_index_top_margin) if str(raw_word_index_top_margin).lstrip('-').isdigit() else 20))
        self._tamil_reading_wpm = self._normalize_reading_speed(data.get("tamil_reading_wpm", 150), 150)
        self._english_reading_wpm = self._normalize_reading_speed(data.get("english_reading_wpm", 250), 250)
        raw_google_prefix = data.get("google_search_url_prefix")
        raw_sorkuvai_prefix = data.get("sorkuvai_search_url_prefix")
        self._google_search_url_prefix = self._normalize_search_url_prefix(
            raw_google_prefix, DEFAULT_GOOGLE_SEARCH_URL_PREFIX
        )
        self._sorkuvai_search_url_prefix = self._normalize_search_url_prefix(
            raw_sorkuvai_prefix, DEFAULT_SORKUVAI_SEARCH_URL_PREFIX
        )
        self._apply_word_index_preferences()
        self.word_index_act.setChecked(self._word_index_enabled)

        # Seed defaults into settings on first run (or repair invalid/empty values)
        # so URL patterns can be changed later without rebuilding the app.
        if (
            raw_google_prefix != self._google_search_url_prefix
            or raw_sorkuvai_prefix != self._sorkuvai_search_url_prefix
            or raw_backdrop_dark != self._word_index_backdrop_opacity_dark
            or raw_backdrop_light != self._word_index_backdrop_opacity_light
            or raw_text_opacity != self._word_index_text_opacity
            or raw_halo_dark != self._word_index_halo_opacity_dark
            or raw_halo_light != self._word_index_halo_opacity_light
            or raw_word_index_color != self._word_index_color
            or raw_word_index_alignment != self._word_index_alignment
            or raw_theme_mode != self._appearance_theme_mode
            or raw_custom_bg != self._appearance_custom_bg
            or raw_custom_fg != self._appearance_custom_fg
        ):
            try:
                data["google_search_url_prefix"] = self._google_search_url_prefix
                data["sorkuvai_search_url_prefix"] = self._sorkuvai_search_url_prefix
                data["word_index_backdrop_opacity_dark"] = self._word_index_backdrop_opacity_dark
                data["word_index_backdrop_opacity_light"] = self._word_index_backdrop_opacity_light
                data["word_index_text_opacity"] = self._word_index_text_opacity
                data["word_index_halo_opacity_dark"] = self._word_index_halo_opacity_dark
                data["word_index_halo_opacity_light"] = self._word_index_halo_opacity_light
                data["word_index_color"] = self._word_index_color
                data["word_index_alignment"] = self._word_index_alignment
                data["appearance_theme_mode"] = self._appearance_theme_mode
                data["appearance_custom_bg"] = self._appearance_custom_bg
                data["appearance_custom_fg"] = self._appearance_custom_fg
                self.settings.save(data)
            except Exception:
                pass

        # Last opened file
        last_file = data.get("last_opened_file")
        if self._restore_last_session and isinstance(last_file, str) and last_file:
            if getattr(self, "_initial_file", None):
                self._last_session_file = last_file
            else:
                self._open_file_path(last_file, notify_errors=False, show_status=False)

        return True

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
            if self.current_path:
                last_opened_file = self.current_path
            elif not self._restore_last_session:
                # Keep the previously remembered file when this window was created
                # as an explicit empty window via the New Window menu action.
                last_opened_file = data.get("last_opened_file", "")
            else:
                last_opened_file = ""
            data.update({
                "word_wrap": self.editor.isWordWrap(),
                "line_numbers_visible": self.editor.isLineNumbersVisible(),
                "status_show_words": getattr(self, "_status_show_words", True),
                "status_show_sentences": getattr(self, "_status_show_sentences", True),
                "status_show_chars": getattr(self, "_status_show_chars", True),
                "status_show_line": getattr(self, "_status_show_line", True),
                "status_show_col": getattr(self, "_status_show_col", True),
                "line_spacing_preset": self._normalize_line_spacing_preset(
                    getattr(self, '_line_spacing_preset', 'normal')
                ),
                "text_margin_percent": self.editor.textMarginPercent(),
                "font_family": font.family(),
                "font_size": int(font.pointSize()) if font.pointSize() > 0 else 12,
                "default_directory": str(self.default_directory),
                "window_size": {"width": width, "height": height},
                "window_maximized": bool(self.isMaximized()),
                "autosave_interval": autosave_interval,
                "last_opened_file": last_opened_file,
                "appearance_theme_mode": self._normalize_theme_mode(
                    getattr(self, '_appearance_theme_mode', 'follow_os')
                ),
                "appearance_custom_bg": self._normalize_hex_color(
                    getattr(self, '_appearance_custom_bg', '#202124'), '#202124'
                ),
                "appearance_custom_fg": self._normalize_hex_color(
                    getattr(self, '_appearance_custom_fg', '#f1f3f4'), '#f1f3f4'
                ),
                "quick_switch_enabled": getattr(self, '_quick_switch_enabled', True),
                "force_anjal_english": getattr(self, '_force_anjal_english', True),
                "unicode_substring_highlight": getattr(self, '_unicode_substring_highlight', False),
                "reading_time_enabled": getattr(self, '_reading_time_enabled', False),
                "word_index_enabled": getattr(self, '_word_index_enabled', False),
                "word_index_adaptive_density": getattr(self, '_word_index_adaptive_density', True),
                "word_index_backdrop_opacity_dark": self._normalize_opacity(
                    getattr(self, '_word_index_backdrop_opacity_dark', 78), 78
                ),
                "word_index_backdrop_opacity_light": self._normalize_opacity(
                    getattr(self, '_word_index_backdrop_opacity_light', 70), 70
                ),
                "word_index_text_opacity": self._normalize_opacity(
                    getattr(self, '_word_index_text_opacity', 255), 255
                ),
                "word_index_halo_opacity_dark": self._normalize_opacity(
                    getattr(self, '_word_index_halo_opacity_dark', 230), 230
                ),
                "word_index_halo_opacity_light": self._normalize_opacity(
                    getattr(self, '_word_index_halo_opacity_light', 245), 245
                ),
                "word_index_color": self._normalize_word_index_color(
                    getattr(self, '_word_index_color', 'white')
                ),
                "word_index_alignment": self._normalize_word_index_alignment(
                    getattr(self, '_word_index_alignment', 'right')
                ),
                "word_index_top_margin": max(0, min(60, int(getattr(self, '_word_index_top_margin', 20)))),
                "tamil_reading_wpm": self._normalize_reading_speed(getattr(self, '_tamil_reading_wpm', 150), 150),
                "english_reading_wpm": self._normalize_reading_speed(getattr(self, '_english_reading_wpm', 250), 250),
                "google_search_url_prefix": self._normalize_search_url_prefix(
                    getattr(self, '_google_search_url_prefix', DEFAULT_GOOGLE_SEARCH_URL_PREFIX),
                    DEFAULT_GOOGLE_SEARCH_URL_PREFIX,
                ),
                "sorkuvai_search_url_prefix": self._normalize_search_url_prefix(
                    getattr(self, '_sorkuvai_search_url_prefix', DEFAULT_SORKUVAI_SEARCH_URL_PREFIX),
                    DEFAULT_SORKUVAI_SEARCH_URL_PREFIX,
                ),
            })
            self.settings.save(data)
        except Exception:
            pass

    @staticmethod
    def _normalize_reading_speed(value, default: int) -> int:
        allowed = set(range(50, 401, 50))
        try:
            speed = int(value)
        except Exception:
            speed = int(default)
        if speed in allowed:
            return speed
        if default in allowed:
            return int(default)
        return 150

    @staticmethod
    def _normalize_opacity(value, default: int) -> int:
        try:
            opacity = int(value)
        except Exception:
            opacity = int(default)
        if opacity < 0:
            return 0
        if opacity > 255:
            return 255
        return opacity

    @staticmethod
    def _normalize_word_index_color(value) -> str:
        allowed = {"white", "grey", "black", "yellow", "green", "blue"}
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in allowed:
                return normalized
        return "white"

    @staticmethod
    def _normalize_word_index_alignment(value) -> str:
        allowed = {"left", "center", "right"}
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in allowed:
                return normalized
        return "right"

    @staticmethod
    def _word_index_visual_preset_for_color(color_name: str) -> dict:
        normalized = Notepad._normalize_word_index_color(color_name)
        presets = {
            "white": {"backdrop_dark": 78, "backdrop_light": 70, "text": 255, "halo_dark": 230, "halo_light": 245},
            "grey": {"backdrop_dark": 74, "backdrop_light": 66, "text": 245, "halo_dark": 220, "halo_light": 240},
            "black": {"backdrop_dark": 88, "backdrop_light": 76, "text": 235, "halo_dark": 240, "halo_light": 240},
            "yellow": {"backdrop_dark": 72, "backdrop_light": 64, "text": 255, "halo_dark": 220, "halo_light": 230},
            "green": {"backdrop_dark": 74, "backdrop_light": 66, "text": 255, "halo_dark": 225, "halo_light": 235},
            "blue": {"backdrop_dark": 76, "backdrop_light": 68, "text": 255, "halo_dark": 230, "halo_light": 240},
        }
        return presets.get(normalized, presets["white"]).copy()

    @staticmethod
    def _normalize_theme_mode(value) -> str:
        allowed = {"follow_os", "dark", "light", "custom"}
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in allowed:
                return normalized
        return "follow_os"

    @staticmethod
    def _normalize_hex_color(value, default: str) -> str:
        if isinstance(value, str):
            cleaned = value.strip()
            if re.fullmatch(r"#[0-9a-fA-F]{6}", cleaned):
                return cleaned.lower()
        if re.fullmatch(r"#[0-9a-fA-F]{6}", default):
            return default.lower()
        return "#202124"

    @staticmethod
    def _normalize_search_url_prefix(value, default: str) -> str:
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
        return default

    @staticmethod
    def _normalize_line_spacing_preset(value) -> str:
        allowed = {"extra_tight", "tight", "normal", "casual", "extra_casual"}
        if isinstance(value, str):
            normalized = value.strip().lower().replace(" ", "_")
            if normalized in allowed:
                return normalized
        return "normal"

    @staticmethod
    def _line_spacing_percent_for_preset(preset: str) -> int:
        mapping = {
            "extra_tight": 75,
            "tight": 90,
            "normal": 100,
            "casual": 150,
            "extra_casual": 200,
        }
        key = Notepad._normalize_line_spacing_preset(preset)
        return mapping.get(key, 100)

    def change_font(self):
        current_font = self.editor.font()
        ok, font = QFontDialog.getFont(current_font, self, "Choose Font")
        if ok:
            self.editor.setFont(font)
            self._save_preferences()

 

    def _toggle_unicode_substring_highlight(self, enabled: bool):
        self._unicode_substring_highlight = bool(enabled)
        self._save_preferences()

    def _toggle_word_index(self, enabled: bool):
        self._word_index_enabled = bool(enabled)
        self.editor.setWordIndexAdaptiveDensity(getattr(self, '_word_index_adaptive_density', True))
        self.editor.setWordIndexVisible(self._word_index_enabled)
        self._save_preferences()

    def _toggle_word_index_from_status_label(self):
        self.word_index_act.toggle()

    def _toggle_wrap(self, enabled: bool):
        self.editor.setWordWrap(bool(enabled))
        self._save_preferences()

    def _toggle_line_numbers(self, enabled: bool):
        self.editor.setLineNumbersVisible(bool(enabled))
        self._save_preferences()

    def _set_line_spacing_preset(self, preset: str, *, save: bool = True, show_status: bool = True):
        key = self._normalize_line_spacing_preset(preset)
        self._line_spacing_preset = key
        self._apply_line_spacing_to_document(self._line_spacing_percent_for_preset(key))
        self._update_line_spacing_menu(key)
        if save:
            self._save_preferences()
        if show_status:
            pretty = {
                "extra_tight": "Very Tight",
                "tight": "Tight",
                "normal": "Default",
                "casual": "Relaxed",
                "extra_casual": "Loose",
            }.get(key, "Default")
            self.status.showMessage(f"Line spacing: {pretty}", 1800)

    def _apply_line_spacing_to_document(self, line_height_percent: int):
        try:
            percent = float(max(50, min(300, int(line_height_percent))))
        except Exception:
            percent = 100.0
        self.editor.setLineSpacingPercent(percent)

    def _update_line_spacing_menu(self, preset: str):
        key = self._normalize_line_spacing_preset(preset)
        self.line_spacing_extra_tight_act.setChecked(key == "extra_tight")
        self.line_spacing_tight_act.setChecked(key == "tight")
        self.line_spacing_normal_act.setChecked(key == "normal")
        self.line_spacing_casual_act.setChecked(key == "casual")
        self.line_spacing_extra_casual_act.setChecked(key == "extra_casual")

    def _set_text_margin_percent(self, percent: int, *, save: bool = True, show_status: bool = True):
        allowed = {0, 5, 10, 15, 20, 25}
        try:
            value = int(percent)
        except Exception:
            value = 0
        if value not in allowed:
            value = 0

        self.editor.setTextMarginPercent(value)

        self.margin_5_act.setChecked(value == 5)
        self.margin_10_act.setChecked(value == 10)
        self.margin_15_act.setChecked(value == 15)
        self.margin_20_act.setChecked(value == 20)
        self.margin_25_act.setChecked(value == 25)

        if show_status:
            if value == 0:
                self.status.showMessage("Margins reset", 2000)
            else:
                self.status.showMessage(f"Margins set to {value}%", 2000)

        if save:
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

        url = f"{self._google_search_url_prefix}{quote_plus(cleaned)}"
        try:
            webbrowser.open(url)
            self.status.showMessage(f'Google search: "{cleaned}"', 2000)
        except Exception as exc:
            QMessageBox.warning(self, "Search Failed", f"Could not launch browser:\n{exc}")

    def launch_sorkuvai_search(self, query: str):
        cleaned = CodeEditor._normalize_search_text(query)
        if not cleaned:
            self.status.showMessage("No word selected for Sorkuvai search", 1500)
            return

        # Sorkuvai works with URL-encoded UTF-8 query text.
        url = f"{self._sorkuvai_search_url_prefix}{quote_plus(cleaned)}"
        try:
            webbrowser.open(url)
            self.status.showMessage(f'Sorkuvai search: "{cleaned}"', 2000)
        except Exception as exc:
            QMessageBox.warning(self, "Search Failed", f"Could not launch browser:\n{exc}")

    def _normalize_unicode_text(self):
        cursor = self.editor.textCursor()
        has_selection = cursor.hasSelection()

        if has_selection:
            original = cursor.selectedText().replace("\u2029", "\n")
        else:
            original = self.editor.toPlainText()

        normalized = unicodedata.normalize("NFC", original)
        if normalized == original:
            self.status.showMessage("Unicode text is already normalized (NFC)", 2000)
            return

        if has_selection:
            cursor.beginEditBlock()
            cursor.insertText(normalized)
            cursor.endEditBlock()
            self.status.showMessage("Normalized selected text to Unicode NFC", 2000)
            return

        restore_cursor = self.editor.textCursor().position()
        update_cursor = self.editor.textCursor()
        update_cursor.beginEditBlock()
        update_cursor.select(QTextCursor.Document)
        update_cursor.insertText(normalized)
        update_cursor.endEditBlock()

        restore_cursor = min(restore_cursor, len(normalized))
        final_cursor = self.editor.textCursor()
        final_cursor.setPosition(restore_cursor)
        self.editor.setTextCursor(final_cursor)
        self.status.showMessage("Normalized document text to Unicode NFC", 2000)

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
        self._schedule_status_update()
        self._update_word_highlights()

    def _schedule_status_update(self):
        self._status_update_timer.start(90)

    def _toggle_status_item(self, item: str, visible: bool):
        """Show/hide an individual status bar counter and persist the change."""
        attr_map = {
            "words":     ("_status_show_words",     self.words_label),
            "sentences": ("_status_show_sentences", self.sentences_label),
            "chars":     ("_status_show_chars",     self.chars_label),
            "line":      ("_status_show_line",      self.line_label),
            "col":       ("_status_show_col",       self.col_label),
        }
        if item not in attr_map:
            return
        attr, widget = attr_map[item]
        setattr(self, attr, bool(visible))
        widget.setVisible(bool(visible))
        if not visible:
            widget.setText("")
        else:
            # Refresh content immediately so label isn't blank after re-enabling
            self._update_status_bar()
        self._save_preferences()

    def _update_cursor_position_status(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        if getattr(self, "_status_show_line", True):
            self.line_label.setText(f"Ln {line}")
        if getattr(self, "_status_show_col", True):
            self.col_label.setText(f"Col {col}")

    def _clear_word_highlight_on_blur(self):
        self._clear_word_highlights()
        self._update_word_match_status(None, 0)

    def _clear_word_highlight_on_navigation(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            return
        self._clear_word_highlights()
        self._update_word_match_status(None, 0)

    @staticmethod
    def _is_single_word(text: str) -> bool:
        if not text:
            return False
        return not re.search(r"\s", text)

    def _update_word_highlights(self):
        # Highlight all occurrences of the selected word; clear when selection disappears
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            self._clear_word_highlights()
            self._update_word_match_status(None, 0)
            return

        selected = self._normalize_selected_text(cursor.selectedText())
        if not self._is_single_word(selected):
            self._clear_word_highlights()
            self._update_word_match_status(None, 0)
            return

        self._clear_word_highlights()
        count = self._apply_word_highlights(selected)
        self._update_word_match_status(selected, count)

    def _apply_word_highlights(self, word: str) -> int:
        doc = self.editor.document()
        search_cursor = QTextCursor(doc)
        matches = []
        flags = QTextDocument.FindFlags() if getattr(self, '_unicode_substring_highlight', False) else QTextDocument.FindWholeWords

        while True:
            match_cursor = doc.find(word, search_cursor, flags)
            if match_cursor.isNull():
                break

            selection = QTextEdit.ExtraSelection()
            selection.cursor = match_cursor
            fmt = selection.format
            fmt.setBackground(QColor("yellow"))
            selection.format = fmt
            matches.append(selection)

            search_cursor = QTextCursor(match_cursor)
            search_cursor.setPosition(match_cursor.selectionEnd())

        base_extras = list(self.editor.extraSelections())
        merged = base_extras + matches
        self.editor.setExtraSelections(merged)

        self._base_extra_selections = base_extras
        self._word_highlight_selections = matches
        self._current_highlight_word = word
        return len(matches)

    def _clear_word_highlights(self):
        if not self._word_highlight_selections and not self._current_highlight_word:
            return
        self.editor.setExtraSelections(self._base_extra_selections)
        self._word_highlight_selections = []
        self._current_highlight_word = None
        self._base_extra_selections = []

    def _update_word_match_status(self, active_word: Optional[str], count: int):
        if active_word is None:
            self.word_match_label.setText("")
            return
        self.word_match_label.setText(f"Matches: {count}")

    @staticmethod
    def _classify_word_script(word: str) -> str:
        tamil_count = 0
        english_count = 0
        for ch in word:
            code = ord(ch)
            if 0x0B80 <= code <= 0x0BFF:
                tamil_count += 1
            elif ('A' <= ch <= 'Z') or ('a' <= ch <= 'z'):
                english_count += 1
        if tamil_count == 0 and english_count == 0:
            return "other"
        if tamil_count > english_count:
            return "tamil"
        if english_count > tamil_count:
            return "english"
        return "other"

    @staticmethod
    def _count_sentences(text: str) -> int:
        if not text or not text.strip():
            return 0

        chunks = re.split(r"[.!?\u0964\u0965\u3002\uff01\uff1f\u061f]+", text)
        return sum(1 for chunk in chunks if re.search(r"\S", chunk))

    @staticmethod
    def _is_word_char(ch: str) -> bool:
        category = unicodedata.category(ch)
        return category.startswith(("L", "N", "M"))

    @classmethod
    def _extract_word_spans(cls, text: str) -> list[tuple[int, int]]:
        if not text:
            return []

        spans = []
        current_start = None
        connector_chars = {"'", "’", "-", "‐"}
        length = len(text)

        for idx, ch in enumerate(text):
            if cls._is_word_char(ch):
                if current_start is None:
                    current_start = idx
                continue

            if (
                ch in connector_chars
                and current_start is not None
                and idx + 1 < length
                and cls._is_word_char(text[idx + 1])
            ):
                continue

            if current_start is not None:
                spans.append((current_start, idx))
                current_start = None

        if current_start is not None:
            spans.append((current_start, length))

        return spans

    @classmethod
    def _extract_word_tokens(cls, text: str) -> list[str]:
        return [text[start:end] for start, end in cls._extract_word_spans(text)]

    def _update_reading_time_status(self, text: str, tokens: Optional[list[str]] = None):
        if not getattr(self, "_reading_time_enabled", False):
            self.reading_time_label.setText("")
            return

        if tokens is None:
            tokens = self._extract_word_tokens(text)
        if not tokens:
            self.reading_time_label.setText("Read: <1 min")
            return

        tamil_words = 0
        english_words = 0
        other_words = 0
        for token in tokens:
            script = self._classify_word_script(token)
            if script == "tamil":
                tamil_words += 1
            elif script == "english":
                english_words += 1
            else:
                other_words += 1

        tamil_wpm = max(1, self._normalize_reading_speed(getattr(self, "_tamil_reading_wpm", 150), 150))
        english_wpm = max(1, self._normalize_reading_speed(getattr(self, "_english_reading_wpm", 250), 250))
        other_wpm = 180

        weighted_minutes = (
            (tamil_words / tamil_wpm) +
            (english_words / english_wpm) +
            (other_words / other_wpm)
        )
        total_words = max(1, len(tokens))
        tamil_pct = int(round((tamil_words * 100.0) / total_words))
        english_pct = int(round((english_words * 100.0) / total_words))

        if weighted_minutes < 1.0:
            estimate = "<1"
        else:
            estimate = str(int(math.ceil(weighted_minutes)))

        self.reading_time_label.setText(f"Read: {estimate} min | Ta {tamil_pct}% En {english_pct}%")

    def _update_status_bar(self):
        text = self.editor.toPlainText()
        # Only tokenise / count what is actually visible — skip expensive ops when hidden
        show_words = getattr(self, "_status_show_words", True)
        show_sentences = getattr(self, "_status_show_sentences", True)
        show_chars = getattr(self, "_status_show_chars", True)
        need_tokens = show_words or getattr(self, "_reading_time_enabled", False)
        tokens = self._extract_word_tokens(text) if need_tokens else []
        if show_words:
            self.words_label.setText(f"Words: {len(tokens)}")
        if show_sentences:
            self.sentences_label.setText(f"Sentences: {self._count_sentences(text)}")
        if show_chars:
            self.chars_label.setText(f"Chars: {len(text)}")
        self._update_reading_time_status(text, tokens=tokens if need_tokens else None)
        self._update_cursor_position_status()

    # Confirm close with save prompt and persist settings
    def closeEvent(self, event):
        if self._maybe_save_changes():
            self._save_preferences()
            event.accept()
        else:
            event.ignore()


def main():
    # Suppress Qt font-database warnings about missing OpenType support for certain
    # scripts (e.g. script 16 = Tamil on macOS with .AppleSystemUIFont).  Must be
    # set before QApplication is constructed.
    os.environ.setdefault("QT_LOGGING_RULES", "qt.text.font.db=false")

    app = QApplication(sys.argv)
    force_empty_window = "--new-window-empty" in sys.argv[1:]
    initial_file = next((arg for arg in sys.argv[1:] if not arg.startswith("-")), None)
    window = Notepad(initial_file=initial_file, restore_last_session=not force_empty_window)
    if getattr(window, "_startup_cancelled", False):
        window.deleteLater()
        sys.exit(0)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
