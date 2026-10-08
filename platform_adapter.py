"""Windows Shell integration. This module also imports safely on macOS."""
import ctypes
import sys
from ctypes import wintypes
from PySide6.QtCore import QAbstractNativeEventFilter, QTimer
from hotkey_core import parse_shortcut, DEFAULT_RECOVERY_SHORTCUT


def set_app_identity(app_id):
    """Set Shell identity before any clock/tray windows are created."""
    if sys.platform != 'win32':
        return None
    shell = ctypes.WinDLL('shell32')
    function = shell.SetCurrentProcessExplicitAppUserModelID
    function.argtypes, function.restype = [wintypes.LPCWSTR], ctypes.c_long
    result = function(app_id)
    if result != 0:
        raise OSError(f'Cannot set Windows application identity: {result:#x}')
    return app_identity()


def app_identity():
    if sys.platform != 'win32':
        return None
    shell, ole = ctypes.WinDLL('shell32'), ctypes.WinDLL('ole32')
    function = shell.GetCurrentProcessExplicitAppUserModelID
    function.argtypes, function.restype = [ctypes.POINTER(ctypes.c_wchar_p)], ctypes.c_long
    value = ctypes.c_wchar_p()
    if function(ctypes.byref(value)) != 0:
        return None
    try:
        return value.value
    finally:
        ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        ole.CoTaskMemFree(ctypes.cast(value, ctypes.c_void_p))


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
    """One or two native key chords; the second registration has a short lifetime."""
    HOTKEY_ID = 0x4FC1
    SECOND_ID = 0x4FC2

    def __init__(self, application, callback, shortcut=DEFAULT_RECOVERY_SHORTCUT):
        super().__init__()
        self.application, self.callback = application, callback
        self.registered = self.armed = self.second_registered = self.suspended = False
        self.supported = sys.platform in ('win32', 'darwin')
        self.mac = None
        self.unavailable_status = '전역 키 미지원 · 트레이/메뉴 막대에서 복원하세요'
        self.timer = QTimer(application)
        self.timer.setSingleShot(True)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.disarm)
        if sys.platform == 'win32':
            self.user32 = ctypes.WinDLL('user32', use_last_error=True)
            self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self.user32.RegisterHotKey.restype = wintypes.BOOL
            self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            self.user32.UnregisterHotKey.restype = wintypes.BOOL
            application.installNativeEventFilter(self)
        elif sys.platform == 'darwin':
            from mac_hotkey import MacHotkeyBackend
            try:
                self.mac = MacHotkeyBackend(self.trigger)
            except (OSError, AttributeError) as error:
                self.supported = False
                self.unavailable_status = f'Mac 전역 키 초기화 실패 · 메뉴 막대에서 복원하세요 ({error})'
        self.configure(shortcut)

    def register_key(self, identifier, chord):
        if self.mac:
            return self.mac.register(identifier, chord)
        return bool(self.user32.RegisterHotKey(None, identifier, chord.modifiers | 0x4000, chord.key))

    def unregister_key(self, identifier):
        if self.mac:
            self.mac.unregister(identifier)
        else:
            self.user32.UnregisterHotKey(None, identifier)

    def configure(self, shortcut):
        self.unregister()
        self.shortcut = shortcut
        try:
            self.chords = parse_shortcut(shortcut)
            if self.mac:
                from mac_hotkey import native_chord
                for chord in self.chords:
                    native_chord(chord)
        except ValueError as error:
            self.chords = ()
            self.status = str(error)
            return
        self.resume()

    def resume(self):
        self.suspended = False
        if not self.supported:
            self.status = self.unavailable_status
        elif not self.chords:
            self.status = '사용 안 함 · 트레이에서 복원하세요'
        elif not self.registered:
            first = self.chords[0]
            self.registered = self.register_key(self.HOTKEY_ID, first)
            self.status = '사용 가능' if self.registered else (self.mac.last_error if self.mac else '등록 실패 · 다른 앱이 사용 중일 수 있습니다')

    def disarm(self):
        self.timer.stop()
        if self.second_registered:
            self.unregister_key(self.SECOND_ID)
        self.second_registered = self.armed = False
        if self.registered:
            self.status = '사용 가능'

    def unregister(self):
        self.disarm()
        if self.registered:
            self.unregister_key(self.HOTKEY_ID)
        self.registered = False

    def suspend(self):
        self.unregister()
        self.suspended = True
        self.status = '키 입력 중 · 적용 또는 입력 종료 후 등록'

    def trigger(self, hotkey_id):
        if hotkey_id == self.SECOND_ID and self.armed:
            self.disarm()
            self.callback()
        elif hotkey_id == self.HOTKEY_ID and self.registered:
            if len(self.chords) == 1 or (self.armed and self.chords[1].key == self.chords[0].key
                                       and self.chords[1].modifiers in (0, self.chords[0].modifiers)):
                self.disarm()
                self.callback()
            else:
                self.disarm()
                first, second = self.chords
                if second != first:
                    self.second_registered = self.register_key(self.SECOND_ID, second)
                # Repeating the first chord also completes the default C,C gesture.
                self.armed = True
                self.timer.start()
                if second != first and not self.second_registered:
                    self.status = '두 번째 키 등록 실패 · 같은 첫 조합을 한 번 더 누르세요'

    def nativeEventFilter(self, event_type, message):
        if sys.platform == 'win32' and event_type in (b'windows_generic_MSG', b'windows_dispatcher_MSG'):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam in (self.HOTKEY_ID, self.SECOND_ID):
                self.trigger(msg.wParam)
                return True, 0
        return False, 0

    def close(self):
        self.unregister()
        if sys.platform == 'win32':
            self.application.removeNativeEventFilter(self)
        if self.mac:
            self.mac.close()
        self.timer.deleteLater()
