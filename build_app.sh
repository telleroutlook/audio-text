#!/bin/bash
# 构建 macOS .app bundle（轻量包装器方式）
# .app 通过 shell 脚本调用项目 venv 中的 Python 运行 GUI

set -e

APP_NAME="语音转文字"
APP_DIR="dist/${APP_NAME}.app"
CONTENTS="${APP_DIR}/Contents"
MACOS="${CONTENTS}/MacOS"
RESOURCES="${CONTENTS}/Resources"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "构建 ${APP_NAME}.app ..."

# 清理旧构建
rm -rf "dist/${APP_NAME}.app"
mkdir -p "${MACOS}" "${RESOURCES}"

# Info.plist
cat > "${CONTENTS}/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>语音转文字</string>
    <key>CFBundleDisplayName</key>
    <string>语音转文字</string>
    <key>CFBundleIdentifier</key>
    <string>com.audio-text.mlx-whisper</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleExecutable</key>
    <string>launch</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>语音转文字需要使用麦克风进行录音转录</string>
    <key>CFBundleDocumentTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeName</key>
            <string>Audio File</string>
            <key>CFBundleTypeExtensions</key>
            <array>
                <string>mp3</string>
                <string>m4a</string>
                <string>wav</string>
                <string>ogg</string>
                <string>flac</string>
                <string>aac</string>
            </array>
            <key>CFBundleTypeRole</key>
            <string>Viewer</string>
        </dict>
        <dict>
            <key>CFBundleTypeName</key>
            <string>Video File</string>
            <key>CFBundleTypeExtensions</key>
            <array>
                <string>mp4</string>
                <string>mov</string>
                <string>mkv</string>
            </array>
            <key>CFBundleTypeRole</key>
            <string>Viewer</string>
        </dict>
    </array>
</dict>
</plist>
EOF

# 启动脚本
cat > "${MACOS}/launch" << EOF
#!/bin/bash
PROJECT_DIR="${PROJECT_DIR}"
cd "\${PROJECT_DIR}"
exec "\${PROJECT_DIR}/.venv/bin/python3" "\${PROJECT_DIR}/gui.py" "\$@"
EOF
chmod +x "${MACOS}/launch"

# 复制图标
if [ -f "${PROJECT_DIR}/AppIcon.icns" ]; then
    cp "${PROJECT_DIR}/AppIcon.icns" "${RESOURCES}/AppIcon.icns"
fi

echo "✓ ${APP_DIR} 构建完成"
echo ""
echo "安装方法："
echo "  cp -r \"${APP_DIR}\" /Applications/"
echo ""
echo "或直接双击 dist/语音转文字.app 启动"
