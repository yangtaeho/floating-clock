"""Qt system tray / macOS menu bar entry, with explicit visibility actions."""
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from app_metadata import APP_NAME, VERSION, ASSETS


class TrayAdapter:
    @staticmethod
    def available():
        return QSystemTrayIcon.isSystemTrayAvailable()

    def __init__(self, app):
        self.app = app
        self.icon = QSystemTrayIcon(QIcon(str(ASSETS / 'icon.png')), app.root)
        self.icon.setToolTip(f'{APP_NAME} {VERSION}\n클릭: 시계 앞으로 가져오기')
        self.menu = QMenu()
        self.restore = self.menu.addAction('시계 앞으로 가져오기')
        self.restore.triggered.connect(self.show_clock)
        self.visibility = self.menu.addAction('시계 숨기기')
        self.visibility.triggered.connect(self.toggle_clock)
        self.reset = self.menu.addAction('주 화면으로 위치 초기화')
        self.reset.triggered.connect(self.reset_position)
        self.menu.addSeparator()
        self.settings = self.menu.addAction('설정…')
        self.settings.triggered.connect(self.show_settings)
        self.about = self.menu.addAction('프로그램 정보… (F1)')
        self.about.triggered.connect(app.show_about)
        self.menu.addSeparator()
        self.quit = self.menu.addAction('종료')
        self.quit.triggered.connect(app.close)
        self.menu.aboutToShow.connect(self.update_menu)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self.activate)
        self.icon.show()

    def update_menu(self):
        self.visibility.setText('시계 숨기기' if self.app.root.isVisible() else '시계 표시')

    def show_clock(self):
        self.app.show_clock()
        self.update_menu()

    def reset_position(self):
        self.app.reset_position()
        self.show_clock()

    def toggle_clock(self):
        if self.app.root.isVisible():
            self.app.hide_clock()
        else:
            self.show_clock()
        self.update_menu()

    def show_settings(self):
        self.show_clock()
        if self.app.settings_panel:
            self.app.settings_panel.raise_()
            self.app.settings_panel.activateWindow()
        else:
            self.app.toggle_settings()

    def activate(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_clock()

    def close(self):
        self.icon.hide()
        self.menu.close()
