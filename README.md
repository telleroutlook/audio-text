# 语音转文字 · MLX Whisper

本地语音转文字工具，基于 [MLX Whisper](https://github.com/ml-explore/mlx-examples)，专为 Apple Silicon (M1/M2/M3/M4) 优化，中文优先，完全离线，无需 API。

## 功能

- 转录音频/视频文件（mp3, m4a, wav, mp4, mov, ogg, flac, aac, mkv）
- 麦克风实时录音转录
- 图形界面 + 命令行双模式
- 中文默认，支持多语言（英/日/粤语等）
- 带时间戳分段输出，支持 SRT/VTT 字幕导出
- 长音频反幻觉优化（过滤重复/低质量段落）
- 领域提示词提升专业术语准确率

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
.venv/bin/pip install -r requirements.txt
```

## 使用

### 图形界面

```bash
.venv/bin/python3 gui.py
```

首次运行会自动下载模型（约 1.5GB），之后本地缓存无需重复下载。

### 命令行

```bash
# 转录文件（带时间戳）
.venv/bin/python3 transcribe.py audio.mp3 -t

# 提供领域词汇提升准确率
.venv/bin/python3 transcribe.py meeting.m4a -t -p "星巴克,SAP,数字化转型"

# 导出为 SRT 字幕
.venv/bin/python3 transcribe.py audio.mp3 -o output.srt

# 导出为 VTT 字幕
.venv/bin/python3 transcribe.py audio.mp3 -o output.vtt

# 保存为文本
.venv/bin/python3 transcribe.py audio.mp3 -t -o result.txt

# 麦克风录音（30秒）
.venv/bin/python3 transcribe.py --record

# 麦克风录音（60秒）
.venv/bin/python3 transcribe.py --record --duration 60
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `file` | 音频/视频文件路径 |
| `--record, -r` | 从麦克风录音 |
| `--duration, -d` | 录音时长（秒，默认30） |
| `--model, -m` | 模型选择 |
| `--lang, -l` | 语言代码（默认 zh） |
| `--output, -o` | 保存结果（.txt/.srt/.vtt） |
| `--timestamps, -t` | 显示时间戳 |
| `--initial-prompt, -p` | 领域提示词 |

## 打包为 macOS 应用

```bash
.venv/bin/pip install py2app
.venv/bin/python3 setup.py py2app
```

生成的应用在 `dist/语音转文字.app`，可直接拖入 Applications 文件夹。

## 模型说明

| 模型 | 大小 | 中文效果 | 速度 |
|------|------|----------|------|
| whisper-large-v3-turbo（默认） | 1.5GB | 最佳 | 快 |
| whisper-large-v3 | 3GB | 最佳 | 慢 |
| whisper-medium | 1.5GB | 良好 | 较快 |
| whisper-small | 500MB | 一般 | 最快 |

## 技术细节

- 使用 `condition_on_previous_text=False` 防止长音频错误级联
- 启用 `word_timestamps` + `hallucination_silence_threshold` 检测并跳过幻觉段落
- 后处理过滤 `compression_ratio > 2.4` 的重复输出
- 过滤 `avg_logprob < -1.0` 的低置信度段落
