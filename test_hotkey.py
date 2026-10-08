import unittest
from hotkey_core import parse_shortcut, DEFAULT_RECOVERY_SHORTCUT, KeyChord
from clock_core import ClockPreferences
from bundle_policy import keep_binary
from mac_hotkey import native_chord

class ShortcutTests(unittest.TestCase):
    def test_mac_keys_and_qt_modifier_mapping(self):
        self.assertEqual(native_chord(parse_shortcut('Ctrl+Alt+Shift+C, C')[0]), (8, 256+2048+512))
        self.assertEqual(native_chord(parse_shortcut('Meta+J')[0]), (38,4096))
        self.assertEqual(native_chord(parse_shortcut('Alt+F20')[0]), (90,2048))
        self.assertEqual(native_chord(parse_shortcut('Ctrl+Left')[0]), (123,256))
        for shortcut in ('Ctrl+F21','Ctrl+F24'):
            with self.assertRaises(ValueError): native_chord(parse_shortcut(shortcut)[0])
    def test_default_two_steps(self):
        self.assertEqual(parse_shortcut(DEFAULT_RECOVERY_SHORTCUT), (KeyChord(7, 67), KeyChord(0, 67)))
    def test_custom_single_and_two_steps(self):
        self.assertEqual(parse_shortcut('Ctrl+Alt+F10'), (KeyChord(3, 0x79),))
        self.assertEqual(parse_shortcut('Meta+Shift+D, Alt+E'), (KeyChord(12, 68), KeyChord(1, 69)))
    def test_disabled_and_mapping_persistence(self):
        self.assertEqual(parse_shortcut(''), ())
        p=ClockPreferences(recovery_shortcut='Alt+F11')
        self.assertEqual(ClockPreferences.from_mapping(p.to_mapping()),p)
        self.assertEqual(ClockPreferences.from_mapping({'recovery_shortcut':''}).recovery_shortcut,'')
        self.assertEqual(ClockPreferences.from_mapping({}).recovery_shortcut,DEFAULT_RECOVERY_SHORTCUT)
    def test_invalid_unmodified_keys_and_three_steps(self):
        for key in ('C','Shift+C','Ctrl+Ctrl+C','Ctrl+Unknown','Ctrl+C, C, C','Ctrl+F25','Ctrl+'):
            with self.subTest(key=key):
                with self.assertRaises(ValueError): parse_shortcut(key)
                self.assertEqual(ClockPreferences.from_mapping({'recovery_shortcut':key}).recovery_shortcut,DEFAULT_RECOVERY_SHORTCUT)

class BundleTests(unittest.TestCase):
    def test_keep_required_cross_platform_paths(self):
        for name in ('PySide6/Qt6Multimedia.dll','PySide6/Qt6Gui.dll','PySide6/plugins/platforms/qwindows.dll',
                     'PySide6/Qt/plugins/platforms/libqcocoa.dylib','PySide6/Qt/plugins/platforms/libqoffscreen.dylib'):
            self.assertTrue(keep_binary(name),name)
    def test_exclude_unused_modules_and_video_codecs(self):
        for name in ('PySide6/opengl32sw.dll','PySide6/avcodec-61.dll','PySide6/Qt6Quick.dll',
                     'PySide6/Qt/lib/QtQuick.framework/Versions/A/QtQuick','PySide6/Qt/lib/libavformat.61.dylib',
                     'PySide6/plugins/multimedia/ffmpegmediaplugin.dll','PySide6/Qt/plugins/imageformats/libqpdf.dylib'):
            self.assertFalse(keep_binary(name),name)

if __name__=='__main__': unittest.main()
