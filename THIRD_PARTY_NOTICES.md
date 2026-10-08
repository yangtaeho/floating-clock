# 배포판의 외부 구성 요소

Floating Clock의 직접 작성한 코드·아이콘·WAV에는 루트 LICENSE의 PolyForm Noncommercial 1.0.0이 적용됩니다. 다음 외부 구성 요소에는 해당 프로젝트의 라이선스가 별도로 적용됩니다.

- CPython 3.12: Python Software Foundation License. https://docs.python.org/3/license.html
- PySide6 / Shiboken6 / Qt 6.10.3: LGPLv3 및 관련 Qt 라이선스·예외. https://doc.qt.io/qtforpython-6/licenses.html / https://www.qt.io/licensing/open-source-lgpl-obligations
- PyInstaller 6.22.0: GPLv2와 배포된 실행 파일에 대한 예외. https://pyinstaller.org/en/stable/license.html

배포판의 third-party-licenses 폴더에 설치된 Python·PySide6·Shiboken6의 라이선스 원문을 함께 제공합니다. 소스와 빌드 스크립트는 https://github.com/yangtaeho/floating-clock 에 공개됩니다. 해당 릴리스 태그를 체크아웃하고 requirements.txt의 PySide6 버전을 원하는 호환 버전으로 교체한 뒤 제공된 OS별 빌드 스크립트를 실행하면 수정된 Qt/PySide6 라이브러리로 배포판을 다시 만들 수 있습니다. 라이브러리 수정 디버깅을 위한 역공학을 금지하지 않습니다.

Qt/PySide6 6.10.3의 해당 소스: https://download.qt.io/archive/qt/6.10/6.10.3/ 와 https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.10.3 . CPython 3.12 소스와 라이선스: https://github.com/python/cpython/tree/3.12 . LGPL 라이브러리의 원래 권리와 조건은 프로젝트의 비상업 라이선스로 제한하지 않습니다.
