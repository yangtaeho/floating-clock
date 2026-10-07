"""Stable Qt preferences panel: no widget recreation during changes."""
from datetime import datetime
from PySide6.QtCore import Qt, QSignalBlocker, QPointF
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QPainter, QPen, QColor, QPolygonF
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QComboBox,
                               QPushButton, QButtonGroup, QFrame, QListView)
from clock_core import TIME_PRESETS, DATE_PRESETS, format_clock
from ui_components import RoundedWindow, button


class ClockComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.arrow_color = "#718094"

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(self.arrow_color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        x, y = self.width() - 18, self.height() / 2
        painter.drawPolyline(QPolygonF([QPointF(x - 4, y - 2), QPointF(x, y + 2), QPointF(x + 4, y - 2)]))


class SettingsPanel(RoundedWindow):
    def __init__(self, app):
        super().__init__(app.root, radius=18)
        self.app = app
        self.setWindowTitle("시계 설정")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.controls = {}
        self.groups = []
        layout = QVBoxLayout(self)
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
        preview_layout.addWidget(self.preview_time)
        preview_layout.addWidget(self.preview_date)
        layout.addWidget(self.preview)
        self.labels = []
        self.add_segments(layout, "크기", "size", {"compact": "작게", "large": "크게"})
        self.add_segments(layout, "테마", "theme", {"light": "라이트", "dark": "다크"})
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
        self.adjustSize()
        self.setFixedSize(max(450, self.sizeHint().width()), self.sizeHint().height())
        bounds = app.root.screen().availableGeometry()
        x = max(bounds.left(), min(app.root.x() - self.width() - 12, bounds.right() - self.width()))
        y = max(bounds.top(), min(app.root.y(), bounds.bottom() - self.height()))
        self.move(x, y)
        self.shortcuts = []
        for key, callback in (("Ctrl+,", app.toggle_settings), ("Ctrl+Shift+S", app.toggle_settings),
                              ("Meta+,", app.toggle_settings), ("Escape", self.close), ("Ctrl+Q", app.close)):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        self.show()
        self.activateWindow()
        self.controls["size"][0].setFocus()

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
        self.apply_colors(colors)
        self.setStyleSheet(self.styleSheet() + f"""
            QFrame#preview {{ background: {colors['panel']}; border: 1px solid {colors['border']}; border-radius: 12px; }}
            QPushButton[segment="true"] {{ background: {colors['control']}; border-radius: 9px; padding: 6px 12px; }}
            QPushButton[segment="true"]:hover {{ background: {colors['hover']}; }}
            QPushButton[segment="true"]:checked {{ color: {colors['accent']}; background: {colors['selected']}; }}
            QPushButton[segment="true"]:focus {{ border: 1px solid {colors['accent']}; }}
            QComboBox {{ background: {colors['panel']}; color: {colors['fg']}; border: 1px solid {colors['border']};
                         border-radius: 9px; padding: 8px 12px; padding-right: 28px; }}
            QComboBox:hover {{ border-color: {colors['subtle']}; }}
            QComboBox:focus {{ border-color: {colors['accent']}; }}
            QComboBox::drop-down {{ border: none; width: 28px; }}
            QComboBox::down-arrow {{ image: none; border: none; width: 0; height: 0; }}
            QComboBox QAbstractItemView {{ background: {colors['panel']}; color: {colors['fg']};
                border: 1px solid {colors['border']}; border-radius: 8px; padding: 5px;
                selection-background-color: {colors['selected']}; selection-color: {colors['accent']}; outline: none; }}
            QComboBox QAbstractItemView::item {{ min-height: 32px; padding-left: 8px; border-radius: 5px; }}
        """)
        for label in self.labels + [self.description, self.preview_date, self.hint, self.chime_hint]:
            label.setStyleSheet(f"color: {colors['muted']};")
        self.status_label.setStyleSheet(f"color: {colors['accent']};")
        for name, controls in self.controls.items():
            value = getattr(self.app.preferences, name)
            if isinstance(controls, list):
                for control in controls:
                    blocker = QSignalBlocker(control)
                    control.setChecked(control.property("value") == value)
                    del blocker
            else:
                controls.arrow_color = colors["muted"]
                controls.update()
                blocker = QSignalBlocker(controls)
                controls.setCurrentIndex(controls.findData(value))
                del blocker
        self.status_label.setText(self.app.status)
        self.update_preview(datetime.now().astimezone())

    def update_preview(self, now):
        clock = format_clock(now, self.app.preferences)
        self.preview_time.setText(clock.time)
        self.preview_date.setText(clock.date)

    def closeEvent(self, event):
        if self.app.settings_panel is self:
            self.app.settings_panel = None
        super().closeEvent(event)
