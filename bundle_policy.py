"""Binary allowlist for the QWidget/PNG/PCM application, shared by native builds."""
import re

PLUGIN_ALLOWLIST = {
    'platforms': {'qwindows', 'qcocoa', 'qoffscreen', 'qminimal'},
    'styles': {'qmodernwindowsstyle', 'qmacstyle'},
    'imageformats': {'qico'},
}
UNUSED_MODULES = ('qt6quick', 'qt6qml', 'qt6pdf', 'qt6opengl', 'qt6multimediawidgets',
                  'qt6svg', 'qt6virtualkeyboard', 'qt6shadertools')
CODECS = ('avcodec', 'avformat', 'avutil', 'swresample', 'swscale', 'avfilter', 'avdevice')


def keep_binary(name):
    path = name.replace('\\', '/').lower()
    basename = path.rsplit('/', 1)[-1]
    if '/plugins/' in path:
        folder, filename = path.split('/plugins/', 1)[1].split('/', 1)
        stem = filename.removeprefix('lib').split('.')[0]
        return stem in PLUGIN_ALLOWLIST.get(folder, set())
    stem = basename.removeprefix('lib')
    if stem.startswith(UNUSED_MODULES) or basename == 'opengl32sw.dll':
        return False
    # macOS framework directories and Windows shared libraries.
    if any('/qt'+module.removeprefix('qt6')+'.framework/' in path for module in UNUSED_MODULES):
        return False
    if any(stem.startswith(codec) for codec in CODECS):
        return False
    return True
