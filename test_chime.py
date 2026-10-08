from datetime import datetime, timedelta, timezone
from pathlib import Path
import struct
import unittest
import wave

from clock_core import ClockPreferences
from chime_core import HourlyChime
from settings import load_preferences


class ChimeTests(unittest.TestCase):
    def setUp(self):
        self.gate = HourlyChime()
        self.hour = datetime(2026, 10, 7, 13, tzinfo=timezone(timedelta(hours=9)))

    def test_normal_boundary_and_no_repeat(self):
        self.assertFalse(self.gate.poll(self.hour - timedelta(seconds=1), 10))
        self.assertTrue(self.gate.poll(self.hour, 11))
        self.assertFalse(self.gate.poll(self.hour + timedelta(seconds=1), 12))
        self.assertFalse(self.gate.poll(self.hour + timedelta(seconds=2), 13))

    def test_midnight_and_next_hour(self):
        midnight = self.hour.replace(hour=0) + timedelta(days=1)
        for number, hour in enumerate((midnight, midnight + timedelta(hours=1))):
            self.gate.poll(hour - timedelta(seconds=1), 3600 * number)
            self.assertTrue(self.gate.poll(hour, 3600 * number + 1))

    def test_startup_at_boundary_is_silent(self):
        self.assertFalse(self.gate.poll(self.hour, 1))
        self.assertFalse(self.gate.poll(self.hour + timedelta(seconds=1), 2))

    def test_disable_and_enable_near_boundary_is_silent(self):
        self.gate.poll(self.hour - timedelta(seconds=1), 1, False)
        self.assertFalse(self.gate.poll(self.hour, 2, True))
        self.gate.reset()
        self.assertFalse(self.gate.poll(self.hour, 2.1, True))
        self.gate.poll(self.hour + timedelta(hours=1, seconds=-1), 3601, False)
        self.assertFalse(self.gate.poll(self.hour + timedelta(hours=1), 3602, False))

    def test_late_wake_and_small_stall_do_not_catch_up(self):
        for gap in (4, 3600, 86400):
            with self.subTest(gap=gap):
                gate = HourlyChime()
                gate.poll(self.hour - timedelta(seconds=gap), 1)
                self.assertFalse(gate.poll(self.hour, 1 + gap))
        self.gate.poll(self.hour - timedelta(seconds=1), 1)
        self.assertFalse(self.gate.poll(self.hour + timedelta(seconds=2), 4))

    def test_wall_clock_jumps_and_suspend_with_little_wall_change(self):
        for wall_gap, mono_gap in ((3601, 1), (-3599, 1), (1, 3601), (2, 1)):
            with self.subTest(wall_gap=wall_gap, mono_gap=mono_gap):
                gate = HourlyChime()
                gate.poll(self.hour - timedelta(seconds=wall_gap), 1)
                self.assertFalse(gate.poll(self.hour, 1 + mono_gap))

    def test_short_timer_delay_is_allowed(self):
        self.gate.poll(self.hour - timedelta(seconds=0.8), 1)
        self.assertTrue(self.gate.poll(self.hour + timedelta(seconds=0.8), 2.6))

    def test_clock_rollback_cannot_repeat_same_boundary(self):
        self.gate.poll(self.hour - timedelta(seconds=1), 1)
        self.assertTrue(self.gate.poll(self.hour, 2))
        self.gate.reset()
        self.gate.poll(self.hour - timedelta(seconds=1), 3)
        self.assertFalse(self.gate.poll(self.hour, 4))

    def test_legacy_default_and_persisted_off(self):
        self.assertTrue(load_preferences({"schema_version": 3}).hourly_chime)
        preferences = ClockPreferences(hourly_chime=False)
        self.assertEqual(load_preferences(preferences.to_mapping()), preferences)
        self.assertTrue(load_preferences({"hourly_chime": "false"}).hourly_chime)

    def test_bundled_pcm_has_two_identical_tones_and_quiet_gap(self):
        with wave.open(str(Path(__file__).parent / "assets/hourly-chime.wav")) as sound:
            self.assertEqual((sound.getnchannels(), sound.getsampwidth(), sound.getframerate()), (1, 2, 44100))
            samples = struct.unpack(f"<{sound.getnframes()}h", sound.readframes(sound.getnframes()))
        tone, gap = round(44100 * .120), round(44100 * .070)
        self.assertEqual(len(samples), tone * 2 + gap + round(44100 * .050))
        self.assertEqual(samples[:tone], samples[tone + gap:tone * 2 + gap])
        self.assertTrue(all(value == 0 for value in samples[tone:tone + gap]))
        self.assertGreater(max(samples), 10000)
        self.assertEqual(samples[0], 0)
        self.assertEqual(samples[tone - 1], 0)
        self.assertTrue(all(value == 0 for value in samples[tone * 2 + gap:]))
        # Final 3ms release is quieter than the sustained body, not abruptly cut.
        tail = samples[tone - round(44100 * .003):tone]
        self.assertLess(max(abs(value) for value in tail), 3000)
        # Count rising zero crossings to verify the high watch-like tone.
        crossings = sum(a <= 0 < b for a, b in zip(samples[:tone-1], samples[1:tone]))
        self.assertAlmostEqual(crossings / .120, 4096, delta=20)


if __name__ == "__main__":
    unittest.main()
