#!/usr/bin/env python3
"""
audio-text: 本地语音转文字工具
基于 MLX Whisper (Apple Silicon 加速)，中文优先
"""

import argparse
import sys
import os
import tempfile
import time
from pathlib import Path

# 默认模型：large-v3-turbo 中文效果好，速度快
DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"


def transcribe_file(audio_path: str, model: str, language: str | None, output: str | None) -> None:
    """转录音频/视频文件"""
    import mlx_whisper

    path = Path(audio_path)
    if not path.exists():
        print(f"错误：文件不存在: {audio_path}", file=sys.stderr)
        sys.exit(1)

    print(f"模型: {model}")
    print(f"文件: {path.name}")
    print("转录中...\n")

    start = time.time()
    result = mlx_whisper.transcribe(
        str(path),
        path_or_hf_repo=model,
        language=language,
        verbose=False,
    )
    elapsed = time.time() - start

    text = result["text"].strip()

    print("=" * 60)
    print(text)
    print("=" * 60)
    print(f"\n耗时: {elapsed:.1f}s | 检测语言: {result.get('language', '未知')}")

    if output:
        out_path = Path(output)
        out_path.write_text(text, encoding="utf-8")
        print(f"已保存到: {out_path}")


def record_and_transcribe(model: str, language: str | None, duration: int) -> None:
    """录音并转录"""
    import sounddevice as sd
    import numpy as np
    import mlx_whisper

    SAMPLE_RATE = 16000
    print(f"开始录音，{duration} 秒后自动停止... (Ctrl+C 提前结束)")

    try:
        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        for remaining in range(duration, 0, -1):
            print(f"\r录音中... {remaining}s ", end="", flush=True)
            time.sleep(1)
        sd.wait()
        print("\r录音完成，转录中...     ")
    except KeyboardInterrupt:
        sd.stop()
        print("\r录音提前结束，转录中...")

    import wave
    import numpy as np

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    audio_data = audio.flatten()
    with wave.open(tmp_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        pcm = (audio_data * 32767).astype(np.int16)
        wf.writeframes(pcm.tobytes())

    try:
        start = time.time()
        result = mlx_whisper.transcribe(
            tmp_path,
            path_or_hf_repo=model,
            language=language,
            verbose=False,
        )
        elapsed = time.time() - start

        text = result["text"].strip()
        print("\n" + "=" * 60)
        print(text)
        print("=" * 60)
        print(f"\n耗时: {elapsed:.1f}s | 检测语言: {result.get('language', '未知')}")
    finally:
        os.unlink(tmp_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="本地语音转文字 (MLX Whisper, Apple Silicon)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 转录文件
  python transcribe.py audio.mp3
  python transcribe.py meeting.m4a -o output.txt

  # 麦克风录音转录（默认30秒）
  python transcribe.py --record
  python transcribe.py --record --duration 60

  # 指定语言（更快）
  python transcribe.py audio.mp3 --lang zh
  python transcribe.py audio.mp3 --lang en

  # 使用更小的模型（速度更快但效果稍差）
  python transcribe.py audio.mp3 --model mlx-community/whisper-small
        """,
    )

    parser.add_argument("file", nargs="?", help="音频/视频文件路径")
    parser.add_argument("--record", "-r", action="store_true", help="从麦克风录音")
    parser.add_argument("--duration", "-d", type=int, default=30, help="录音时长（秒，默认30）")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help=f"模型（默认: {DEFAULT_MODEL}）")
    parser.add_argument("--lang", "-l", default="zh", help="语言代码，如 zh/en/ja（默认中文）")
    parser.add_argument("--output", "-o", default=None, help="保存结果到文本文件")

    args = parser.parse_args()

    if not args.file and not args.record:
        parser.print_help()
        sys.exit(0)

    if args.record:
        record_and_transcribe(args.model, args.lang, args.duration)
    else:
        transcribe_file(args.file, args.model, args.lang, args.output)


if __name__ == "__main__":
    main()
