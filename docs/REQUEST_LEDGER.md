# Floating Clock 요청·설계 누적 기록

기록 기준일: 2026-10-07 (Asia/Seoul). 구현자는 작업 전에 이 파일과 루트 `AGENTS.md`를 읽는다.

## 상태 규약

`planned`: 분석·설계됨 / `implementing`: 구현 중 / `verified`: 구현과 해당 범위 검증 완료 / `blocked`: 외부 정보·환경이 필요함.
`verified`는 명시된 검증 범위에 대한 상태다. Mac 실기기 검증과 사용자 수용을 자동으로 의미하지 않는다.

## 현재 유효한 제품 결정

- **R010 공개·제품 기준**: 시계 저장소는 공개, 직접 작성한 코드/자산에 PolyForm Noncommercial 1.0.0 적용. v1.1.0 다중 모니터 복구·전역 복원·아이콘·종료 확인. 용량 축소는 R011 다음 버전.

- **R009 저장소 기준**: 학습은 `yangtaeho/study-vibe-coding-production-principles`, 시계는 `yangtaeho/floating-clock`. standalone 이름은 시계 저장소로 통합됨. 아래 R003/R006의 당시 원격 이름은 역사적 기록이다.


- 목적: Windows 작업 표시줄 자동 숨김 때문에 시간 확인이 불편할 때 사용하는 작은 데스크톱 시계.
- Windows 실행 파일 제공. Mac 포팅을 위해 로직·OS 어댑터·UI를 분리. R003부터 UI는 PySide6(Qt).
- Windows 자동 모드는 작업 표시줄의 **자동 숨기기 설정**을 감지한다. 실제 순간적인 펼침/접힘과는 구분한다.
- 새 설치에는 작은 크기, 라이트 테마, 12시간제, 초·정각 시보 켜짐, 콜론 시간, `yyyy년 MM월 dd일 (ddd)` 날짜를 적용. R004는 시보를 추가하고 R005는 R003 날짜 기본값을 대체.
- 사용자가 선택한 설정은 재실행 시 보존한다. R003은 이전 기본 날짜만 새 기본값으로 이전하고, v3 이후 선택값은 그대로 보존한다.
- 시계는 오프라인으로 동작하며 외부 서비스를 사용하지 않는다.
- R006부터 시계 전용 저장소에서 개발. R007 버전 1.0.0·고유 아이콘·F1 프로그램 정보, R008 Windows 시스템 트레이/작업표시줄 비표시 및 Mac 메뉴 막대 유틸리티. 원본 학습 저장소는 분리 전 상태로 보존.
- 정각 시보는 짧은 두 음. 설정에서 켜기/끄기·미리 듣기. 실행 직후나 절전 복귀·시간 변경의 지난 시보는 재생하지 않는다.

## R001 — 최초 시계 제작

요청일: 2026-10-07. 상태: **verified (Windows 기본 구현)**.

### 원문 의도와 요구

시분초·연월일을 표시하는 Windows 프로그램. 코어 로직은 플랫폼 독립적으로 구성하여 추후 Mac 포팅 가능. Windows에서 작업 표시줄 숨기기를 감지하면 항상 위에 표시.

### 분석과 설계

- Python 표준 라이브러리 Tk로 데스크톱 UI 구성. 실행에 외부 패키지 불필요.
- `clock_core.py`: 시간·날짜 문자열, 갱신 간격, topmost 판단.
- `platform_adapter.py`: `SHAppBarMessage(ABM_GETSTATE)`의 `ABS_AUTOHIDE` 비트를 1초마다 조회. Explorer 중단 시 마지막 상태 유지.
- `main.py`: 테두리 없는 창, 드래그, 우클릭, 닫기, 실제 시각 재조회로 초 갱신.
- `settings.py`: 사용자별 위치·표시 방식 저장, 임시 파일 후 교체.
- PyInstaller로 Python 미설치 PC에서 실행할 Windows EXE 생성. Mac 빌드 스크립트 제공.
- 초기 기본값은 큰 화면·다크·24시간제. **R002에서 대체됨**.

### 상태와 증거

| ID | 항목 | 상태 | 검증/한계 |
|---|---|---|---|
| R001-01 | 시분초·연월일·요일 | verified | 윤년·연도 변경 테스트, 실제 초 갱신 |
| R001-02 | 플랫폼 독립 코어 | verified | OS/UI import 없는 코어, 비Windows 어댑터 분기 테스트 |
| R001-03 | Windows 자동 숨김 → 항상 위 | verified | Shell 실제 상태 조회, 비트·정책 테스트, 실제 창 topmost 변경. 실제 설정 토글은 별도 |
| R001-04 | 드래그·메뉴·설정 저장 | verified | 실제 UI 스모크 및 저장/손상 복구 테스트 |
| R001-05 | Windows EXE 및 Mac 빌드 준비 | verified | Windows EXE 실행 확인. Mac 실기기·서명·공증은 미검증 |

이전 검증: `python -m unittest -v` 6개 통과, `python smoke_ui.py` 통과, Windows EXE 실제 창 확인. 하단 문구 잘림을 고쳐 높이를 180px로 조정함.

## R002 — 기록 기반 작업·Git 관리와 작은 시계 개선

요청일: 2026-10-07. 상태: **verified (Windows 및 로컬 Git 범위)**.

### 요청 분석

1. 작업 폴더를 로컬 Git 저장소로 만들고 커밋·푸시.
2. 최초 요청과 후속 요청의 분석·설계를 누적하고 각 상태를 구현 기준으로 사용.
3. 모서리를 둥글게. 작업 표시줄 시계에 가까운 작은 크기 추가 및 기본 적용.
4. 작은 크기에는 제목·설정 상태를 숨기고 은은한 닫기 버튼만 표시.
5. 라이트 테마 추가 및 기본 적용. 기존 큰 크기와 다크 테마는 선택 가능.
6. 12/24시간 토글, 기본 12시간. 시간 포맷 프리셋. 초 토글, 기본 켜짐.
7. 날짜 포맷 프리셋, 기본 `yyyy년 MM월 dd일 (dddd)`.
8. 별도 설정 패널과 일반적 설정 단축키로 토글.
9. 컨텍스트 메뉴를 시계 테마에 맞는 UI로 개선.

### 결정한 설계

- 기존 Python/Tk 구조 유지. 설정을 검증된 불변 `ClockPreferences`로 코어에서 관리.
- 작은 화면은 2줄(시간/날짜), 높이 약 60px를 시작값으로 사용. 글꼴 측정 및 DPI에 따라 크기를 계산해 잘림 방지. 큰 화면은 제목·상태 표시를 유지.
- Windows 창 영역을 둥근 사각형으로 자르는 OS 어댑터 사용. 공통 UI는 둥근 표면으로 그리며 Mac 경로는 안전한 폴백 제공.
- 12시간 표시는 오전/오후로 구분하고 자정·정오를 12시로 표시. 24시간제에는 오전/오후 숨김.
- 시간 프리셋: 콜론(기본), 한글 단위, 점 구분. 초 토글은 모든 프리셋에 적용.
- 날짜 프리셋: 한글 전체 요일(기본), 한글 짧은 날짜, ISO 날짜+요일, 슬래시 날짜.
- 설정 패널에서 크기·테마·시간제·초·시간/날짜 프리셋·항상 위 방식을 편집하고 즉시 적용/저장. 예시와 기본값 복원 제공.
- Windows/Linux `Ctrl+,`, macOS `Cmd+,`로 설정 토글. 보조 `Ctrl+Shift+S`. 앱이 포커스를 받은 상태의 단축키이며 전역 핫키는 아님.
- 컨텍스트 메뉴는 테마별 직접 그린 작은 팝업, 호버 및 키보드 탐색 제공. 밖 클릭/Esc로 닫힘.
- 기존 설정 스키마에는 새 기본값을 보충하고 기존 위치·topmost 모드는 보존. 신규 스키마에서는 선택값 보존.
- Git 루트는 현재 작업 폴더. 기존 HTML도 원본 그대로 추적. `.venv`, 산출 EXE, 빌드 중간 파일, 사용자 설정은 제외.

### 구현 항목과 수용 기준

| ID | 항목 | 상태 | 수용 기준 |
|---|---|---|---|
| R002-01 | 누적 기록과 작업 규칙 | verified | 최초/현재 요청, 상태·설계·검증 기록 및 AGENTS 지침 존재 |
| R002-02 | 로컬 Git·커밋 | verified | `main`에 최초 커밋 `2dd3004` 및 이번 구현·검증 기록을 포함하는 후속 커밋. 사용자 수정 지시로 원격 푸시는 범위에서 제외 |
| R002-03 | 둥근 모서리 | verified | Windows 네이티브 영역 적용 성공, 실제 창/메뉴 PNG 확인 |
| R002-04 | 기본 작은 크기 | verified | 기본 220×60px(현재 DPI), 제목·상태 없음, × 표시. 192개 조합 잘림 검사 |
| R002-05 | 기본 라이트·선택 다크 | verified | 시계·메뉴·패널 양쪽 테마 PNG 확인, 설정 파일 왕복 테스트 |
| R002-06 | 12/24·초·시간 프리셋 | verified | 자정/정오/23시 및 각 프리셋×초 조합 테스트 |
| R002-07 | 날짜 프리셋 | verified | 기본 전체 요일, 윤년·연도 전환 및 4개 프리셋 테스트 |
| R002-08 | 설정 패널·단축키 | verified | 실제 Ctrl+, 열기/닫기, 패널 제어·예시·복원, 저장 내용·재로딩 검증 |
| R002-09 | 컨텍스트 메뉴 | verified | 테마·호버·키보드 탐색, 외부 클릭 및 열린 메뉴와 함께 종료 검사 |
| R002-10 | 통합 검증·Windows EXE | verified | 로직 12개, UI 조합 192개 및 상호작용 통과, 새 EXE 실행·PNG 확인 |

### 검증 및 전달 기록

사용자가 로컬 Git부터 진행하도록 범위를 수정했다. `https://github.com/yangtaeho`는 계정 주소로 보관하며 원격 저장소 URL로 사용하지 않는다. 원격 푸시는 이번 작업에서 제외하고 저장소가 정해지면 진행한다. 작성자 정보는 이 저장소에만 `Codex <codex@localhost>`를 사용한다. 사용자 전역 Git 설정은 변경하지 않았다.

- `python -m unittest -v`: 12개 통과. 12/24 자정·정오, 윤년, 모든 포맷, 초 토글, 손상·v1 설정 보충·v2 파일 왕복, Shell 및 비Windows 분기 검증.
- `python smoke_ui.py --capture`: 192개 조합과 기본값, 실제 Ctrl+, 설정 토글, 패널 선택·프리셋 이벤트, 저장 데이터, 네이티브 topmost와 둥근 영역, 메뉴 키보드·밖 클릭, 초 갱신, 열린 메뉴 종료 검사 통과.
- `previews/compact-light.png`, `large-dark.png`, `settings-light.png`, `settings-dark.png`, `menu-light.png`, `menu-dark.png`의 텍스트·레이아웃을 직접 확인.
- PyInstaller Windows 빌드 성공. 새 `dist/FloatingClock.exe`를 실행해 응답하는 실제 창과 `previews/packaged-windows.png`를 확인. 현재 수정 버전 시계 실행 중.
- 검증 중 네이티브 둥근 영역 적용이 Configure를 다시 발생시키는 문제를 수정: 같은 창/크기/반경에는 재적용하지 않는다. 캐시는 창 객체 수명에 묶어 네이티브 핸들 재사용을 방지한다.
- 기존 루트 HTML 예제는 변경하지 않았다. 실행 EXE는 로컬 제공하고 Git에는 소스·빌드 스크립트·검증 이미지만 포함한다.
- 남은 검증 한계: Mac 실기기, 실제 자동 숨김 설정 토글, 다중 모니터 및 다양한 DPI. 이 한계를 완료 여부와 구분해서 유지한다.

## 다음 요청 기록 형식

R003 이후에도 `요청일 / 요청 분석 / 결정한 설계 / 항목별 ID·상태·수용 기준 / 검증 및 전달 기록`을 추가한다. 상단 현재 유효한 결정도 함께 갱신한다.

## R003 — 수정 요청 #2: 포커스·렌더링 개선 및 GitHub 업로드

요청일: 2026-10-07. 상태: **verified (Windows 및 GitHub 업로드 범위)**.

### 요청 분석

- 설정 변경 시 포커스가 빼앗겨 선택 상자 조작이 어려운 문제 해결.
- `yyyy 년 MM 월 dd 일 (ddd)` 날짜 프리셋 추가 및 기본값 지정.
- 첨부 스크린샷의 끊어진 라운드 테두리·다크 계단 현상 개선. 작은/큰 크기 모두 적용.
- 설정창 헤더도 테마를 따르게 하고 선택 상자·토글을 다듬기.
- `yangtaeho` GitHub 계정에 적절한 이름의 저장소를 생성하고 업로드. 필요한 도구 설치 및 인증 설정 허용.

### 원인 및 설계 결정

- 기존 Tk 구현은 설정마다 시계의 위젯·네이티브 영역을 재생성하고 topmost를 반복 갱신하며, 테마 변경 시 패널도 다시 만들어 포커스 유지가 불안정하다.
- Tk Canvas 곡선과 Win32 정수 픽셀 영역이 서로 다른 경계를 사용하여 절단·점선·계단 모양이 발생한다. 단순 색 변경으로는 부분 투명도와 앤티앨리어싱을 해결할 수 없다.
- 공통 코어·사용자 설정·Shell 감지는 유지하고 UI를 PySide6(Qt)로 전환. UI 품질에 필요한 단일 런타임 의존성이며 프로젝트 `.venv`에만 설치한다. Python 미설치용 EXE도 갱신한다.
- 투명 창에서 QPainter 앤티앨리어싱으로 배경·경계를 한 번에 그린다. 정수 영역 자르기와 Tk Canvas 경계는 제거한다.
- 설정 위젯을 유지한 채 값·스타일만 갱신한다. 설정 적용·1초 타이머가 설정창 활성 상태와 선택 상자 포커스를 바꾸지 않도록 한다.
- Windows topmost는 `SetWindowPos`의 `SWP_NOACTIVATE`로 변경한다. 설정창은 동일한 테마의 직접 그린 드래그 가능한 헤더를 사용한다.
- 새 날짜 프리셋 예: `2026 년 10 월 07 일 (수)`. 기존 긴 요일 형식도 선택 가능. 이전 버전의 기본값 `korean_full`만 새 기본값으로 이전하고 다른 선택값은 보존. 새 설정 스키마 v3에서는 선택 보존.
- GitHub 저장소 이름 `floating-clock`, 기본 비공개. GitHub CLI를 사용하고 원격 이름 `origin`. 브라우저 로그인에 인간 인증이 필요하면 해당 단계만 요청하고 구현은 계속한다.
- 실행 파일·도구·자격 증명은 Git에 포함하지 않는다. 업로드는 사용자 요청에 따라 수행하며 임의 공개 전환은 하지 않는다.

### 구현 상태 및 수용 기준

| ID | 항목 | 상태 | 수용 기준 |
|---|---|---|---|
| R003-01 | 설정 포커스 안정화 | verified | 실제 설정 제어·드롭다운 키보드 선택 후 활성 창과 포커스 유지, 열린 목록에 1초 타이머 적용 |
| R003-02 | 공백 포함 짧은 요일 날짜 | verified | 새 기본 예시, 이전 기본값 이전 및 v3 명시적 선택 보존 테스트 |
| R003-03 | 부드러운 라운드 창 | verified | 작은/큰×라이트/다크 실제 PNG, 모서리 알파 0과 경계 0<알파<255 검사 |
| R003-04 | 테마 설정창과 컨트롤 | verified | 헤더 포함 전체 테마 PNG 확인, 유지되는 컨트롤·단축키·선택 상자 실제 조작 |
| R003-05 | GitHub 저장소·푸시 | verified | 기존 인증으로 비공개 `yangtaeho/floating-clock` 생성, main 푸시, 로컬/원격 커밋 일치 확인 |
| R003-06 | 통합 검증·EXE·문서 | verified | 로직 13개·Qt UI 240개 조합 통과, 새 Windows EXE 실제 렌더링·정상 종료·재실행, 문서 갱신 |

### 검증 및 전달 기록

작업 중. GitHub CLI의 MSI 설치가 1603으로 실패하여 프로젝트의 Git 제외 폴더에 공식 휴대용 배포판을 설치하는 방식으로 전환.

- `python -m unittest -v`(프로젝트 `.venv`): 13개 통과.
- `python smoke_ui.py --capture`(프로젝트 `.venv`): 실제 Qt 창의 240개 조합·부분 투명 경계·설정/목록 포커스·목록을 연 채 시간/Shell 타이머·실제 키보드 선택·NOACTIVATE topmost·단축키·메뉴·종료 검증 통과.
- 시계 4개 테마/크기 이미지와 라이트/다크 설정창·메뉴 이미지를 확인. 선택 상자 화살표는 QPainter로 부드럽게 그린 셰브론을 사용.
- Git Credential Manager의 기존 GitHub 인증으로 `yangtaeho` 계정을 확인. `gh auth login`은 기존 토큰에 CLI 기본 추가 범위를 요구하여 사용하지 않고, 기존 인증을 프로세스 환경에만 전달하여 필요한 저장소 API를 사용. 자격 증명 값은 파일/명령행/기록에 저장하지 않음. 새로운 OAuth 기기 인증은 취소했고 추가 권한은 부여하지 않음.
- 빌드 중 PATH의 타 프로그램 `icuuc.dll`이 Qt의 Windows ICU API와 호환되지 않아 QtCore 로드 실패. 진단 빌드에서 해당 DLL 제외 후 정상 실행 확인. `build_app.py`가 해당 ICU 및 데이터 DLL을 제외하여 같은 문제 재발 방지.
- 수정한 Windows 빌드의 `--verify-build`가 종료 코드 0으로 완료. `build/packaged-verification.json`에 실제 창 visible=true, 220×56 논리 픽셀, 새 날짜 형식이 기록됐으며 `previews/packaged-windows.png`로 실제 EXE 렌더링을 보관. 기존 사용자가 선택한 24시간제도 보존됨. 최종 시계 재실행.
- Mac 실기기·여러 DPI·다중 모니터 실사용은 여전히 미검증. 부분 투명 경계와 포커스 회귀는 현재 Windows PC(150% DPI)에서 검증.
- GitHub 저장소: `https://github.com/yangtaeho/floating-clock`, 비공개, 기본 브랜치 `main`, 로컬 원격 `origin`.
- 기능 커밋 `7df51d6bbdcebf5d334924df346ee7cdd62d5755`를 푸시했고 `git ls-remote origin refs/heads/main` 값과 로컬 HEAD가 일치했다. 이 완료 기록과 루트 README도 후속 커밋으로 전달한다.
- 새 OAuth 권한·공개 접근·전역 Git 설정 변경 없이 기존 계정 인증을 사용했다. GitHub CLI 휴대용 도구는 `.tools/`에 있고 Git에는 제외된다.

## R004 — 매 정각 두 번 울리는 시보

요청일: 2026-10-07. 상태: **verified (현재 Windows 환경)**.

### 요청 분석 및 설계

- 카시오 손목시계처럼 매 정각 짧고 높은 소리가 두 번 나는 시보 요청. 외부 녹음 대신 4,096Hz 두 음을 직접 합성한 WAV를 동봉한다.
- 기본값은 시보 켜짐. 설정창에 켜기/끄기와 `소리 들어보기`를 추가하고 선택을 저장한다. 기존 표시 설정은 유지한다.
- 플랫폼 독립적인 정각 판정은 벽시계와 단조 시간을 함께 사용한다. 정각 직전부터 연속 실행 중인 경우에만 울린다. 시작·절전 복귀·시간 점프에는 지난 시보를 재생하지 않는다. 동일 정각 중복을 억제한다.
- 표시되는 초를 꺼도 시보는 동작한다. Qt QSoundEffect의 비동기 재생으로 화면·설정 포커스를 유지하며 시스템 음량/음소거를 따른다.
- 소리는 80ms 두 음과 70ms 간격, 짧은 페이드로 클릭을 줄인다. 코어 판정, 공통 Qt 재생, WAV 자산을 분리하고 Windows/Mac 빌드에 함께 포함한다.
- 영향: clock_core.py, chime_core.py, chime_audio.py, main.py, settings_panel.py, build_app.py, 테스트 및 README. 설정 스키마 v3에 선택 필드를 보충한다.

### 구현 상태 및 수용 기준

| ID | 항목 | 상태 | 수용 기준 |
|---|---|---|---|
| R004-01 | 정각 판정 | verified | 정상/자정 경계, 중복, 끄기, 시작, 절전 및 시간 점프 테스트 |
| R004-02 | 삐빅 소리·설정 | verified | 두 음 WAV, 기본 켜짐·저장·미리 듣기, 실제 Qt 재생 상태 및 포커스 검증 |
| R004-03 | 빌드·문서·전달 | verified | UI 회귀·새 EXE의 소리 자산 로드, 실행 교체, 누계 갱신 및 커밋·푸시 |

### 검증 및 전달 기록

- 구현 전 설계 기록 완료. Mac 실제 오디오 장치 검증은 현재 Windows 작업 환경에서 수행할 수 없음.
- `python -m unittest -q`: 전체 23개 통과. 정각·자정·중복·비활성/다시 켜기·시작·절전·시간 점프·타이머 지연 및 WAV의 두 음/간격/주파수를 검증.
- `python smoke_ui.py --capture`: 기존 240개 표시 조합과 새 시보 토글·저장·미리 듣기 버튼의 포커스·설정창 화면 내 배치 검증 통과. 라이트/다크 설정창 이미지 확인.
- `python smoke_audio.py`: 현재 Windows 오디오 장치에서 Qt Ready → 재생 시작 → 정상 종료 확인. 꺼짐 상태에서 미리 듣기가 선택값을 바꾸지 않으며 포커스를 유지. 정각 타이머의 재생 호출 한 번도 검증. 귀로 들리는 음색에 대한 사용자 수용은 별도.
- UI 검증에서 네이티브 목록 종료가 부모 시계의 topmost 상태를 바꾸는 경우 발견. Windows 실제 스타일과 저장 정책이 어긋나면 기존 NOACTIVATE 방식으로 복구하도록 보강. 열린 설정창의 포커스와 always/never 실제 스타일 검사 통과.
- Windows EXE 빌드 성공, `--verify-build` 종료 코드 0. 실제 창 220×56, 시보 켜짐, WAV 자산 존재, Qt 오디오 Ready 및 새 날짜 확인. 기존 사용자 선택 24시간제 보존. 새 EXE 실행 중.
- Mac 소리 출력은 실기기 미검증. 공통 판정 및 Qt 재생 경로·동봉 자산은 Mac 빌드에도 적용됨.
- R004/R005 기능 커밋 `16639cf2d2a8c0c8d6a285b7b717f5549f7e4555`를 비공개 원격 main에 푸시했고 로컬/원격 커밋 일치를 확인. 완료 상태와 이 전달 기록은 후속 문서 커밋에 포함한다.

## R005 — 날짜 단위 앞 공백 제거

요청일: 2026-10-07. 상태: **verified**.

- 요청: R003의 `yyyy 년 MM 월 dd 일 (ddd)`를 `yyyy년 MM월 dd일 (ddd)`로 교체한다. 예: `2026년 10월 07일 (수)`.
- 설계: 기본 프리셋의 표시 문자열과 출력만 변경하고 저장 식별자는 유지하여 기존 선택도 즉시 새 형식을 사용한다. 다른 날짜 프리셋은 보존한다. R003 날짜 기본값을 대체한다.
- 영향: clock_core.py, 날짜 테스트, README 및 이미지. R004와 함께 구현·검증·전달한다.

| ID | 항목 | 상태 | 수용 기준 |
|---|---|---|---|
| R005-01 | 새 기본 형식·기존 선택 적용 | verified | 기본·이전 설정·윤년 날짜 출력 및 Qt/EXE의 새 날짜 확인 |

### 검증 및 전달 기록

- 구현 전 설계 기록 완료.
- 기본·윤년·연도 전환·기존 v3 선택 출력 검사와 전체 UI 검증 통과. 실제 EXE 날짜 `2026년 10월 07일 (수)` 확인. 날짜 문자열과 미리보기 이미지를 갱신.

## R006 — 시계 전용 저장소 분리와 독립 실행 배포판

요청일: 2026-10-07 (Asia/Seoul). 상태: **verified (Windows 실제 검증 및 macOS 네이티브 빌드 범위)**.

### 사용자 의도와 요구

현재 학습 저장소에서 시계 관련 내용만 별도 Git 저장소로 분리하고 AGENTS.md 등 작업 지침과 요청 기록을 이전한다. 사용자 GitHub에 업로드하고 Python 설치 없이 실행하는 Windows 및 macOS 배포판을 제공한다.

### 설계와 기본값

- 새 로컬 루트 `C:/dev/workspace-codex/floating-clock`, 새 비공개 원격 `yangtaeho/floating-clock-standalone`. 기존 `floating-clock` 원격과 학습 폴더는 보존한다.
- 추적된 `desktop-clock/` 파일을 새 저장소 루트로 이전. AGENTS.md 경로 조정, docs/REQUEST_LEDGER.md의 R001~R006 보존, 출처 커밋 기록. 학습 HTML과 인증/도구/설정/빌드 결과는 제외.
- R002의 혼합 Git 루트 정책을 새 시계 전용 저장소에 한해 대체한다. 기존 요청의 기능·기본값은 유지한다.
- 기존 이력에는 학습 HTML이 포함되어 있으므로 새 저장소는 시계만 담는 새 이력으로 시작한다. 원본 이력은 기존 저장소에 보존한다.
- GitHub Actions에서 Windows x64, macOS arm64 및 x64를 각 OS에서 빌드한다. 로직 검사와 패키지 실행 검증 후 ZIP/DMG 및 SHA-256을 제공하고 비공개 GitHub Release에 올린다.
- Mac 개발자 인증서가 없으므로 Apple 공인 서명/공증 없이 제공하며 실제 Mac 사용자 기기의 UI/오디오 수용은 미검증으로 기록한다.
- 영향 파일: 새 저장소 AGENTS.md, README.md, docs, 빌드·패키징 스크립트, GitHub Actions. 기존 학습 HTML 변경 없음.

### 수용 기준

| ID | 항목 | 상태 | 기준 |
|---|---|---|---|
| R006-01 | 소스와 지침 분리 | verified | 시계 소스·자산 해시 일치, HTML/환경/개인설정 미포함, 독립 Git 루트 |
| R006-02 | GitHub 전달 | verified | 비공개 새 원격 생성, main 푸시, 로컬/원격 HEAD 일치 |
| R006-03 | Windows 배포 | verified | 로직·실제 Qt 창·독립 EXE 실행 검증, ZIP과 체크섬 |
| R006-04 | Mac 배포 | verified | 두 아키텍처 실제 macOS 빌드 및 번들 실행 확인, DMG, 검증 한계 명시 |

### 검증 및 Git 전달

- 시계 코드/자산 28개 SHA-256 일치(README와 .gitignore는 구조에 맞춰 변경). 독립 Git 루트 확인, HTML/개인설정/환경/산출물 미포함 확인.
- 새 비공개 GitHub 저장소 생성. 최초 커밋 `6720fb50aa5b428207ffc74c3e0ebbb768105270`의 로컬/원격 HEAD 일치 확인. GitHub API로 사용자 계정과 이름/이메일을 확인하여 새 저장소 로컬 작성자로 적용. 전역 설정 변경 없음.
- `python -m unittest -v`: 23개 통과. `python smoke_ui.py`: Windows 실제 창 240개 조합·알파·포커스·목록·정책·단축키 통과. `python smoke_audio.py`: 현재 Windows 장치 Ready→재생→종료 및 정각 1회 호출 통과. 새 소스 경로에서 기존 동일 버전 프로젝트 환경으로 검사.
- 새 전용 `.venv`에서 `build-windows.ps1` 성공. `python package_release.py --platform windows-x64` 성공: 실제 EXE 실행/종료, 220×56 창 visible, 시보 WAV 및 Qt Ready. 기본값을 임시 사용자 환경에 격리해 검사하여 기존 설정을 보존. packaged-preview.png 직접 확인.
- Windows ZIP `FloatingClock-windows-x64.zip` 및 SHA-256 생성. 릴리스 업로드 준비 중.
- GitHub Actions 실행 `37639033191`: Apple Silicon 빌드 성공. Intel/Windows CI 진행 중. Mac은 offscreen 번들 실행과 이미지 렌더링 검사이며 실제 데스크톱 포커스·소리 출력·실기기 수용은 미검증.

## R007 — 배포용 아이콘·버전·프로그램 정보

요청일: 2026-10-07 (Asia/Seoul). 상태: **verified (Windows UI 및 두 OS 패키지 범위)**.

### 의도와 요구

사용자 추가 요청: 시계 배포판에 아이콘과 버전 정보, F1으로 여는 about 종류의 패널을 갖춘다. R006의 릴리스 발행을 이 요구까지 반영한 빌드 이후로 연기한다.

### 설계와 기본값

- 버전 `1.0.0`, 제품명 Floating Clock, 작성자 yangtaeho를 단일 메타데이터 모듈에서 관리한다.
- 기존 앱 색상과 어울리는 둥근 시계 아이콘을 코드로 직접 그린다. PNG(앱/정보창), 다중 크기 ICO(Windows), ICNS(macOS)를 동일 도안으로 생성하고 소스로 추적한다.
- F1, 우클릭 `프로그램 정보…` 및 설정창 F1에서 단일 정보창을 연다. 반복 호출은 같은 창 활성화. 테마 연동, 버전/작성자/사용법/단축키/오프라인 동작을 표시. Esc/닫기 버튼으로 정보창만 닫는다.
- Windows PE 제품/파일 버전과 회사/설명, macOS Info.plist 버전·식별자·아이콘을 빌드에 적용한다. 실행 파일 검사에서 정보창·아이콘·버전도 확인한다.
- 영향: app_metadata.py, about_panel.py, main.py, ui_components.py, settings_panel.py, assets, generate_icons.py, build_app.py, package_release.py, smoke_ui.py, README 및 누적 기록.

| ID | 항목 | 상태 | 수용 기준 |
|---|---|---|---|
| R007-01 | 아이콘·버전 메타데이터 | verified | 두 OS 패키지에 아이콘과 1.0.0 정보, 앱 창 아이콘 |
| R007-02 | 정보창과 접근 | verified | 실제 F1/우클릭/설정 F1·단일 창·Esc·테마·잘림·포커스 검증 |
| R007-03 | 최종 배포·전달 | verified | 새 Windows EXE/두 Mac DMG 재빌드 및 패키지 정보창 검증, 릴리스 업로드 |

### 검증 및 전달

설계 기록 완료. 구현 전.

## R008 — 시스템 트레이 상주

요청일: 2026-10-07 (Asia/Seoul). 상태: **verified (Windows 실제 트레이 및 macOS 번들 설정 범위)**.

### 의도와 설계

사용자 추가 요청: 작은 시계의 특성상 작업표시줄 대신 시스템 트레이로 접근하는 형태가 필요하다.

- Windows 기본값은 시스템 트레이 상주. 트레이 사용 가능 시 Qt Tool 창으로 작업표시줄 버튼을 없애고 시계는 계속 표시한다. 설정/정보창도 Tool 창을 사용한다.
- Mac은 메뉴 막대 아이콘으로 제공. 번들의 LSUIElement를 사용하여 Dock 공간을 차지하지 않는 유틸리티로 동작. Tool 창은 비활성 시에도 시계를 유지한다.
- 트레이 메뉴: 시계 표시/숨김, 설정, 프로그램 정보(F1), 종료. 아이콘 클릭/더블클릭은 숨겨진 시계를 복원. 숨긴 동안에도 정각 시보는 계속 실행한다. 마지막 창을 숨겨도 앱이 종료되지 않는다.
- 기존 ×/Esc(시계만 있을 때)/Ctrl+Q의 종료 동작은 유지하고 트레이 숨김은 별도 메뉴로 명시한다. 숨김은 저장하지 않아 재실행하면 시계를 표시한다.
- 트레이를 제공하지 않는 환경은 일반 창으로 폴백하여 접근 경로를 유지한다. 정보창·설정창에서 앱 종료하면 트레이도 제거한다.
- 영향: tray_adapter.py, main.py, about_panel.py, settings_panel.py, build_app.py, smoke_ui.py, README, 검증 기록.

| ID | 항목 | 상태 | 수용 기준 |
|---|---|---|---|
| R008-01 | 트레이와 작업표시줄 | verified | 실제 Windows 트레이 존재·Tool 플래그/작업표시줄 비표시, 트레이 없는 환경 폴백 |
| R008-02 | 메뉴·수명 | verified | 숨김/복원·설정·정보·종료, 타이머 유지·상주·중복 없는 복원·아이콘 제거 |
| R008-03 | 배포와 Mac 검증 한계 | verified | 최종 배포 재빌드, LSUIElement·메뉴 막대 설정 검사, 실기기 한계 명시 |

### 검증 및 전달

설계 기록 완료. 구현 전.

- R007/R008 Windows 소스 검증: 전체 로직 23개, UI 240개 조합과 실제 F1/우클릭/설정 F1, 단일 정보창 재사용, 라이트/다크 알파·버전 문자열·잘림·포커스, 트레이 메뉴·숨김 중 타이머 유지·클릭 복원·설정 재사용·종료·아이콘 제거 통과. Windows 네이티브 WS_EX_TOOLWINDOW와 WS_EX_APPWINDOW 비설정 확인. 트레이 없는 환경의 일반 창 폴백 검사 통과.
- `previews/about-light.png`, `about-dark.png`, `assets/icon.png` 직접 확인. 기존 오디오 실제 재생 검사 통과. Tool 창 전환 후 단축키 충돌을 발견하여 컨트롤러의 애플리케이션 범위 단축키 한 곳으로 통합하고 회귀 검사 통과. 이 단축키는 앱이 활성 상태일 때만 작동한다.
- 최종 R007/R008 배포의 두 Mac 빌드 및 메타데이터 검증은 진행 중.

- R007/R008 Windows 최종 EXE: build_app.py 및 package_release.py 성공. PE ProductName=Floating Clock, ProductVersion/FileVersion=1.0.0, CompanyName=yangtaeho 및 아이콘 리소스 검사 통과. 실행 정보 icon_loaded/about_visible/tray_available/tray_visible/tool_window 모두 true, 실제 정보창 이미지 직접 확인. 최종 Windows ZIP SHA-256은 `07e4912b1fe780a94bd4fa7c8bf95549d8ef83a5636300c9f8ec78c74c89e522`.

### R006~R008 최종 검증과 전달

- 최종 기능 커밋 `4db00813789ae609911afc3c5b273c0f8a868ef6`. GitHub Actions `37640515472`의 Windows x64, macOS arm64, macOS x64 모두 success. 각 OS에서 로직 23개·네이티브 패키징·실행/정보창/아이콘 검사 완료. Mac의 CFBundleShortVersionString/CFBundleVersion=1.0.0, 식별자 com.yangtaeho.floatingclock, LSUIElement=true, ICNS 자산 및 DMG 검증 통과.
- Mac 검증 이미지를 직접 확인(한국어 렌더링/정보창). offscreen 환경에는 트레이가 없어서 일반 창 폴백을 사용했다. **실제 Mac 메뉴 막대 클릭·Dock 부재·포커스·오디오 출력은 미검증**이다. Windows CI 오디오 장치는 Error 상태지만 현재 사용자 PC의 실제 재생은 Ready→재생→종료로 확인했다.
- 배포: https://github.com/yangtaeho/floating-clock-standalone/releases/tag/v1.0.0 . 비공개 저장소의 정식 릴리스에 Windows ZIP 및 두 Mac DMG와 각각 SHA-256 파일 총 6개 업로드. GitHub 자산 digest와 로컬 체크섬 일치 확인. 릴리스 태그는 최종 기능 커밋을 가리키며 이 완료 기록은 후속 문서 커밋에 전달한다.
- Windows ZIP SHA-256: 07e4912b1fe780a94bd4fa7c8bf95549d8ef83a5636300c9f8ec78c74c89e522.
- macOS arm64 DMG SHA-256: ef3ab89f6f18987df69de8fa54afd2870838b01629fe96b67e191a79ad89eb2e.
- macOS x64 DMG SHA-256: 1ca35c5369c78a89de6dd91b2275399eacef6c8be22627c193c6bb3ad628302a.
- Windows는 ZIP 압축 해제 후 EXE 실행. Mac은 DMG를 열고 앱을 Applications로 복사. Python/Qt 별도 설치 불필요. Mac 개발자 인증서 서명/공증 없음; 실행 차단 시 기기 보안 설정에서 해당 앱 허용 필요 가능. Mac 실기기 수용·이전 OS·다중 모니터 및 다양한 DPI는 남은 한계다.
- Git 전달: 소스와 지침·요청 기록·검증 이미지만 추적. 개인 설정/.venv/빌드 결과/인증 제외. 작성자와 원격은 확인된 yangtaeho 계정을 사용했고 전역 설정은 변경하지 않았다.

## R009 — 학습 저장소와 시계 저장소의 역할·이름 정정

요청일: 2026-10-08 (Asia/Seoul). 상태: **verified**.

### 사용자 의도와 요구

`desktop-clock` 외의 학습 파일은 한 저장소로, 시계 파일만 `floating-clock` 저장소로 관리한다. 잘못 추가된 `floating-clock-standalone`은 시계의 최종 기능과 배포판까지 `floating-clock`으로 통합한다. R006의 원격 이름과 혼합 저장소 보존 정책을 이 요청으로 대체한다.

### 설계와 기본값

- 현재 혼합 원격(id 1408915425)을 `study-vibe-coding-production-principles`로 이름 변경하고 최신 트리에서 desktop-clock 파일을 분리한다. 학습 HTML은 바이트 그대로 보존한다.
- 현재 최종 시계 전용 원격(id 1408945050)을 `floating-clock`으로 이름 변경한다. 기존 v1.0.0 릴리스, 6개 배포/체크섬 파일, CI 기록, 태그, 아이콘·정보창·트레이 소스를 그대로 유지한다. 새 중복 저장소를 만들거나 원격 이력을 강제 덮어쓰지 않는다.
- 두 저장소 모두 비공개 유지. 기존 혼합 이력은 학습 저장소에 보존하고 시계 전용 이력은 시계 저장소에서 이어간다. Git bundle로 양쪽 이력을 로컬 백업한다.
- 학습 폴더의 구형 desktop-clock 디렉터리는 새 시계 저장소의 Git 제외 build/legacy-desktop-clock로 이동 보관한다. 학습 루트 README/AGENTS는 학습용으로 조정한다. 시계 README/출처/현재 링크는 canonical 원격을 사용한다. 역사적 요청 기록은 삭제하지 않고 이 정정 항목을 추가한다.
- 영향: 두 저장소 원격 주소, 학습 tracked desktop-clock 제거, 두 README/AGENTS/REQUEST_LEDGER, 시계 EXTRACTION.json. 시계 실행 코드와 배포 바이너리는 변경 없음.

| ID | 항목 | 상태 | 수용 기준 |
|---|---|---|---|
| R009-01 | 학습 분리 | verified | 학습 main에 시계 소스 없음, 원본 HTML SHA-256 일치, 지침/문서 적합 |
| R009-02 | floating-clock 통합 | verified | 최종 시계 원격의 이름/ID 확인, 시계 전용 트리, standalone 중복 이름 없음 |
| R009-03 | 배포와 Git 전달 | verified | v1.0.0 태그/6개 자산 digest 유지, 두 로컬·원격 main 일치 |

### 검증 및 전달

- GitHub API로 canonical 원격 이름과 ID 검증: 학습 id=1408915425, 시계 id=1408945050. 양쪽 비공개 유지. 계정 저장소 목록에 standalone 이름 없음(이전 URL은 GitHub 리디렉션일 수 있으나 별도 저장소가 아님).
- 학습 원격 루트: .gitattributes, .gitignore, 원본 HTML, AGENTS.md, README.md, docs만 존재. tracked desktop-clock 30개 파일 제거 완료. 학습 HTML의 이전 SHA-256 일치 확인.
- 시계 원격 루트에는 최종 앱·아이콘·F1 정보창·트레이·검증/빌드 파일만 존재. 시계 수정 파일은 README/EXTRACTION/REQUEST_LEDGER 문서뿐이며 실행 코드와 자산의 변경 없음. 따라서 기능 테스트·재빌드는 이번 구조 수정의 필수 검증 범위가 아니다. 기존 플랫폼 검증 한계는 R006~R008 그대로다.
- 원본 desktop-clock 전체(소스/기존 환경/산출물)는 `C:/dev/workspace-codex/floating-clock/build/legacy-desktop-clock`로 이동 보관. 두 저장소의 Git bundle을 `build/repository-reorg-backups`에 보관하고 학습 bundle 검증 성공. 이 보관 파일들은 Git에 제외됨.
- v1.0.0 릴리스 새 주소: https://github.com/yangtaeho/floating-clock/releases/tag/v1.0.0 . 태그는 기존 최종 기능 커밋 4db00813789ae609911afc3c5b273c0f8a868ef6을 유지한다. Windows ZIP·두 Mac DMG 및 세 체크섬 파일 총 6개의 GitHub digest가 변경 전과 일치.
- Git 전달: 학습 구조 정리 커밋 7ade96aac5359d3f5e44ea56ff61415e4211fe37, 시계 이름/링크 정리 커밋 75ff828a4ef40f372a41626a3e09db142f89ec99를 각각 올바른 원격에 푸시하고 로컬/원격 main 일치 확인. 이 완료 기록은 후속 문서 커밋에 전달한다.
- 혼합 이력을 강제로 재작성하지 않았으므로 학습 저장소의 과거 커밋에는 시계 파일이 남아 있다. 최신 트리에는 시계 파일이 없고, 시계 전용 저장소는 분리된 이력으로 계속 개발한다.


## R010 — v1.1.0 공개 배포와 다중 모니터·접근성·UI·시보 개선

요청일: 2026-10-08 (Asia/Seoul). 상태: **verified (Windows 실제 UI·오디오 및 Mac 네이티브 패키지 범위)**.

### 사용자 의도와 요구

floating-clock을 공개하고 비상업적 사용·수정·배포를 허용하며 Issues와 PR을 받는다. 회사 Windows 독립 실행 성공은 사용자 보고로 기록한다. UHD 외부 모니터 분리 후 시계가 화면 밖에 남는 문제를 고치고 숨김/일반 표시에서 다시 찾는 경로를 보강한다. 포맷별 여백, 큰/작은 모드 아이콘과 숨김, 팝업 밖 클릭, 종료 확인, 도움말 GitHub 링크, 시보 끝음을 개선한다. 용량 약 54MB 축소는 이번 구현에서 제외하고 R011로 남긴다.

### 설계·기본값·대체 관계

- 제품 버전 1.1.0. 비상업 소프트웨어용 PolyForm Noncommercial 1.0.0 원문과 저작권 공지 적용. README/기여 안내/이슈·PR 템플릿 제공. GitHub 공개 전 tracked 파일과 이력의 인증·개인 설정 미포함을 확인. 학습 저장소는 비공개 그대로.
- 모든 연결 화면의 availableGeometry 기준으로 겹침이 가장 큰 화면(겹침 없으면 가장 가까운 화면)을 선택해 창 전체가 들어오도록 이동. 음수 좌표·작업표시줄·UHD/DPI 고려. 화면 추가/제거·작업영역/DPI 변경 신호와 1초 구성 검사에서 시계/열린 패널을 복구하고 복구된 위치 저장. 기존 유효한 다중 모니터 위치는 보존.
- 트레이에 항상 '시계 앞으로 가져오기'와 위치 초기화 제공, 왼쪽 클릭도 복원/앞으로 가져오기. Windows 전역 Ctrl+Alt+C 등록(충돌이면 도움말에서 미사용 표시). 일반 표시 정책은 바꾸지 않음. 트레이 없는 환경은 숨김 버튼 비활성.
- 포맷별 최대 글꼴 측정으로 안정적인 폭 계산, 불필요한 220/340px 고정 최소폭·큰 높이 제거. 아이콘/상태 텍스트에 필요한 최소 공간은 유지. 작은 모드 숨기기/종료, 큰 모드 설정/도움말/숨기기/종료 순서. 직접 그린 동일 스타일 아이콘, 툴팁·접근성 이름.
- Qt.Popup 밖 클릭으로 숨겨질 때 컨트롤러 참조도 정리. 시계 클릭/다른 앱 클릭/Esc 닫힘 검증.
- 종료 버튼/창닫기/Ctrl+Q/Esc/트레이 종료를 단일 확인창으로 통합. 기본 선택 취소, 반복 호출은 기존 확인창 활성화. 취소는 타이머·트레이 유지, 종료만 실제 shutdown. R008의 즉시 종료 정책을 대체. 빌드 검증과 자동화는 내부 shutdown 사용.
- 도움말에 공개 GitHub/Issues 링크 및 복원·아이콘 사용법. 명시적 링크 클릭만 브라우저 열기.
- 두 4096Hz 동일 음을 각 120ms, 70ms 간격, 12ms 부드러운 끝맺음과 50ms 무음 꼬리로 합성. 진폭 0.45와 Qt 볼륨 0.5 보존. 정각 판정 정책 유지.
- 영향: clock_core/platform_adapter/main/ui_components/tray_adapter/about_panel/app_metadata/chime_core, WAV, tests/smoke, README/LICENSE/기여·템플릿, package_release/build/CI 및 요청 기록.

| ID | 항목 | 상태 | 수용 기준 |
|---|---|---|---|
| R010-01 | 공개·라이선스·기여 | verified | 원격 private=false, Issues/PR 사용 가능, 라이선스·안내·템플릿 포함 |
| R010-02 | 화면 복구·다시 표시 | verified | 음수/분리/작업영역 코어 검사, 실제 창 복구·전역 핫키·트레이, 기존 유효 위치 보존 |
| R010-03 | 포맷·아이콘·메뉴 | verified | 240개 조합·양쪽 테마·버튼/툴팁·포커스·팝업 클릭 검사 |
| R010-04 | 종료 확인·도움말 | verified | 취소/종료/중복 확인창·각 종료 경로, 링크·사용법 |
| R010-05 | 시보 | verified | PCM 두 동일 음·페이드·무음 꼬리, 정각/절전/시각 변경 회귀·실제 오디오 |
| R010-06 | 배포·Git 전달 | verified | Windows x64/두 Mac v1.1.0 독립 실행 빌드·메타데이터/자산 확인, 릴리스·체크섬 |

### 검증 및 전달

Windows 구현·검증과 공개/배포 전달 완료. 회사 Windows 독립 실행은 사용자 확인. 실제 UHD 케이블 분리와 Mac 실기기 수용은 현재 환경에서 미검증으로 구분한다.


- Windows 로직 29개 통과: 정각 중복/절전/시각 변경, 음수 모니터 좌표·분리·부분 노출·작업 영역·가장 가까운 화면·큰 창, 두 음/페이드/꼬리 검사.
- Windows 실제 Qt UI 240개 조합·경계 알파·레이블 잘림·설정 포커스·목록 유지, F1/링크, 포맷별 폭 축소, 창 화면 밖 이동 후 복구/저장, 네이티브 전역 핫키/트레이 복원, 팝업 시계/밖 클릭, 종료 요청별 취소·중복 방지·확정 종료 통과. 4개 테마/크기와 도움말·확인창 이미지를 직접 확인.
- smoke_audio.py: 실제 Windows 오디오 Ready→재생→끝남, 포커스 유지 및 정각 1회 호출 통과. 음량 0.5 보존. '명료한 삐삐'의 최종 청감은 사용자 수용을 기다림.
- 공개 전 모든 이력의 68개 Git blob을 인증 키/비밀 값 패턴으로 검사: 발견 경로 없음. tracked 사용자 설정/환경/빌드/인증 파일 없음. 공개 허용은 사용자 요청에 근거함.

- 별도 프로세스의 실제 전경 창에서 네이티브 Ctrl+Alt+C를 입력: 숨긴 일반 표시 시계 복원·전경 활성화, 표시 방식 never 유지 확인. 트레이 없는 폴백에서 숨김 비활성. 핫키 선점 시 앱은 계속 실행되고 도움말은 사용 불가를 표시.
- GitHub API 확인: yangtaeho/floating-clock private=false, Issues/Discussions=true, allow_forking=true. 기여/이슈/PR 템플릿과 라이선스 공개. PR에도 contents:read 자동 빌드 적용. 학습 저장소 private=true 유지.
- 기능·라이선스 전달 커밋 e8541a10091744fd97e30438cfb682c0edfa287c. GitHub Actions 37773517157: Windows x64/macOS arm64/macOS x64 세 작업 success. 각 호스트 로직 29개·네이티브 패키징·실제 번들 실행·정보창/아이콘/1.1.0/WAV 검사 통과. Mac LSUIElement/Info.plist 및 DMG 검증, 두 Mac 한국어 도움말 이미지 직접 확인.
- 로컬 Windows build_app.py 및 package_release.py 성공: PE 버전 1.1.0·아이콘, 실제 EXE visible, 185×56 논리픽셀(기본 포맷), Qt Tool, 트레이 visible, About/아이콘/시보 Ready. 기존 사용자 설정을 임시 경로로 격리해 검증. ZIP과 DMG에 프로젝트 LICENSE 및 Python/PySide6/Qt 라이선스·외부 안내 포함.
- 공개 정식 배포: https://github.com/yangtaeho/floating-clock/releases/tag/v1.1.0 . 태그 대상은 위 기능 커밋. Windows ZIP, Mac arm64/x64 DMG, 각 SHA-256 파일 총 6개. GitHub 자산 digest와 로컬 SHA-256 일치 확인.
- Windows ZIP SHA-256: 6e42f18161adb70aaf69e880ba1f49f30c3e0e02ffb7299cf375eb5aa19c29bb (58,732,158 bytes).
- macOS arm64 DMG SHA-256: b01c2a62aeffc739ebec0a1ab222c00bc6f04d25345cee50ecf7cbccc87ac1f2 (53,178,619 bytes).
- macOS x64 DMG SHA-256: 0cce822b78fe2234e8fde062b39ab2fa9ca4c8bf64dfe0febbc0b82b3385f306 (58,549,641 bytes).
- 기존 v1.0.0 바이너리/체크섬은 그대로 두고 FloatingClock-license-notices.zip만 추가 제공하여 공개 배포의 이용 조건·외부 원문에 접근 가능하게 함.
- 한계: 실제 UHD 연결/분리·모든 DPI 구성·Mac 실기기 메뉴 막대/전경/음향/이전 OS는 미검증. Mac offscreen CI의 tray=false는 일반 창 폴백 검사이며 실기기 트레이 부재를 의미하지 않음. Apple 개발자 서명/공증 없음. 청감은 사용자 수용 사항. 배포 크기 축소는 계획 R011 그대로 유지.
- Git 전달: 소스·원본 자산·문서·검증 이미지만 추적. 사용자 설정/빌드/환경/인증 제외, 확인된 로컬 작성자와 canonical origin 사용, 전역 설정 변경 없음. 완료 기록은 후속 문서 커밋에 전달한다.

## R011 — 다음 버전: 독립 실행 배포판 용량 축소

요청일: 2026-10-08. 상태: **verified (R013/R017의 v1.2.1에서 수행)**.

사용자 요청: 약 54MB인 배포판이 크므로 다음 버전에서 축소한다. 이번 v1.1.0의 구현/수용 범위에서 제외한다. 다음 작업은 파일 구성·Qt/오디오 플러그인 비중을 측정하고 불필요한 포함 제거와 대체 패키징을 비교한다. 실행 필수 의존성·한국어·아이콘·시보·독립 실행을 유지하고 Windows/Mac 각각 크기와 동작을 검증할 것. 설계 기본값과 구체적 영향 파일·목표 크기는 실측 후 정한다.


## R012 — 사용자 PC의 C:/dev/tools 설치본 v1.1.0 갱신

요청일: 2026-10-08. 상태: **verified**.

의도: GitHub 배포뿐 아니라 실제 사용하는 C:/dev/tools/FloatingClock.exe도 새 버전으로 갱신한다.
설계·기본값: 기존 EXE를 날짜가 포함된 backups 하위 폴더로 백업하고 공개 v1.1.0 Windows ZIP의 EXE와 라이선스/안내를 설치한다. 기존 FloatingClock.lnk의 대상/내용과 사용자 설정은 보존한다. 대상 EXE가 실행 중인지 확인하고, 현재 실행 중인 대상이 없으면 바로 교체한다. 설치된 EXE를 임시 사용자 환경에서 --verify-build로 검사한 뒤 사용자 환경에서 새 시계를 실행한다. 영향: tools 설치 파일과 백업, 이 누적 문서; 제품 소스 변경 없음.
수용 기준: 설치 EXE 버전=1.1.0·릴리스 EXE와 SHA-256 일치, 기존 EXE 백업 해시 일치, 바로가기 보존, 설치 경로에서 실제 패키지 검사 성공, 새 프로세스 실행 확인. 기존 기능·플랫폼 검증 한계는 R010 유지.
검증 및 전달:
- 교체 전 대상 실행 프로세스 없음. 기존 EXE를 tools/backups/FloatingClock-previous-20261008-210509/FloatingClock.exe에 복사하고 이전 SHA-256 일치 확인.
- 공식 v1.1.0 ZIP 체크섬 검증 후 EXE와 라이선스/외부 원문/READ-ME 설치. 설치 EXE SHA-256 bb76cfec3d4205c3c806203adc453a568bbda568883f95e97b41c7866c584125, 검증된 릴리스 EXE와 일치.
- 설치 경로의 실제 EXE를 임시 사용자 환경에서 --verify-build로 실행: version=1.1.0, visible/tray_visible/about_visible/chime_asset_exists=true. 바로가기 대상 C:/dev/tools/FloatingClock.exe 및 기존 .lnk 해시, 사용자 설정 해시 보존.
- 설치된 새 EXE를 사용자 환경에서 실행. onefile 부모/자식 프로세스와 실제 Floating Clock 창 visible=true 확인. 기존 설정으로 실행 중. 제품 코드/릴리스는 변경 없음. 이 설치 완료 기록만 문서 커밋으로 전달.


## R013 — v1.2.0 Windows 앱 식별과 배포판 경량화·설치 갱신

요청일: 2026-10-08. 상태: **verified (Windows 실제 검증 / Mac 네이티브 번들 범위, 아래 한계 참조)**.

의도: Windows 트레이 설정에서 Python/긴 설명으로 보이는 시계 이름을 Floating Clock으로 고치고 미완료 R011 용량 축소를 이번 버전에서 처리한다. 완성한 Windows/Mac 배포판을 GitHub에 올리고 C:/dev/tools 설치본까지 갱신한다.
설계/기본값: v1.2.0. Windows 프로세스에 BUNDLE_ID 기반 AppUserModelID를 창/트레이 생성 전에 적용, Qt 표시명과 PE FileDescription을 Floating Clock으로 통일. Windows 설치 정리에서는 예전 Python 트레이 기록의 아이콘 snapshot이 시계와 정확히 일치하고 UID=0/경로가 확인된 항목만 백업 후 제거하며, '항상 표시' 선택을 실제 tools EXE 항목에 이전. 다른 Python/앱 기록과 시작프로그램은 변경하지 않음.
- 빌드의 58,732,158-byte Windows ZIP을 기준으로 구성 실측. QWidget UI·PNG/ICO·PCM WAV만 쓰므로 QtQuick/QML/PDF/3D/OpenGL 소프트웨어 렌더러, 영상 FFmpeg 코덱, 미사용 플러그인을 제외. QSoundEffect는 Qt Multimedia 본체의 내장 오디오 기능을 유지. 목표: Windows ZIP 최소 30% 축소, Mac도 같은 제한으로 전/후 측정. 파일별 포함 목록·제외 근거와 패키지 오디오 검증 기록.
- UI/시보/트레이/화면 복구·독립 실행 유지. 설치본 --verify-build 및 실제 번들 오디오 Ready→재생→종료 검사. 기존 종료 확인을 거쳐 현재 tools 실행본을 종료하고 백업/교체/재실행. 이전 설정·바로가기 보존.
- 영향: app_metadata/platform_adapter/main/build_app, 패키지 검증/빌드 구성/README·AGENTS·누적 기록, tools 설치본/관련 캐시(로컬 백업). 실제 UHD 케이블 분리·Mac 실기기/서명 등 R010의 환경상 한계는 미검증으로 유지.
수용: 앱 ID/표시명/PE FileDescription 확인, Windows 캐시의 시계에 해당하는 Python 기록만 정리, ZIP 크기≥30% 감소·두 Mac 전후 측정, 로직/실제 Qt UI·소스 및 번들 오디오, 3종 CI·릴리스/체크섬·tools 실행 확인.
검증 및 전달: R017의 v1.2.1 묶음 검증·배포 기록 참조.


## R014 — v1.2.0 사용자 지정 전역 복원 단축키

요청일: 2026-10-08. 상태: **verified (Windows 실제 검증 / Mac 네이티브 번들 범위, 아래 한계 참조)**.
의도: 기존 Ctrl+Alt+C는 충돌 우려가 높으므로 Ctrl+Alt+Shift+C, C를 기본으로 하고 사용자마다 단축키를 설정할 수 있도록 한다. R010 고정 전역 키 정책을 대체하고 R013/v1.2.0에 함께 배포한다.
설계/기본값: Windows 기본 Ctrl+Alt+Shift+C를 누른 뒤 1초 안에 C(또는 같은 조합을 한 번 더)를 눌러 복원. 사용자 키 입력 위젯에서 1~2단계 조합을 입력한 뒤 적용하거나 사용 안 함 선택. 첫 단계에는 Ctrl/Alt/Win 중 하나 필요. 설정 필드 recovery_shortcut 저장, 기존 설정에는 새 기본값 보충. 등록 실패/유효하지 않은 키/사용 안 함/Windows 전용 상태를 설정·도움말에 표시. 키 입력 중 기존 전역·앱 단축키를 해제해 입력 방해 방지; 적용/포커스 종료/창닫기에서 재등록. 두 번째 키는 대기 시간 동안만 등록하고 성공·시간 초과·설정 변경·종료에서 해제. 설정창 이외 앱 입력과 포커스는 유지.
영향: clock_core/hotkey_core/platform_adapter/main/settings_panel/about_panel, 테스트·README·기록.
수용: 기본 두 단계, 사용자 한/두 단계·끄기·재시작 보존, 충돌·시간 초과·두 번째 키 해제·입력 포커스 검증, 네이티브 다른 앱에서 복원. Mac 전역키는 Windows 전용 표시 및 트레이 경로 유지.


## R015 — v1.2.0 다크 설정 셀렉트의 흰 영역 제거

요청일: 2026-10-08. 상태: **verified (Windows 실제 검증 / Mac 네이티브 번들 범위, 아래 한계 참조)**.
의도: 다크 모드 설정 셀렉트의 의도치 않은 흰 영역을 이번 개선에 포함.
설계: 닫힌 콤보·드롭다운·네이티브 팝업 컨테이너·뷰포트·스크롤바의 palette와 배경/선택/화살표 스타일을 테마 색으로 명시. 영향: settings_panel, 실제 UI/이미지 검사. 수용: 라이트/다크 닫힘·펼침·선택·호버·스크롤 영역의 흰 배경 제거, 기존 드롭다운 포커스/타이머 검사 유지.

## R016 — v1.2.0 즉시 툴팁·숨기기 아이콘·단일 실행

요청일: 2026-10-08. 상태: **verified (Windows 실제 검증 / Mac 네이티브 번들 범위, 아래 한계 참조)**.
의도: 아이콘 마우스 오버 시 빠르고 예쁜 위쪽 툴팁, 다운로드처럼 보이지 않는 숨기기, 재실행 시 시계 한 개.
설계/기본값: 툴팁 인위적 대기 0ms, 아이콘 위 둥근 테마 팝업·화면 경계 안 배치·포커스 비활성·이탈/클릭/숨김 제거. 요청의 0.125ms는 실제 OS 렌더링에서 보장 불가하므로 125ms보다 짧게 반응하는지 검사하고 지연 없이 표시. 숨기기 도안은 아래 화살표를 없애고 일반 최소화 가로선으로 통일.
- 사용자 설정 경로별 QLockFile + QLocalServer(UserAccessOption)로 단일 인스턴스. 재실행은 로컬 IPC로 기존 시계를 보이게/앞으로 가져오고 두 번째 실행은 종료. 시작 경쟁·남은 잠금/죽은 프로세스·정상 종료/재실행 검사. 인터넷/관리자 권한 불필요. 빌드 검증 모드는 임시 사용자 환경에서 별도 실행.
- 영향: ui_components/instance_adapter/main, 회귀검사/사용법/기록. 수용: 양쪽 테마 툴팁 위치·빠른 표시·포커스/수명, 숨기기 가로선, 실제 별도 프로세스 재실행·숨김 복원·동시 실행·충돌/종료 후 재시작.


## R017 — 오로라 테마와 v1.2.1 묶음 배포

요청일: 2026-10-08. 상태: **verified (Windows 실제 검증 / Mac 네이티브 번들 범위, 아래 한계 참조)**.
의도: fancy한 테마를 하나 추가하고 버전을 조금 올린다. 아직 발행하지 않은 R013~R016 v1.2.0 개선 묶음은 이 요청과 함께 v1.2.1로 전달한다.
설계/기본값: 오로라(aurora) 테마: 남색→보라색 대각 그라데이션 표면, 민트 포인트·밝은 텍스트·푸른 경계/컨트롤. 시계/설정/도움말/메뉴/툴팁에 공통 적용. 새 설치 라이트 기본값은 유지하고 선택 저장. 영향: ui_components/clock_core/settings_panel/app_metadata·이미지/사용법/검증. 수용: 세 테마 × 모든 시간/날짜·크기의 360개 조합, 잘림·알파·선택/포커스·저장·실제 이미지 확인. 배포/설치 버전 1.2.1.

### R011/R013~R017 v1.2.1 최종 검증·전달

- R017에 따라 미발행 v1.2.0 묶음을 v1.2.1로 최종 전달. 소스 커밋 60ce61ebe67055a6aa7ba80ca51c16326cf52c96, canonical main 푸시 완료. 사용자 설정·환경·빌드·실행 파일·레지스트리 백업은 Git 제외.
- `python -m unittest -v`: 35개 통과. 순수 키 파싱/설정 유지/미사용 바이너리 정책과 기존 시각·시보·모니터 좌표 정책 포함.
- `smoke_ui.py --capture`: Windows 실제 Qt 360개 조합 통과. 라이트/다크/오로라 × 크기/시간제/초/시간·날짜 프리셋, 글자 잘림·경계 알파, 설정 포커스/열린 목록/타이머, 네이티브 topmost, 전역 두 단계 입력과 설정 변경·끄기, 즉시 툴팁 위치/125ms 이내 표시/포커스 유지/이탈 제거, 어두운 목록·뷰포트·팝업 경계, 메뉴 외부 클릭, 확인 후 종료/취소 검사. 오로라 시계·설정과 다크 드롭다운 이미지를 직접 확인. Qt 네이티브 창의 topmost 힌트도 Win32 상태와 맞춰 목록 창이 always 상태를 되돌리지 않도록 수정.
- `smoke_audio.py`: Windows 실제 소리 Ready→재생 시작→끝남, 포커스 유지·정각 한 번 호출 통과. 음원과 음량은 v1.1.0 유지.
- 로컬 격리 `build/hotkey-smoke.py`: 실제 RegisterHotKey 기본 두 단계, 1초 시간 초과와 bare C 해제, 사용자 Ctrl+Alt+F10 복원, 키 선점 실패/해제 후 재등록, 사용 안 함 통과. 별도 앱의 전경을 만드는 `native_recovery_probe.py`는 이번 세션에서 Windows 전경 권한 제한으로 사전 조건에 실패하여 외부 앱→전경 활성화 수용을 다시 검증하지 못함. 이 한계를 숨기지 않으며 기존 v1.1.0의 전경 복원 구현은 유지.
- 로컬 격리 `build/instance-smoke.py`: 실제 별도 프로세스 재실행으로 숨긴 시계 복원, 동시에 두 보조 실행이 같은 인스턴스에 전달, 테스트 소유 프로세스 종료 후 잠금 회수와 정상 unlock 통과. 설치된 실제 EXE도 재실행 exit=0, 기존 HWND 7540828/PID 25952 그대로 visible, 사용자 시계 창 하나 유지. onefile 부모·자식 두 프로세스는 한 인스턴스임.
- Windows `build_app.py`/`package_release.py --platform windows-x64`: 제품명/PE FileDescription Floating Clock, ProductVersion 1.2.1, 앱 ID com.yangtaeho.floatingclock, 실제 트레이·정보창·아이콘·PCM WAV와 번들 오디오 재생/끝남 통과.
- GitHub Actions 37780112021: Windows x64, Mac arm64, Mac x64 세 작업 success. 각 플랫폼 로직 35개·실제 번들 실행·버전·아이콘·Info.plist/LSUIElement(Mac)·오디오 Ready/시작/끝남·30% 이상 크기 축소 검사 통과. Mac offscreen 정보창 두 이미지를 직접 확인.
- 배포 크기: Windows ZIP 58,732,158→31,574,572 bytes(-46.24%), Mac arm64 DMG 53,178,619→33,891,209(-36.27%), Mac x64 DMG 58,549,641→36,743,694(-37.24%). 필수 Qt Widgets·Network(로컬 IPC)·Multimedia/PCM·한국어·아이콘·원문 라이선스 유지, 사용하지 않는 영상/3D/QML/PDF/소프트웨어 OpenGL 구성만 제외.
- 정식 공개 릴리스: https://github.com/yangtaeho/floating-clock/releases/tag/v1.2.1 . 대상은 위 테스트 소스 커밋. Windows ZIP·두 Mac DMG와 각 SHA-256 파일 총 6개 업로드, GitHub digest와 로컬 해시 일치 후 draft=false로 발행.
- Windows ZIP SHA-256 84cb32285d7c9e612590069772dafd3d2f00ebf7acc941368a13d27a13e83865.
- Mac arm64 DMG SHA-256 4bcd5dfafc89050483a73423ad75f707cb491f8367b9540b63af6bfe22ec63d1.
- Mac x64 DMG SHA-256 bf10f45a36cfc5521e9d74d32c1f807383f547f7315bd10dde71868f2447ffac.
- C:/dev/tools 갱신: 교체 직전 해당 EXE 실행 프로세스 없음. 기존 v1.1.0 EXE·바로가기·설정 및 관련 캐시는 C:/dev/tools/backups/FloatingClock-1.1.0-20261008-215353에 백업. 설치 EXE 31,817,918 bytes, SHA-256 aff8f3dee4fd53eac5bcf98068d4ef42d3df6947b0e6ed503da2fb0e8cfa417c, 릴리스 EXE와 일치. 기존 .lnk와 settings.json 해시 보존. 격리 환경에서 설치 경로 --verify-audio 통과 후 사용자 환경으로 실행, 실제 창 확인. 기존 라이트/24시간/위치 선택을 보존하고 오로라를 임의로 켜지 않음.
- 예전 Python 트레이 캐시: key 9395770847283810984의 Python312/python.exe 경로·UID=0와 tools 항목의 IconSnapshot SHA-256 9ff8b5217de992b4ed57a7e485ca48b69acf601640e928cc26ed1ef51793cf68 일치를 확인. 해당 키와 tools 키를 reg export로 백업 후 그 Python 키 하나만 제거, 기존 IsPromoted=1을 tools 실행 항목에 이전. 제거 완료와 tools IsPromoted=1 재확인. 다른 Python/앱 캐시와 Explorer는 건드리지 않음. Windows 설정 화면 자체의 재렌더링은 사용자 확인 범위.
- 한계: Mac 실기기 테마·메뉴 막대·단일 실행·포커스·물리 음향, UHD 실제 케이블 분리와 모든 DPI, Apple 개발자 서명/공증은 미검증/미제공. Windows 외부 앱에서 전경 활성화는 위 사전 조건 실패로 이번 세션 재검증 불가. 툴팁은 인위적 지연 0이며 OS 렌더링 0.125ms를 보장하지 않음. UI 검사는 125ms 이내 기준. 소리 청감은 사용자 수용 대상.

## R018 — ARM Mac 실기기 실행 확인과 설정 패널 깜빡임 개선

요청일: 2026-10-08. 상태: **verified (Windows 실제 Qt 및 Mac CI 범위 / ARM Mac 깜빡임 재수용 대기)**.

사용자 보고: v1.2.1 ARM Mac이 안내대로 실행되고 잘 동작함을 확인. 설정 창·셀렉트 박스의 흔들림과 오른쪽 스크롤바 깜빡임은 남아 있음. 실행 성공만 실기기 검증으로 추가하며 모든 개별 기능의 수용으로 확대하지 않는다.

설계: v1.2.2 유지보수 배포. 설정 변경 시 테마가 같으면 스타일/팔레트 재적용을 피하고 바뀐 값만 동기화. 드롭다운의 테마는 화면에 보이기 전에 적용하여 표시 직후 재배치·재도장을 제거. 설정 시각 미리보기의 글자 폭 변화가 패널 크기 계산으로 전달되지 않도록 크기 정책 고정. 패널 공간 부족 여부로 스크롤바 공간을 미리 결정하고 Mac 자동 숨김/오버레이 전환을 피한다. 타이머·설정 변경·열린 목록·스크롤·테마 전환 동안 창/목록/스크롤바 위치와 크기·포커스·스타일 재적용 여부를 검사한다.

영향: settings_panel.py, smoke_ui.py 및 플랫폼 공통 설정 패널 회귀 검사, app_metadata.py, README/누적 기록. 수용: Windows 실제 Qt와 Mac CI에서 미리보기 반복 갱신·설정 변경·열린 선택 목록·작은 화면 스크롤 중 기하 상태 유지, 기존 360개 UI 조합·소리·독립 실행 회귀 통과. Windows/ARM·Intel Mac 배포와 체크섬 GitHub 전달 및 tools 갱신. ARM Mac 실제 깜빡임 해소는 새 배포판 사용자 재확인 범위.


### R018 검증·배포 결과

- 사용자의 ARM Mac v1.2.1 실행 성공을 확인된 실기기 보고로 추가. 세부 동작 전체 통과나 깜빡임 해소로 확대하지 않음.
- 설정 테마가 같으면 전체 QSS와 콤보 팔레트를 재적용하지 않도록 변경. RoundedWindow도 같은 색상의 재적용을 생략하여 부모 창 갱신이 설정 컨트롤을 다시 스타일링하지 않음. 목록 배경은 showPopup 전에 적용. 미리보기 QLabel은 가로 Ignored/세로 Fixed로 글자 폭에 따른 sizeHint 변화를 차단. 패널 공간 기준 AlwaysOn/AlwaysOff 스크롤바와 별도 Fusion proxy의 SH_ScrollBar_Transient=0 적용.
- `python -m unittest -q`: 35개 통과. `smoke_ui.py --capture`: Windows 실제 Qt 360개 조합·경계 알파·포커스/목록/메뉴/종료·키·트레이 검사 통과. 기존 툴팁 검사에서 QTest의 native popup 이후 Enter 누락이 발생하여 해당 Qt Enter를 명시 전달하도록 검사 안정화; 실제 렌더링/위치와 커서 이탈 제거 검사는 유지. 설정 오로라 이미지를 직접 확인.
- 신규 `smoke_settings.py`: Windows 실제 Qt와 Mac arm64/x64 offscreen CI 모두 세 테마 × 420/1600 논리픽셀 작업 영역, 미리보기 90회/조합(총 540회), 설정 변경, 열린 목록 30회 갱신, 1.1초 타이머/스크롤 위치 유지 통과. 전체 패널·콤보·스크롤바의 비테마 StyleChange=0, 창/본문/뷰포트/콤보/열린 목록의 기하 상태 유지와 자동 숨김 비활성 확인. Mac 물리 화면 깜빡임 검사로 주장하지 않음.
- 전달 소스 커밋 48f068ccade6f2b0b94195bbf0f64700543c61a5. GitHub Actions 37783899621 Windows x64/Mac arm64/Mac x64 세 작업 success. 위 설정 검사와 로직 검사, 각 호스트 네이티브 빌드·번들 실행·버전/아이콘/About/시보 Ready→시작→종료·경량화 기준 통과.
- 공개 릴리스 https://github.com/yangtaeho/floating-clock/releases/tag/v1.2.2 . 해당 소스 커밋 대상으로 3종 배포·각 SHA-256 파일 총 6개 업로드, 바이너리 GitHub digest와 로컬 SHA-256 일치 확인 후 정식 발행.
- Windows ZIP 31,578,145 bytes, SHA-256 1674f5793bf09615412b2c5863c5cb4feff366b1cbb6c6beb0984b04ff1ee587.
- ARM Mac DMG 33,895,711 bytes, SHA-256 b4404acc9f067aece1b486ea03c482f49e8863acbea8ed7c2de19dc863ba4cb8.
- Intel Mac DMG 36,627,745 bytes, SHA-256 586ff69108f775919b8a7601c9a75ac0116b2f52d0ecaf56e5f60c4b81886d71.
- tools 기존 1.2.1 EXE/바로가기/설정 백업: C:/dev/tools/backups/FloatingClock-1.2.1-20261008-221720 . 종료 확인 자동 입력과 Windows 접근성 Close/Invoke 시도는 종료하지 못함. 정확한 C:/dev/tools/FloatingClock.exe 경로로 확인된 프로세스만 업데이트 범위에서 중지하고 교체 직전 설정도 추가 백업. 설정과 .lnk 해시 보존, 릴리스 EXE와 해시 일치.
- tools 설치 EXE 1.2.2, 31,820,847 bytes, SHA-256 e5746ad51158478ed63107b887ba9aba9d1124e0dc57fde0010297a6efc67f3a. 격리 환경 --verify-audio로 ID/트레이/About/실제 시보 종료 확인 후 사용자 환경으로 실행. 실제 시계 창 하나 visible, 재실행 exit=0/동일 HWND 17108968 유지 확인.
- 기존 v1.2.1 자산을 덮어쓰지 않고 별도 v1.2.2로 전달. 사용자 설정/환경/빌드/설치 파일·백업은 Git 제외. 기존 Mac 서명·공증/실기기 음향·UHD/DPI·전경 수용 한계는 유지. ARM Mac 새 설정 창 깜빡임 해소는 사용자 재확인 필요.

## R019 — ARM Mac 설정 개선 수용과 단축키 확인·시계 크기 조절

요청일: 2026-10-08. 상태: **implementing**.

사용자 보고: ARM Mac에서 v1.2.2의 이전 설정 창/셀렉트/스크롤 문제들이 해결된 것으로 확인. 이 범위는 실기기 수용 완료로 추가. 단축키는 잘 동작하는지 불확실하며, 시계는 생각보다 큼. 단축키 종류와 원하는 축소 수준은 확인 중.

설계: 시계 전용 크기 비율 65/80/100/120%를 설정에 추가하여 글자·여백·모서리·버튼을 함께 조절. 기존 사용자 비율은 100%로 이전하고 설정/도움말 패널은 읽기 쉬운 크기 유지. 작은 모드의 56px 최소 높이와 60px 버튼 여백도 비율에 맞춰 축소. 저장 필드 clock_scale, 설정에 65%/80%/100%/120% 표시. R018의 설정 기하 안정성 유지. 단축키는 현재 Mac 전역 복원이 미지원임을 명확히 설명하고 실제 사용자 대상 키 확인 후 범위 확정. 설정/종료 키는 Mac ⌘ 표기로 통일.

영향: clock_core.py/main.py/settings_panel.py/about_panel.py·UI 및 로직 회귀검사·사용법/누적 기록. 수용: 세 테마/작은·큰/포맷/각 비율 잘림·경계 알파·클릭 영역·화면 복구 검사, 설정 값 저장·이전 보존, 설정 패널의 기하/열린 목록 안정성. 단축키의 종류/지원 범위/수용은 추가 확인 내용을 누적한다. 검증 완료 시 후속 유지보수 배포.


### R019 확인 답변에 따른 설계 확정

- 사용자가 지칭한 것은 숨긴 시계 복원 전역 키. 기존 v1.2.2 Mac 미지원이 원인이며 v1.2.3에 Mac 네이티브 전역 등록을 추가. 기본 키는 Qt portable Ctrl+Alt+Shift+C, C의 Mac 표현 ⌘⌥⇧C → C. Carbon RegisterEventHotKey/앱 이벤트 핸들러를 사용하고 입력 모니터링/외부 Python 라이브러리를 추가하지 않음. 1초 동안만 두 번째 키를 등록하고 완료/시간초과/입력 편집/설정 변경/종료에 해제, 같은 첫 조합 반복도 기본 제스처를 완료. 설정 커스텀/끄기/등록 오류 표시 유지. Mac Ctrl는 ⌘, Meta는 ⌃로 Qt와 동일하게 해석. F21~F24는 Mac 하드웨어 키 매핑 부재로 오류 표시, F1~F20 지원. ANSI 키 위치 기준.
- 사용자 크기 선택은 Mac에서만 기존의 약 90%, Windows는 현재 유지. 위 초기 65/80/100/120% 제안을 대체해 선택을 80/90/100/120%로 확정. OS 독립 ClockPreferences 기본값은 100%, 설정 로딩 어댑터가 비율 없는 Mac 설정(기존 버전 포함)에 90% 적용. Windows는 100%, 명시 선택 값은 재시작·업그레이드 시 보존. 설정 패널 자체는 축소하지 않음.
- Mac CI에서 실제 Cocoa 환경의 Carbon 등록 및 네이티브 이벤트 전달로 숨김 복원·두 단계·시간초과·커스텀·입력 중 중지/재등록·끄기 검사. OS에서 사람이 누르는 실제 전역 키와 다른 앱에서 전경 이동은 사용자 Mac 재수용 범위로 구분. Windows 실제 Qt 비율 포함 1440조합 검사, 기본100% 치수 유지·90% 축소·클릭·화면복구·설정 패널 안정성 검사.
