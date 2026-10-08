"""Actual Carbon registration/event delivery; physical keypress needs user QA."""
import ctypes as C
import json
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from main import ClockApp
from mac_hotkey import HotKeyID


def run():
    qt = QApplication([])
    qt.setStyle('Fusion')
    with patch('main.load_settings', return_value={}), patch('main.save_settings'):
        app = ClockApp()
        try:
            hotkey = app.hotkey
            assert hotkey.mac and hotkey.registered, hotkey.status
            assert app.preferences.clock_scale == 90
            app.set_preference('mode', 'never')
            app.root.hide()
            lib = hotkey.mac.lib
            hotkey.mac.bind('CreateEvent',[C.c_void_p,C.c_uint32,C.c_uint32,C.c_double,C.c_uint32,C.POINTER(C.c_void_p)])
            hotkey.mac.bind('SetEventParameter',[C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p])
            hotkey.mac.bind('SendEventToEventTarget',[C.c_void_p,C.c_void_p])
            hotkey.mac.bind('ReleaseEvent',[C.c_void_p],None)
            def native_event(identifier, kind=5):
                event = C.c_void_p()
                key = HotKeyID(hotkey.mac.signature, identifier)
                assert lib.CreateEvent(None,0x6B657962,kind,0,0,C.byref(event)) == 0
                try:
                    assert lib.SetEventParameter(event,0x2D2D2D2D,0x686B6964,C.sizeof(key),C.byref(key)) == 0
                    assert lib.SendEventToEventTarget(event, hotkey.mac.target) == 0
                    QTest.qWait(40)
                finally:
                    lib.ReleaseEvent(event)
            native_event(hotkey.HOTKEY_ID)
            assert hotkey.armed and not app.root.isVisible()
            native_event(hotkey.HOTKEY_ID,6)
            assert hotkey.SECOND_ID in hotkey.mac.references
            native_event(hotkey.SECOND_ID)
            assert app.root.isVisible() and not hotkey.armed and hotkey.SECOND_ID not in hotkey.mac.references
            app.root.hide()
            native_event(hotkey.HOTKEY_ID)
            native_event(hotkey.HOTKEY_ID,6)
            QTest.qWait(1100)
            assert not hotkey.armed and hotkey.SECOND_ID not in hotkey.mac.references
            app.set_preference('recovery_shortcut','Ctrl+Alt+Shift+D')
            assert hotkey.registered, hotkey.status
            native_event(hotkey.HOTKEY_ID)
            assert app.root.isVisible()
            hotkey.suspend()
            assert not hotkey.mac.references
            hotkey.resume()
            assert hotkey.registered
            app.set_preference('recovery_shortcut','')
            assert not hotkey.registered and not hotkey.mac.references
            data={'registered_default':True,'native_event_restores_hidden':True,'timeout_unregisters_second':True,
                  'custom_single':True,'suspend_resume_disable':True,'mac_default_scale':90,'physical_keypress_verified':False}
            Path('build').mkdir(exist_ok=True)
            Path('build/packaged-mac-hotkey.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
            print('PASS: real Carbon default/custom registration, native events restore hidden clock, timeout, suspend/disable')
        finally:
            app.shutdown()


if __name__ == '__main__':
    run()
