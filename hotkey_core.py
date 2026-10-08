"""Pure Windows shortcut validation; no Qt or platform imports."""
from dataclasses import dataclass

DEFAULT_RECOVERY_SHORTCUT = 'Ctrl+Alt+Shift+C, C'
MODIFIERS = {'ctrl': 2, 'alt': 1, 'shift': 4, 'meta': 8, 'win': 8}
KEYS = {'space': 0x20, 'tab': 9, 'home': 0x24, 'end': 0x23,
        'insert': 0x2d, 'delete': 0x2e, 'left': 0x25, 'up': 0x26,
        'right': 0x27, 'down': 0x28, 'pgup': 0x21, 'pgdown': 0x22}

@dataclass(frozen=True)
class KeyChord:
    modifiers: int
    key: int


def parse_shortcut(text):
    if not isinstance(text, str) or len(text) > 100:
        raise ValueError('단축키는 1~2단계 조합으로 입력하세요')
    if not text.strip():
        return ()
    parts = text.split(',')
    if not 1 <= len(parts) <= 2:
        raise ValueError('최대 두 단계까지 사용할 수 있습니다')
    chords = []
    for part in parts:
        tokens = [token.strip().lower() for token in part.split('+')]
        modifiers = 0
        for token in tokens[:-1]:
            if token not in MODIFIERS or modifiers & MODIFIERS[token]:
                raise ValueError('지원하지 않는 조합입니다')
            modifiers |= MODIFIERS[token]
        name = tokens[-1]
        if len(name) == 1 and name.isascii() and name.isalnum():
            key = ord(name.upper())
        elif name.startswith('f') and name[1:].isdigit() and 1 <= int(name[1:]) <= 24:
            key = 0x70 + int(name[1:]) - 1
        elif name in KEYS:
            key = KEYS[name]
        else:
            raise ValueError('영문/숫자/F1~F24/방향·이동 키를 사용하세요')
        chords.append(KeyChord(modifiers, key))
    if not chords[0].modifiers & (1 | 2 | 8):
        raise ValueError('첫 단계에 Ctrl, Alt 또는 Win 키를 포함하세요')
    return tuple(chords)
