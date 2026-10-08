"""Settings geometry regression, also runnable on macOS offscreen CI."""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
import json
from pathlib import Path

from PySide6.QtCore import QObject, QEvent, QRect, Qt
from PySide6.QtGui import QFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStyle
from main import ClockApp


class StyleChanges(QObject):
    def __init__(self):
        super().__init__()
        self.changes = 0

    def eventFilter(self, watched, event):
        if event.type() == QEvent.StyleChange:
            self.changes += 1
        return False


def geometry(panel, combo):
    return (panel.geometry().getRect(), panel.body.size().toTuple(),
            panel.scroll.viewport().size().toTuple(), combo.geometry().getRect(),
            panel.scroll.verticalScrollBar().isVisible())


def run():
    qt = QApplication([])
    qt.setStyle('Fusion')
    qt.setFont(QFont('Malgun Gothic', 9))
    cases = 0
    with patch('main.load_settings', return_value={'schema_version': 3, 'recovery_shortcut': ''}), \
            patch('main.save_settings'), patch('main.ChimeAudio.play', return_value=True):
        app = ClockApp()
        try:
            for available_height in (420, 1600):
                for theme in ('light', 'dark', 'aurora'):
                    app.set_preference('theme', theme)
                    screen = SimpleNamespace(availableGeometry=lambda: QRect(0, 0, 1400, available_height))
                    with patch.object(app.root, 'screen', return_value=screen):
                        app.toggle_settings()
                    panel = app.settings_panel
                    QTest.qWait(50)
                    bar = panel.scroll.verticalScrollBar()
                    assert not bar.style().styleHint(QStyle.SH_ScrollBar_Transient, None, bar)
                    assert panel.scroll.verticalScrollBarPolicy() == (
                        Qt.ScrollBarAlwaysOn if available_height == 420 else Qt.ScrollBarAlwaysOff)
                    combo = panel.controls['date_preset']
                    panel.scroll.ensureWidgetVisible(combo)
                    QTest.qWait(30)
                    initial = geometry(panel, combo)
                    changes = StyleChanges()
                    for widget in (panel, combo, bar, panel.scroll.viewport()):
                        widget.installEventFilter(changes)
                    for minute in range(60):
                        panel.update_preview(datetime(2026, 12, 31, 23, 59) + timedelta(minutes=minute))
                        qt.processEvents()
                        assert geometry(panel, combo) == initial, 'Clock text moved settings controls/scrollbar'
                    for key, value in (('hour_cycle', 24), ('show_seconds', False),
                                       ('time_preset', 'korean'), ('date_preset', 'iso'),
                                       ('hour_cycle', 12), ('show_seconds', True)):
                        app.set_preference(key, value)
                        qt.processEvents()
                        assert geometry(panel, combo) == initial, 'Preference change moved settings controls'
                    assert changes.changes == 0, 'Non-theme updates repolished panel/selector/scrollbar'
                    combo.showPopup()
                    QTest.qWait(30)
                    popup = combo.view().window()
                    opened = popup.geometry().getRect()
                    popup.installEventFilter(changes)
                    for second in range(30):
                        panel.update_preview(datetime(2026, 1, 1, 11, 11, second))
                        app.apply_policy()
                        panel.refresh()
                        qt.processEvents()
                        assert popup.isVisible() and popup.geometry().getRect() == opened
                        assert geometry(panel, combo) == initial
                    assert changes.changes == 0, 'Live dropdown/style changed during preview/policy refresh'
                    combo.hidePopup()
                    if available_height == 420:
                        bar.setValue(bar.maximum())
                        QTest.qWait(1100)
                        assert bar.isVisible() and geometry(panel, combo) == initial
                        assert bar.value() == bar.maximum(), 'Timer jumped the scroll position'
                    panel.close()
                    qt.processEvents()
                    cases += 1
        finally:
            app.shutdown()
    Path('build').mkdir(exist_ok=True)
    Path('build/packaged-settings.json').write_text(json.dumps({'passed': True, 'theme_screen_cases': cases,
        'preview_updates_per_case': 90, 'physical_mac_flicker_verified': False}, indent=2), encoding='utf-8')
    print(f'PASS: {cases} theme/screen cases; stable settings, dropdown and scrollbar through text/settings/timer updates')


if __name__ == '__main__':
    run()
