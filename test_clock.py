import ctypes
from datetime import datetime
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from unittest.mock import patch

from clock_core import (ClockPreferences, DATE_PRESETS, TIME_PRESETS,
                        TopmostMode, format_clock, next_tick_ms, should_be_topmost)
from platform_adapter import TaskbarMonitor, APPBARDATA
from settings import load_settings, save_settings, load_mode, load_preferences


class ClockTests(unittest.TestCase):
    def test_leap_day_and_midnight(self):
        leap = format_clock(datetime(2024, 2, 29, 0, 0, 1))
        self.assertEqual(leap.time, "오전 12:00:01")
        self.assertEqual(leap.date, "2024년 02월 29일 (목)")
        self.assertEqual(format_clock(datetime(2027, 1, 1)).date, "2027년 01월 01일 (금)")

    def test_new_defaults_and_v1_migration(self):
        preferences = load_preferences({"mode": "always", "x": 100, "y": 50})
        self.assertEqual(preferences.size, "compact")
        self.assertEqual(preferences.theme, "light")
        self.assertEqual(preferences.hour_cycle, 12)
        self.assertTrue(preferences.show_seconds)
        self.assertEqual(preferences.date_preset, "korean_spaced_short")
        self.assertEqual(preferences.mode, "always")

    def test_midnight_noon_and_24_hour(self):
        expected = {0: "오전 12:05:09", 11: "오전 11:05:09", 12: "오후 12:05:09", 23: "오후 11:05:09"}
        for hour, text in expected.items():
            now = datetime(2026, 10, 7, hour, 5, 9)
            self.assertEqual(format_clock(now).time, text)
            self.assertEqual(format_clock(now, ClockPreferences(hour_cycle=24)).time, f"{hour:02}:05:09")

    def test_every_time_preset_and_seconds_toggle(self):
        now = datetime(2026, 10, 7, 13, 5, 9)
        expected = {"colon": ("1:05:09", "1:05"), "korean": ("1시 05분 09초", "1시 05분"),
                    "dot": ("1·05·09", "1·05")}
        for preset in TIME_PRESETS:
            for seconds in (True, False):
                preferences = ClockPreferences(time_preset=preset, show_seconds=seconds)
                self.assertEqual(format_clock(now, preferences).time, "오후 " + expected[preset][0 if seconds else 1])

    def test_all_date_presets(self):
        now = datetime(2026, 10, 7)
        expected = ("2026년 10월 07일 (수)", "2026년 10월 07일 (수요일)", "10월 07일 (수)", "2026-10-07 (수)", "2026/10/07")
        for preset, text in zip(DATE_PRESETS, expected):
            self.assertEqual(format_clock(now, ClockPreferences(date_preset=preset)).date, text)

    def test_invalid_preferences_fall_back_independently(self):
        values = {"size": "bad", "theme": "bad", "hour_cycle": "24", "show_seconds": "false",
                  "date_preset": [], "time_preset": None, "mode": False}
        self.assertEqual(ClockPreferences.from_mapping(values), ClockPreferences())
        self.assertEqual(ClockPreferences.from_mapping({"hour_cycle": True}).hour_cycle, 12)
        self.assertEqual(ClockPreferences.from_mapping({"theme": "dark", "size": None}).theme, "dark")

    def test_v2_preferences_round_trip(self):
        preferences = ClockPreferences(size="large", theme="dark", hour_cycle=24, show_seconds=False,
                                       time_preset="korean", date_preset="iso", mode="never")
        with TemporaryDirectory() as folder:
            with patch("settings.settings_path", return_value=Path(folder) / "settings.json"):
                save_settings({"schema_version": 2, **preferences.to_mapping(), "x": 12, "y": 34})
                saved = load_settings()
                self.assertEqual(load_preferences(saved), preferences)
                self.assertEqual((saved["x"], saved["y"]), (12, 34))

    def test_default_date_migration_preserves_new_explicit_choice(self):
        legacy = load_preferences({"schema_version": 3, "date_preset": "korean_spaced_short"})
        self.assertEqual(format_clock(datetime(2026, 10, 7), legacy).date, "2026년 10월 07일 (수)")
        self.assertEqual(load_preferences({"schema_version": 2, "date_preset": "korean_full"}).date_preset,
                         "korean_spaced_short")
        self.assertEqual(load_preferences({"schema_version": 2, "date_preset": "iso"}).date_preset, "iso")
        self.assertEqual(load_preferences({"schema_version": 3, "date_preset": "korean_full"}).date_preset,
                         "korean_full")

    def test_topmost_modes_and_unknown_state(self):
        for state in (False, True, None):
            self.assertTrue(should_be_topmost(TopmostMode.ALWAYS, state))
            self.assertFalse(should_be_topmost(TopmostMode.NEVER, state))
            self.assertEqual(should_be_topmost(TopmostMode.AUTO, state), state is True)

    def test_ticks_align_to_seconds(self):
        self.assertEqual(next_tick_ms(datetime(2026, 1, 1)), 1000)
        self.assertEqual(next_tick_ms(datetime(2026, 1, 1, microsecond=456000)), 544)
        self.assertEqual(next_tick_ms(datetime(2026, 1, 1, microsecond=999999)), 20)

    def test_windows_shell_bitmask_and_explorer_restart(self):
        monitor = TaskbarMonitor.__new__(TaskbarMonitor)
        monitor.supported = True
        monitor._find_window = lambda *args: 123
        for flags in (0, 1, 2, 3):
            def query(message, pointer):
                self.assertEqual(message, 4)
                self.assertEqual(pointer._obj.cbSize, ctypes.sizeof(APPBARDATA))
                return flags
            monitor._query = query
            self.assertEqual(monitor.auto_hide_enabled(), bool(flags & 1))
        monitor._find_window = lambda *args: 0
        self.assertIsNone(monitor.auto_hide_enabled())

    def test_other_platform_skips_shell(self):
        with patch("platform_adapter.sys.platform", "darwin"):
            monitor = TaskbarMonitor()
            self.assertFalse(monitor.supported)
            self.assertIsNone(monitor.auto_hide_enabled())

    def test_settings_round_trip_and_corrupt_file(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            with patch("settings.settings_path", return_value=path):
                self.assertEqual(load_settings(), {})
                save_settings({"mode": "always", "x": 20, "y": 30})
                self.assertEqual(load_mode(load_settings()), TopmostMode.ALWAYS)
                path.write_text("broken", encoding="utf-8")
                self.assertEqual(load_settings(), {})
                self.assertEqual(load_mode({"mode": "bad"}), TopmostMode.AUTO)


if __name__ == "__main__":
    unittest.main()
