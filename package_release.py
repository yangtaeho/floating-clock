"""Verify the bundled executable and package standalone downloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
import plistlib
from importlib.metadata import distribution
from app_metadata import VERSION, BUNDLE_ID


def license_files(root):
    """Include project terms and runtime notices with every standalone download."""
    files = [(root / name, name) for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md')]
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.is_file():
        python_license = Path(sys.base_prefix) / 'LICENSE'
    if python_license.is_file():
        files.append((python_license, 'third-party-licenses/Python-LICENSE.txt'))
    else:
        files.append((root/'assets/legal/Python-LICENSE.txt', 'third-party-licenses/Python-LICENSE.txt'))
    for package in ('PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6'):
        dist = distribution(package)
        for file in dist.files or []:
            if '/licenses/' in str(file):
                path = Path(dist.locate_file(file))
                if path.is_file():
                    files.append((path, f'third-party-licenses/{package}/{path.name}'))
    files.extend((path, f'third-party-licenses/Qt/{path.name}') for path in (root/'assets/legal').glob('*.txt') if path.name != 'Python-LICENSE.txt')
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', required=True, choices=['windows-x64', 'macos-arm64', 'macos-x64'])
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    os.chdir(root)
    mac = sys.platform == 'darwin'
    expected = 'macos-' + ('arm64' if platform.machine() == 'arm64' else 'x64') if mac else 'windows-x64'
    if expected != args.platform or (not mac and sys.platform != 'win32'):
        raise RuntimeError('Distribution platform must match the native build host')
    executable = root / ('dist/FloatingClock.app/Contents/MacOS/FloatingClock' if mac else 'dist/FloatingClock.exe')
    report = root / 'build/packaged-verification.json'
    report.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as scratch:
        env = dict(os.environ, LOCALAPPDATA=scratch, HOME=scratch)
        if mac:
            env['QT_QPA_PLATFORM'] = 'offscreen'
        subprocess.run([str(executable), '--verify-build'], env=env, check=True, timeout=90)
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data['visible'] and data['width'] > 0 and data['height'] > 0, data
    assert data['time'] and data['date'] and data['chime_asset_exists'], data
    assert data['version'] == VERSION and data['icon_loaded'] and data['about_visible'], data
    assert VERSION in data['about_version'], data
    if mac:
        with (root/'dist/FloatingClock.app/Contents/Info.plist').open('rb') as stream:
            info = plistlib.load(stream)
        assert info['CFBundleShortVersionString'] == VERSION and info['CFBundleVersion'] == VERSION
        assert info['CFBundleIdentifier'] == BUNDLE_ID and info['LSUIElement']
        assert (root/'dist/FloatingClock.app/Contents/Resources'/info['CFBundleIconFile']).is_file()
    else:
        import pefile
        pe = pefile.PE(str(executable))
        strings = {}
        for group in pe.FileInfo:
            for entry in group:
                for table in getattr(entry, 'StringTable', []):
                    strings.update(table.entries)
        assert strings[b'ProductVersion'].decode('utf-8') == VERSION, strings
        assert strings[b'ProductName'].decode('utf-8') == 'Floating Clock', strings
        assert any(entry.id == 14 for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries), 'Missing Windows icon'
        pe.close()
    # CI machines may have no audio output device; don't claim audible playback.
    output = root / 'release'
    output.mkdir(exist_ok=True)
    notices = license_files(root)
    instructions = ('Windows: unzip and open FloatingClock.exe. No Python installation required.\n'
                    'macOS: open the DMG and drag FloatingClock.app to Applications.\n'
                    'Use arm64 for Apple Silicon or x64 for Intel. Built on macOS 15.\n'
                    'No Apple Developer signature or notarization. If blocked, allow this app in System Settings > Privacy & Security.\n'
                    'Mac verification uses offscreen rendering, not physical display/audio acceptance.\n')
    if mac:
        with tempfile.TemporaryDirectory() as scratch:
            staging = Path(scratch) / 'FloatingClock'; staging.mkdir()
            subprocess.run(['ditto', str(root/'dist/FloatingClock.app'), str(staging/'FloatingClock.app')], check=True)
            (staging/'Applications').symlink_to('/Applications')
            (staging/'READ-ME.txt').write_text(instructions, encoding='utf-8')
            for source, name in notices:
                destination = staging / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            archive = output / f'FloatingClock-{args.platform}.dmg'
            subprocess.run(['hdiutil', 'create', '-volname', 'FloatingClock', '-srcfolder', str(staging), '-ov', '-format', 'UDZO', str(archive)], check=True)
            subprocess.run(['hdiutil', 'verify', str(archive)], check=True)
    else:
        archive = output / f'FloatingClock-{args.platform}.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(executable, 'FloatingClock.exe')
            bundle.writestr('READ-ME.txt', instructions)
            for source, name in notices:
                bundle.write(source, name)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / f'{archive.name}.sha256').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    print(f'Verified and packaged: {archive.name} sha256={digest}')


if __name__ == '__main__':
    main()
