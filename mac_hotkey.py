"""macOS Carbon hotkeys without keyboard monitoring or external dependencies."""
import ctypes as C
from itertools import count
from PySide6.QtCore import QTimer


KEY_CODES = dict(zip('ASDFHGZXCVBQWERYT', (0,1,2,3,4,5,6,7,8,9,11,12,13,14,15,16,17)))
KEY_CODES.update(dict(zip('1234659780OUIPLJKNM', (18,19,20,21,22,23,25,26,28,29,31,32,34,35,37,38,40,45,46))))
FUNCTION_CODES = (122,120,99,118,96,97,98,100,101,109,103,111,105,107,113,106,64,79,80,90)
SPECIAL_CODES = {0x20:49, 9:48, 0x24:115, 0x23:119, 0x2d:114, 0x2e:117,
                 0x25:123, 0x26:126, 0x27:124, 0x28:125, 0x21:116, 0x22:121}


def native_chord(chord):
    """Qt portable Ctrl is Command on Mac; portable Meta is Control."""
    if 0x70 <= chord.key <= 0x83:
        key = FUNCTION_CODES[chord.key-0x70]
    elif chord.key in SPECIAL_CODES:
        key = SPECIAL_CODES[chord.key]
    else:
        key = KEY_CODES.get(chr(chord.key))
    if key is None:
        raise ValueError('Mac에서는 영문/숫자/F1~F20/방향·이동 키를 사용하세요')
    modifiers = sum(native for mask, native in ((1,2048),(2,256),(4,512),(8,4096)) if chord.modifiers & mask)
    return key, modifiers


class HotKeyID(C.Structure):
    _fields_ = [('signature', C.c_uint32), ('id', C.c_uint32)]


class EventType(C.Structure):
    _fields_ = [('eventClass', C.c_uint32), ('eventKind', C.c_uint32)]


HANDLER = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_void_p, C.c_void_p)
_signatures = count(0x466C436C)


class MacHotkeyBackend:
    def __init__(self, callback):
        self.callback = callback
        self.signature = next(_signatures)
        self.references = {}
        self.pressed = set()
        self.last_error = ''
        self.closed = False
        self.lib = C.CDLL('/System/Library/Frameworks/Carbon.framework/Carbon')
        self.bind('GetApplicationEventTarget', [], C.c_void_p)
        self.bind('InstallEventHandler', [C.c_void_p,HANDLER,C.c_uint32,C.POINTER(EventType),C.c_void_p,C.POINTER(C.c_void_p)])
        self.bind('RemoveEventHandler', [C.c_void_p])
        self.bind('GetEventKind', [C.c_void_p], C.c_uint32)
        self.bind('GetEventParameter', [C.c_void_p,C.c_uint32,C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.c_void_p])
        self.bind('RegisterEventHotKey', [C.c_uint32,C.c_uint32,HotKeyID,C.c_void_p,C.c_uint32,C.POINTER(C.c_void_p)])
        self.bind('UnregisterEventHotKey', [C.c_void_p])
        self.target = self.lib.GetApplicationEventTarget()
        self.handler = HANDLER(self.handle_event)  # Keep the native callback alive.
        self.handler_ref = C.c_void_p()
        event_types = (EventType*2)(EventType(0x6B657962,5), EventType(0x6B657962,6))
        result = self.lib.InstallEventHandler(self.target,self.handler,2,event_types,None,C.byref(self.handler_ref))
        if result:
            raise OSError(f'Mac hotkey event handler unavailable ({result})')

    def bind(self, name, args, result=C.c_int32):
        function = getattr(self.lib, name)
        function.argtypes, function.restype = args, result

    def register(self, identifier, chord):
        try:
            key, modifiers = native_chord(chord)
        except ValueError as error:
            self.last_error = str(error)
            return False
        reference = C.c_void_p()
        result = self.lib.RegisterEventHotKey(key, modifiers, HotKeyID(self.signature,identifier),
                                            self.target,1,C.byref(reference))
        self.last_error = '' if result == 0 else f'등록 실패 ({result}) · 다른 앱/시스템 키와 충돌할 수 있습니다'
        if result == 0:
            self.references[identifier] = reference
        return result == 0

    def unregister(self, identifier):
        reference = self.references.pop(identifier, None)
        self.pressed.discard(identifier)
        if reference:
            self.lib.UnregisterEventHotKey(reference)

    def handle_event(self, next_handler, event, user_data):
        identifier = HotKeyID()
        if self.lib.GetEventParameter(event,0x2D2D2D2D,0x686B6964,None,C.sizeof(identifier),None,C.byref(identifier)):
            return -9874  # eventNotHandledErr
        if self.closed or identifier.signature != self.signature or identifier.id not in self.references:
            return -9874
        if self.lib.GetEventKind(event) == 6:
            self.pressed.discard(identifier.id)
        elif identifier.id not in self.pressed:
            self.pressed.add(identifier.id)
            QTimer.singleShot(0, lambda key=identifier.id: self.deliver(key))
        return 0

    def deliver(self, identifier):
        if not self.closed and identifier in self.references:
            self.callback(identifier)

    def close(self):
        self.closed = True
        for identifier in list(self.references):
            self.unregister(identifier)
        self.lib.RemoveEventHandler(self.handler_ref)
