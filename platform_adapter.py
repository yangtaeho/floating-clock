"""Windows Shell integration. This module also imports safely on macOS."""
import ctypes
import sys
from ctypes import wintypes


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
