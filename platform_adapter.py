"""Windows Shell integration. This module also imports safely on macOS."""
import ctypes
import sys
from ctypes import wintypes
from PySide6.QtCore import QAbstractNativeEventFilter


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class APPBARDATA(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                ("uCallbackMessage", wintypes.UINT), ("uEdge", wintypes.UINT),
                ("rc", RECT), ("lParam", ctypes.c_ssize_t)]


class TaskbarMonitor:
    def __init__(self):
        self.supported = sys.platform == "win32"
        self._query = None
        self._find_window = None
        if self.supported:
            self._query = ctypes.WinDLL("shell32").SHAppBarMessage
            self._query.argtypes = [wintypes.DWORD, ctypes.POINTER(APPBARDATA)]
            self._query.restype = ctypes.c_size_t
            self._find_window = ctypes.WinDLL("user32").FindWindowW
            self._find_window.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
            self._find_window.restype = wintypes.HWND

    def auto_hide_enabled(self) -> bool | None:
        if not self.supported:
            return None
        # Explorer may be restarting. Do not confuse missing taskbar with OFF.
        if not self._find_window("Shell_TrayWnd", None):
            return None
        data = APPBARDATA()
        data.cbSize = ctypes.sizeof(data)
        return bool(self._query(0x00000004, ctypes.byref(data)) & 0x1)


class WindowChrome:
    """Native z-order changes must never activate or reshape a window."""
    def __init__(self):
        self.supported = sys.platform == "win32"
        if self.supported:
            self.user32 = ctypes.WinDLL("user32", use_last_error=True)
            self.user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                               ctypes.c_int, ctypes.c_int, wintypes.UINT]
            self.user32.SetWindowPos.restype = wintypes.BOOL
            self._get_style = getattr(self.user32, "GetWindowLongPtrW", self.user32.GetWindowLongW)
            self._get_style.argtypes = [wintypes.HWND, ctypes.c_int]
            self._get_style.restype = ctypes.c_ssize_t

    def is_topmost(self, handle: int) -> bool | None:
        if not self.supported:
            return None
        return bool(self._get_style(handle, -20) & 0x8)

    def set_topmost(self, handle: int, enabled: bool) -> bool | None:
        if not self.supported:
            return None
        # HWND_TOPMOST/-NOTOPMOST; NOMOVE | NOSIZE | NOACTIVATE.
        return bool(self.user32.SetWindowPos(handle, wintypes.HWND(-1 if enabled else -2), 0, 0, 0, 0, 0x0013))


class RecoveryHotkey(QAbstractNativeEventFilter):
    """Windows Ctrl+Alt+C works while the clock is hidden or another app is active."""
    HOTKEY_ID = 0x4FC1

    def __init__(self, application, callback):
        super().__init__()
        self.application, self.callback = application, callback
        self.registered = False
        if sys.platform == 'win32':
            self.user32 = ctypes.WinDLL('user32', use_last_error=True)
            self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self.user32.RegisterHotKey.restype = wintypes.BOOL
            self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            self.user32.UnregisterHotKey.restype = wintypes.BOOL
            # MOD_NOREPEAT | MOD_CONTROL | MOD_ALT, C.
            self.registered = bool(self.user32.RegisterHotKey(None, self.HOTKEY_ID, 0x4003, 0x43))
            if self.registered:
                application.installNativeEventFilter(self)

    def nativeEventFilter(self, event_type, message):
        if self.registered and event_type in (b'windows_generic_MSG', b'windows_dispatcher_MSG'):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == self.HOTKEY_ID:
                self.callback()
                return True, 0
        return False, 0

    def close(self):
        if self.registered:
            self.application.removeNativeEventFilter(self)
            self.user32.UnregisterHotKey(None, self.HOTKEY_ID)
            self.registered = False
