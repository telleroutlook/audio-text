"""
py2app 打包配置
用法: .venv/bin/python3 setup.py py2app
"""

from setuptools import setup

APP = ["gui.py"]
DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "语音转文字",
        "CFBundleDisplayName": "语音转文字",
        "CFBundleIdentifier": "com.audio-text.mlx-whisper",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSMinimumSystemVersion": "13.0",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Audio File",
                "CFBundleTypeExtensions": ["mp3", "m4a", "wav", "ogg", "flac", "aac"],
                "CFBundleTypeRole": "Viewer",
            },
            {
                "CFBundleTypeName": "Video File",
                "CFBundleTypeExtensions": ["mp4", "mov", "mkv"],
                "CFBundleTypeRole": "Viewer",
            },
        ],
    },
    "packages": ["mlx_whisper", "mlx", "numpy", "sounddevice"],
    "includes": ["tkinter", "wave", "tempfile"],
    "excludes": ["test", "unittest", "email", "html", "http", "xml", "pydoc"],
    "iconfile": None,
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
