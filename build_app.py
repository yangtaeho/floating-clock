"""Reproducible PyInstaller bundle, avoiding unrelated ICU DLLs on PATH."""
import os
from pathlib import Path
import PyInstaller.__main__
from app_metadata import APP_NAME, VERSION, AUTHOR, DESCRIPTION


SPEC = r'''
import sys
from pathlib import Path
project = Path(SPECPATH).parent
sys.path.insert(0, str(project))
from app_metadata import VERSION, BUNDLE_ID
a = Analysis([str(project / 'main.py')], pathex=[str(project)],
             binaries=[], datas=[(str(project / 'assets' / 'hourly-chime.wav'), 'assets'),
                                 (str(project / 'assets' / 'icon.png'), 'assets')],
             hiddenimports=[], hookspath=[], hooksconfig={},
             runtime_hooks=[], excludes=[], noarchive=False)
if sys.platform == 'win32':
    # Qt's Windows build imports the unversioned Windows ICU API. A different
    # program on PATH may provide icuuc.dll with versioned exports instead.
    # Never bundle that DLL (or its data file); use the matching system API.
    a.binaries = [entry for entry in a.binaries
                  if not (Path(entry[0]).name.lower() == 'icuuc.dll'
                          or Path(entry[0]).name.lower().startswith('icudt'))]
pyz = PYZ(a.pure)
if sys.platform == 'darwin':
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='FloatingClock',
              debug=False, strip=False, upx=False, console=False)
    collect = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='FloatingClock')
    app = BUNDLE(collect, name='FloatingClock.app', bundle_identifier=BUNDLE_ID,
                 icon=str(project / 'assets/icon.icns'),
                 info_plist={'CFBundleShortVersionString': VERSION, 'CFBundleVersion': VERSION,
                             'LSUIElement': True, 'NSHighResolutionCapable': True})
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='FloatingClock',
              debug=False, strip=False, upx=False, console=False,
              icon=str(project / 'assets/icon.ico'), version=str(project / 'build/version_info.txt'))
'''


if __name__ == "__main__":
    project = Path(__file__).resolve().parent
    os.chdir(project)
    folder = project / "build"
    folder.mkdir(exist_ok=True)
    parts = tuple(int(part) for part in VERSION.split('.')) + (0,)
    strings = {'CompanyName': AUTHOR, 'FileDescription': DESCRIPTION,
               'FileVersion': VERSION, 'ProductName': APP_NAME, 'ProductVersion': VERSION,
               'OriginalFilename': 'FloatingClock.exe'}
    resource = "VSVersionInfo(ffi=FixedFileInfo(filevers=" + repr(parts) + ", prodvers=" + repr(parts) + ", mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)), kids=[StringFileInfo([StringTable('040904B0', [" + ','.join('StringStruct(' + repr(k) + ',' + repr(v) + ')' for k,v in strings.items()) + "])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])"
    (folder / 'version_info.txt').write_text(resource, encoding='utf-8')
    spec = folder / "FloatingClock.spec"
    spec.write_text(SPEC, encoding="utf-8")
    PyInstaller.__main__.run(["--noconfirm", "--clean", str(spec)])
