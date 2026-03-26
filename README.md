# 语音转文字 · MLX Whisper

本地语音转文字工具，基于 [MLX Whisper](https://github.com/ml-explore/mlx-examples)，专为 Apple Silicon (M1/M2/M3/M4) 优化，中文优先，完全离线，无需 API。

## 功能

- 转录音频/视频文件（mp3, m4a, wav, mp4, mov 等）
- 麦克风实时录音转录
- 图形界面 + 命令行双模式
- 中文默认，支持多语言

## 环境要求

- macOS + Apple Silicon (M1 及以上)
- Python 3.10+
- ffmpeg

## 安装

```bash
# 安装 Python 3.12（如未安装）
brew install python@3.12

# 安装 ffmpeg（必须）
brew install ffmpeg

# 创建虚拟环境并安装依赖
python3.12 -m venv .venv
.venv/bin/pip install mlx-whisper sounddevice numpy
```

## 使用

### 图形界面

```bash
.venv/bin/python3 gui.py
```

首次运行会自动下载模型（约 1.5GB），之后本地缓存无需重复下载。

### 命令行

```bash
# 转录文件
.venv/bin/python3 transcribe.py audio.mp3

# 转录并保存结果
.venv/bin/python3 transcribe.py meeting.m4a -o result.txt

# 麦克风录音（30秒）
.venv/bin/python3 transcribe.py --record

# 麦克风录音（60秒）
.venv/bin/python3 transcribe.py --record --duration 60
```

## 桌面快捷方式

在 macOS 桌面创建可点击的 .app 图标：

```bash
mkdir -p ~/Desktop/语音转文字.app/Contents/MacOS
mkdir -p ~/Desktop/语音转文字.app/Contents/Resources
```

详见项目中的 `gui.py`。

## 模型说明

| 模型 | 大小 | 中文效果 | 速度 |
|------|------|----------|------|
| whisper-large-v3-turbo（默认） | 1.5GB | 最佳 | 快 |
| whisper-large-v3 | 3GB | 最佳 | 慢 |
| whisper-medium | 1.5GB | 良好 | 较快 |
| whisper-small | 500MB | 一般 | 最快 |
