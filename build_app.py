"""Reproducible PyInstaller bundle, avoiding unrelated ICU DLLs on PATH."""
import os
from pathlib import Path
import PyInstaller.__main__


SPEC = r'''
import sys
from pathlib import Path
project = Path(SPECPATH).parent
a = Analysis([str(project / 'main.py')], pathex=[str(project)],
             binaries=[], datas=[(str(project / 'assets' / 'hourly-chime.wav'), 'assets')],
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
    app = BUNDLE(collect, name='FloatingClock.app', bundle_identifier='local.floatingclock')
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='FloatingClock',
              debug=False, strip=False, upx=False, console=False)
'''


if __name__ == "__main__":
    project = Path(__file__).resolve().parent
    os.chdir(project)
    folder = project / "build"
    folder.mkdir(exist_ok=True)
    spec = folder / "FloatingClock.spec"
    spec.write_text(SPEC, encoding="utf-8")
    PyInstaller.__main__.run(["--noconfirm", "--clean", str(spec)])
