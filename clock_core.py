"""Pure, platform-independent clock formatting, preferences and policy."""
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from enum import Enum
from hotkey_core import DEFAULT_RECOVERY_SHORTCUT, parse_shortcut


class TopmostMode(str, Enum):
    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


TIME_PRESETS = {
    "colon": "콜론 · 12:34:56",
    "korean": "한글 · 12시 34분 56초",
    "dot": "점 구분 · 12·34·56",
}
DATE_PRESETS = {
    "korean_spaced_short": "yyyy년 MM월 dd일 (ddd)",
    "korean_full": "yyyy년 MM월 dd일 (dddd)",
    "korean_short": "MM월 dd일 (ddd)",
    "iso": "yyyy-MM-dd (ddd)",
    "slash": "yyyy/MM/dd",
}


@dataclass(frozen=True)
class ClockPreferences:
    size: str = "compact"
    theme: str = "light"
    hour_cycle: int = 12
    show_seconds: bool = True
    time_preset: str = "colon"
    date_preset: str = "korean_spaced_short"
    mode: str = "auto"
    hourly_chime: bool = True
    recovery_shortcut: str = DEFAULT_RECOVERY_SHORTCUT

    @classmethod
    def from_mapping(cls, values: dict) -> "ClockPreferences":
        defaults = cls()
        choices = {
            "size": ("compact", "large"), "theme": ("light", "dark", "aurora"),
            "hour_cycle": (12, 24), "time_preset": tuple(TIME_PRESETS),
            "date_preset": tuple(DATE_PRESETS), "mode": tuple(m.value for m in TopmostMode),
        }
        clean = {}
        for field in fields(cls):
            value = values.get(field.name, getattr(defaults, field.name))
            valid = type(value) is type(getattr(defaults, field.name))
            if field.name in choices:
                valid = valid and value in choices[field.name]
            if field.name == 'recovery_shortcut' and valid:
                try:
                    parse_shortcut(value)
                except ValueError:
                    valid = False
            clean[field.name] = value if valid else getattr(defaults, field.name)
        return cls(**clean)

    def to_mapping(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ClockText:
    time: str
    date: str


def format_clock(now: datetime, preferences: ClockPreferences | None = None) -> ClockText:
    preferences = preferences or ClockPreferences()
    hour = now.hour if preferences.hour_cycle == 24 else (now.hour % 12 or 12)
    hour_text = f"{hour:02}" if preferences.hour_cycle == 24 else str(hour)
    minute, second = f"{now.minute:02}", f"{now.second:02}"
    if preferences.time_preset == "korean":
        time_text = f"{hour_text}시 {minute}분"
        if preferences.show_seconds:
            time_text += f" {second}초"
    else:
        separator = "·" if preferences.time_preset == "dot" else ":"
        parts = [hour_text, minute]
        if preferences.show_seconds:
            parts.append(second)
        time_text = separator.join(parts)
    if preferences.hour_cycle == 12:
        time_text = ("오전 " if now.hour < 12 else "오후 ") + time_text
    weekday = ("월", "화", "수", "목", "금", "토", "일")[now.weekday()]
    year, month, day = f"{now.year:04}", f"{now.month:02}", f"{now.day:02}"
    date_text = {
        "korean_spaced_short": f"{year}년 {month}월 {day}일 ({weekday})",
        "korean_full": f"{year}년 {month}월 {day}일 ({weekday}요일)",
        "korean_short": f"{month}월 {day}일 ({weekday})",
        "iso": f"{year}-{month}-{day} ({weekday})",
        "slash": f"{year}/{month}/{day}",
    }[preferences.date_preset]
    return ClockText(time_text, date_text)


def should_be_topmost(mode: TopmostMode, auto_hide: bool | None) -> bool:
    return mode == TopmostMode.ALWAYS or (mode == TopmostMode.AUTO and auto_hide is True)


def next_tick_ms(now: datetime) -> int:
    """Align to wall-clock seconds, without accumulating timer drift."""
    return max(20, 1000 - now.microsecond // 1000)


@dataclass(frozen=True)
class ScreenArea:
    """Logical-pixel available area; right/bottom are exclusive."""
    x: int
    y: int
    width: int
    height: int


def visible_position(x, y, width, height, screens):
    """Keep a valid monitor position; recover to the closest available area."""
    if not screens:
        return x, y
    def overlap(area):
        return (max(0, min(x + width, area.x + area.width) - max(x, area.x)) *
                max(0, min(y + height, area.y + area.height) - max(y, area.y)))
    def clamped(area):
        return (max(area.x, min(x, area.x + max(0, area.width - width))),
                max(area.y, min(y, area.y + max(0, area.height - height))))
    def distance(area):
        nx, ny = clamped(area)
        return (nx - x) ** 2 + (ny - y) ** 2
    area = max(screens, key=lambda area: (overlap(area), -distance(area)))
    return clamped(area)
