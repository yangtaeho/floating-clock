"""A single, themed help and product information window."""
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap, QKeySequence, QShortcut
from PySide6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout
from app_metadata import APP_NAME, VERSION, AUTHOR, ASSETS, GITHUB_URL
from ui_components import RoundedWindow, button


class AboutPanel(RoundedWindow):
    def __init__(self, app):
        super().__init__(app.root, flags=app.utility_flags, radius=18)
        self.app = app
        self.setWindowTitle("프로그램 정보 · " + APP_NAME)
        self.setAttribute(Qt.WA_DeleteOnClose)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(16)
        heading = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(QPixmap(str(ASSETS / "icon.png")).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        heading.addWidget(icon)
        identity = QVBoxLayout()
        title = QLabel(APP_NAME)
        title.setFont(QFont("Malgun Gothic", 19, QFont.Bold))
        identity.addWidget(title)
        self.version_label = QLabel(f"버전 {VERSION}  ·  제작 {AUTHOR}")
        identity.addWidget(self.version_label)
        heading.addLayout(identity, 1)
        close = button("×", self.close, self)
        close.setFixedSize(30, 30)
        heading.addWidget(close, 0, Qt.AlignTop)
        layout.addLayout(heading)
        summary = QLabel("언제든 시간을 확인하는 작은 데스크톱 시계")
        summary.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        layout.addWidget(summary)
        settings_key = "Cmd+," if sys.platform == "darwin" else "Ctrl+,"
        tray_name = "메뉴 막대 아이콘" if sys.platform == "darwin" else "트레이 아이콘"
        recovery_key = ("Ctrl+Alt+C  다른 앱에서도 시계 앞으로 가져오기\n" if app.hotkey.registered else
                        "Ctrl+Alt+C  사용 불가 (다른 앱이 사용 중) · 트레이로 복원\n") if sys.platform == 'win32' else ''
        help_text = QLabel(
            "시계를 드래그하면 위치를 옮길 수 있습니다.\n"
            "우클릭 메뉴에서 표시와 설정을 바꿀 수 있습니다.\n"
            "매 정각 짧게 두 번 울립니다. 설정에서 끌 수 있습니다.\n\n"
            f"{settings_key}  설정 열기 / 닫기\n"
            "F1  프로그램 정보와 사용법\n"
            "Esc  열린 메뉴 / 패널 닫기 · 시계만 있으면 종료 확인\n"
            "Ctrl+Q  프로그램 종료 확인\n"
            + recovery_key +
            f"{tray_name} 클릭  숨김 / 일반 표시 시계를 앞으로 가져오기\n"
            "아이콘: 설정 · 도움말 · 트레이로 숨기기 · 종료\n"
            "작은 시계에는 숨기기 · 종료 아이콘이 있습니다.\n"
            "모니터 연결이 바뀌면 보이는 화면 안으로 자동 이동합니다.\n\n"
            "인터넷 연결 없이 동작하며 외부로 데이터를 보내지 않습니다.\n"
            "설정은 이 기기에 저장됩니다."
        )
        help_text.setWordWrap(True)
        help_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(help_text)
        self.muted = [self.version_label, help_text]
        self.github_link = QLabel(f'<a href="{GITHUB_URL}">GitHub · 소스와 다운로드</a> &nbsp; '
                                  f'<a href="{GITHUB_URL}/issues">버그 신고 · 기능 제안</a>')
        self.github_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.github_link.setOpenExternalLinks(True)
        layout.addWidget(self.github_link)
        license_label = QLabel('비상업적 사용·수정·배포 가능 · PolyForm Noncommercial 1.0.0')
        license_label.setWordWrap(True)
        layout.addWidget(license_label)
        self.muted.append(license_label)
        footer = QHBoxLayout()
        footer.addStretch()
        self.close_button = button("닫기", self.close, self)
        footer.addWidget(self.close_button)
        layout.addLayout(footer)
        self.refresh()
        self.setFixedWidth(510)
        self.adjustSize()
        bounds = app.root.screen().availableGeometry()
        self.move(max(bounds.left(), min(app.root.x() - self.width() - 12, bounds.right() - self.width() + 1)),
                  max(bounds.top(), min(app.root.y(), bounds.bottom() - self.height() + 1)))
        self.show()
        self.activateWindow()
        self.close_button.setFocus()

    def refresh(self):
        self.apply_colors(self.app.colors)
        for label in self.muted:
            label.setStyleSheet(f"color: {self.app.colors['muted']};")

    def closeEvent(self, event):
        if self.app.about_panel is self:
            self.app.about_panel = None
        super().closeEvent(event)
