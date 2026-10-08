"""Stable Qt preferences panel: no widget recreation during changes."""
from datetime import datetime
from PySide6.QtCore import Qt, QSignalBlocker, QPointF
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QPainter, QPen, QColor, QPolygonF, QPalette, QFontMetrics
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QComboBox,
                               QPushButton, QButtonGroup, QFrame, QListView, QKeySequenceEdit, QScrollArea, QSizePolicy, QProxyStyle, QStyle)
from clock_core import TIME_PRESETS, DATE_PRESETS, format_clock
from hotkey_core import parse_shortcut
from ui_components import RoundedWindow, button


class PersistentScrollStyle(QProxyStyle):
    """Avoid macOS overlay/auto-hide scrollbar transitions in settings."""
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_ScrollBar_Transient:
            return 0
        return super().styleHint(hint, option, widget, returnData)


class ClockComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.arrow_color = "#718094"

    def prepare_popup(self):
        # Prepare the native container before its first visible frame.
        container = self.view().window()
        palette = self.palette()
        if container.palette() != palette:
            container.setPalette(palette)
        container.setAutoFillBackground(True)
        sheet = f"background: {palette.color(QPalette.Base).name()};"
        if container.styleSheet() != sheet:
            container.setStyleSheet(sheet)

    def showPopup(self):
        self.prepare_popup()
        super().showPopup()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(self.arrow_color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        x, y = self.width() - 18, self.height() / 2
        painter.drawPolyline(QPolygonF([QPointF(x - 4, y - 2), QPointF(x, y + 2), QPointF(x + 4, y - 2)]))


class ShortcutEditor(QKeySequenceEdit):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel
        self.setMaximumSequenceLength(2)
        self.setAccessibleName('전역 시계 복원 단축키')

    def focusInEvent(self, event):
        self.panel.app.hotkey.suspend()
        for shortcut in self.panel.app.shortcuts:
            shortcut.setEnabled(False)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.panel.resume_shortcuts()


class SettingsPanel(RoundedWindow):
    def __init__(self, app):
        super().__init__(app.root, flags=app.utility_flags, radius=18)
        self.app = app
        self.setWindowTitle("시계 설정")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.controls = {}
        self.groups = []
        self.applied_theme = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea(self)
        self.scroll.setObjectName('settingsScroll')
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scrollbar = self.scroll.verticalScrollBar()
        self.scroll_style = PersistentScrollStyle('Fusion')
        self.scroll_style.setParent(scrollbar)
        scrollbar.setStyle(self.scroll_style)
        self.body = QWidget()
        self.body.setObjectName('settingsBody')
        self.scroll.setWidget(self.body)
        outer.addWidget(self.scroll)
        layout = QVBoxLayout(self.body)
        layout.setContentsMargins(24, 18, 24, 20)
        layout.setSpacing(13)
        header = QHBoxLayout()
        title = QLabel("시계 설정")
        title.setFont(QFont("Malgun Gothic", 17, QFont.Bold))
        title.setAttribute(Qt.WA_TransparentForMouseEvents)
        header.addWidget(title)
        header.addStretch()
        close = button("×", self.close, self)
        close.setFixedSize(30, 30)
        header.addWidget(close)
        layout.addLayout(header)
        self.description = QLabel("변경한 설정은 바로 적용되고 저장됩니다.")
        layout.addWidget(self.description)
        self.preview = QFrame()
        self.preview.setObjectName("preview")
        preview_layout = QVBoxLayout(self.preview)
        preview_layout.setContentsMargins(16, 14, 16, 14)
        preview_layout.setSpacing(5)
        self.preview_time = QLabel()
        self.preview_time.setFont(QFont("Malgun Gothic", 18, QFont.Bold))
        self.preview_date = QLabel()
        self.preview_date.setFont(QFont("Malgun Gothic", 10))
        # Time digit widths must not invalidate the scroll area's size hints.
        for label in (self.preview_time, self.preview_date):
            label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            label.setFixedHeight(QFontMetrics(label.font()).height())
        preview_layout.addWidget(self.preview_time)
        preview_layout.addWidget(self.preview_date)
        layout.addWidget(self.preview)
        self.labels = []
        self.add_segments(layout, "크기", "size", {"compact": "작게", "large": "크게"})
        self.add_segments(layout, "테마", "theme", {"light": "라이트", "dark": "다크", "aurora": "오로라"})
        self.add_segments(layout, "시간제", "hour_cycle", {12: "12시간", 24: "24시간"})
        self.add_segments(layout, "초 표시", "show_seconds", {True: "켜기", False: "끄기"})
        self.add_segments(layout, "정각 시보", "hourly_chime", {True: "켜기", False: "끄기"})
        chime_row = QHBoxLayout()
        self.chime_hint = QLabel("매 정각 짧게 두 번 · 시스템 음량 적용")
        chime_row.addWidget(self.chime_hint, 1)
        self.chime_preview_button = button("소리 들어보기", app.preview_chime, self)
        chime_row.addWidget(self.chime_preview_button)
        layout.addLayout(chime_row)
        self.add_combo(layout, "시간 포맷", "time_preset", TIME_PRESETS)
        self.add_combo(layout, "날짜 포맷", "date_preset", DATE_PRESETS)
        self.add_combo(layout, "표시 방식", "mode", {
            "auto": "자동 · 작업 표시줄 연동" if app.monitor.supported else "자동 연동 · Windows 전용",
            "always": "항상 위에 표시", "never": "일반 표시"})
        shortcut_row = self.row(layout, '전역 복원 키')
        self.shortcut_editor = ShortcutEditor(self)
        self.shortcut_editor.setKeySequence(QKeySequence(app.preferences.recovery_shortcut))
        shortcut_row.addWidget(self.shortcut_editor, 1)
        self.shortcut_apply = button('적용', self.apply_shortcut, self)
        shortcut_row.addWidget(self.shortcut_apply)
        self.shortcut_disable = button('사용 안 함', lambda: app.set_preference('recovery_shortcut', ''), self)
        shortcut_row.addWidget(self.shortcut_disable)
        self.hotkey_hint = QLabel('두 단계는 1초 안에 이어 누르세요. 키 입력 후 적용을 누르세요.')
        self.hotkey_hint.setWordWrap(True)
        layout.addWidget(self.hotkey_hint)
        self.hotkey_status = QLabel()
        self.hotkey_status.setWordWrap(True)
        layout.addWidget(self.hotkey_status)
        for control in (self.shortcut_editor, self.shortcut_apply, self.shortcut_disable):
            control.setEnabled(app.hotkey.supported)
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        self.hint = QLabel("Ctrl+, 설정 열기/닫기  ·  Esc 닫기")
        layout.addWidget(self.hint)
        footer = QHBoxLayout()
        footer.addWidget(button("기본값 복원", app.restore_defaults, self))
        footer.addStretch()
        footer.addWidget(button("닫기", self.close, self))
        layout.addLayout(footer)
        self.refresh()
        bounds = app.root.screen().availableGeometry()
        self.body.adjustSize()
        content_height = self.body.sizeHint().height()
        panel_height = min(content_height, bounds.height() - 16)
        self.scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOn if content_height > panel_height else Qt.ScrollBarAlwaysOff)
        self.setFixedSize(max(450, self.body.sizeHint().width() + 16), panel_height)
        x = max(bounds.left(), min(app.root.x() - self.width() - 12, bounds.right() - self.width()))
        y = max(bounds.top(), min(app.root.y(), bounds.bottom() - self.height()))
        self.move(x, y)
        self.show()
        self.activateWindow()
        self.controls["size"][0].setFocus()

    def resume_shortcuts(self):
        if self.app.closing:
            return
        self.app.hotkey.resume()
        for shortcut in self.app.shortcuts:
            shortcut.setEnabled(True)
        self.update_hotkey_status()

    def apply_shortcut(self):
        text = self.shortcut_editor.keySequence().toString(QKeySequence.PortableText)
        try:
            parse_shortcut(text)
        except ValueError as error:
            self.hotkey_status.setText(str(error))
            return
        if text == self.app.preferences.recovery_shortcut:
            self.app.hotkey.configure(text)
            self.update_hotkey_status()
        else:
            self.app.set_preference('recovery_shortcut', text)

    def update_hotkey_status(self):
        self.hotkey_status.setText(self.app.hotkey.status)

    def row(self, layout, text):
        row = QHBoxLayout()
        row.setSpacing(16)
        label = QLabel(text)
        label.setFixedWidth(78)
        row.addWidget(label)
        self.labels.append(label)
        layout.addLayout(row)
        return row

    def add_segments(self, layout, text, name, choices):
        row = self.row(layout, text)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self.groups.append(group)
        self.controls[name] = []
        for value, label in choices.items():
            control = button(label, lambda checked=False, n=name, v=value: self.app.set_preference(n, v), self)
            control.setCheckable(True)
            control.setProperty("segment", True)
            control.setMinimumHeight(34)
            control.setProperty("value", value)
            group.addButton(control)
            row.addWidget(control, 1)
            self.controls[name].append(control)

    def add_combo(self, layout, text, name, choices):
        row = self.row(layout, text)
        combo = ClockComboBox(self)
        combo.setView(QListView())
        combo.setMinimumHeight(38)
        combo.setMinimumWidth(270)
        for value, label in choices.items():
            combo.addItem(label, value)
        combo.currentIndexChanged.connect(lambda index, n=name, c=combo: self.app.set_preference(n, c.itemData(index)))
        row.addWidget(combo, 1)
        self.controls[name] = combo

    def refresh(self):
        colors = self.app.colors
        theme_changed = self.applied_theme != self.app.preferences.theme
        if theme_changed:
            self.apply_theme(colors)
            self.applied_theme = self.app.preferences.theme
        self.sync_controls(theme_changed)
        self.update_preview(datetime.now().astimezone())

    def apply_theme(self, colors):
        self.apply_colors(colors)
        self.setStyleSheet(self.styleSheet() + f"""
            QScrollArea#settingsScroll, QWidget#settingsBody {{ background: transparent; }}
            QLineEdit {{ background: {colors['panel']}; color: {colors['fg']};
                         border: 1px solid {colors['border']}; border-radius: 7px; padding: 6px; }}
            QFrame#preview {{ background: {colors['panel']}; border: 1px solid {colors['border']}; border-radius: 12px; }}
            QPushButton[segment="true"] {{ background: {colors['control']}; border-radius: 9px; padding: 6px 12px; }}
            QPushButton[segment="true"]:hover {{ background: {colors['hover']}; }}
            QPushButton[segment="true"]:checked {{ color: {colors['accent']}; background: {colors['selected']}; }}
            QPushButton[segment="true"]:focus {{ border: 1px solid {colors['accent']}; }}
            QComboBox {{ background: {colors['panel']}; color: {colors['fg']}; border: 1px solid {colors['border']};
                         border-radius: 9px; padding: 8px 12px; padding-right: 28px; }}
            QComboBox:hover {{ border-color: {colors['subtle']}; }}
            QComboBox:focus {{ border-color: {colors['accent']}; }}
            QComboBox::drop-down {{ background: transparent; border: none; width: 28px; }}
            QComboBox::down-arrow {{ image: none; border: none; width: 0; height: 0; }}
            QComboBox QAbstractItemView {{ background: {colors['panel']}; color: {colors['fg']};
                border: 1px solid {colors['border']}; border-radius: 8px; padding: 5px;
                selection-background-color: {colors['selected']}; selection-color: {colors['accent']}; outline: none; }}
            QComboBox QAbstractItemView::item {{ min-height: 32px; padding-left: 8px; border-radius: 5px; }}
            QScrollBar:vertical {{ background: {colors['control']}; width: 10px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {colors['subtle']}; border-radius: 4px; min-height: 24px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        """)
        for label in self.labels + [self.description, self.preview_date, self.hint, self.chime_hint, self.hotkey_hint, self.hotkey_status]:
            label.setStyleSheet(f"color: {colors['muted']};")
        self.status_label.setStyleSheet(f"color: {colors['accent']};")

    def sync_controls(self, theme_changed):
        colors = self.app.colors
        for name, controls in self.controls.items():
            value = getattr(self.app.preferences, name)
            if isinstance(controls, list):
                for control in controls:
                    blocker = QSignalBlocker(control)
                    control.setChecked(control.property("value") == value)
                    del blocker
            else:
                if theme_changed:
                    palette = controls.palette()
                    for role, color in ((QPalette.Window, colors['panel']), (QPalette.Base, colors['panel']),
                                        (QPalette.Button, colors['panel']), (QPalette.Text, colors['fg']),
                                        (QPalette.WindowText, colors['fg']), (QPalette.ButtonText, colors['fg']),
                                        (QPalette.Highlight, colors['selected']), (QPalette.HighlightedText, colors['fg'])):
                        palette.setColor(role, QColor(color))
                    controls.setPalette(palette)
                    controls.view().setPalette(palette)
                    controls.view().viewport().setPalette(palette)
                    controls.view().viewport().setAutoFillBackground(True)
                    controls.arrow_color = colors["muted"]
                    controls.update()
                    controls.prepare_popup()
                blocker = QSignalBlocker(controls)
                controls.setCurrentIndex(controls.findData(value))
                del blocker
        self.status_label.setText(self.app.status)
        if not self.shortcut_editor.hasFocus():
            self.shortcut_editor.setKeySequence(QKeySequence(self.app.preferences.recovery_shortcut))
        self.update_hotkey_status()

    def update_preview(self, now):
        clock = format_clock(now, self.app.preferences)
        if self.preview_time.text() != clock.time:
            self.preview_time.setText(clock.time)
        if self.preview_date.text() != clock.date:
            self.preview_date.setText(clock.date)

    def closeEvent(self, event):
        self.resume_shortcuts()
        if self.app.settings_panel is self:
            self.app.settings_panel = None
        super().closeEvent(event)
