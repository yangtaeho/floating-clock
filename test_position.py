import unittest
from clock_core import ScreenArea, visible_position


class PositionTests(unittest.TestCase):
    def setUp(self):
        self.laptop = ScreenArea(0, 0, 1920, 1040)
        self.uhd = ScreenArea(-2560, -100, 2560, 1400)

    def test_valid_negative_monitor_position_is_preserved(self):
        self.assertEqual(visible_position(-2400, 1100, 220, 56, [self.laptop, self.uhd]), (-2400, 1100))

    def test_disconnected_monitor_recovers_whole_window(self):
        self.assertEqual(visible_position(-2400, 1100, 220, 56, [self.laptop]), (0, 984))

    def test_partial_window_and_taskbar_work_area(self):
        self.assertEqual(visible_position(1880, 1020, 220, 56, [self.laptop]), (1700, 984))

    def test_largest_overlap_wins_and_gap_uses_nearest_area(self):
        right = ScreenArea(2200, 0, 1920, 1040)
        self.assertEqual(visible_position(1850, 0, 500, 56, [self.laptop, right]), (2200, 0))
        self.assertEqual(visible_position(2070, 900, 100, 56, [self.laptop, right]), (2200, 900))

    def test_above_screen_and_oversized_window_anchor_visible_controls(self):
        self.assertEqual(visible_position(100, -800, 220, 56, [self.laptop]), (100, 0))
        self.assertEqual(visible_position(100, 100, 3000, 2000, [self.laptop]), (0, 0))

    def test_no_screen_during_transition(self):
        self.assertEqual(visible_position(1, 2, 220, 56, []), (1, 2))


if __name__ == '__main__':
    unittest.main()
