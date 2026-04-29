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

DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"


# ── 工具函数（供 gui.py 共享） ─────────────────────────────────


def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def filter_segments(segments: list[dict]) -> list[dict]:
    """过滤掉幻觉/低质量段落"""
    filtered = []
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        if seg.get("compression_ratio", 0) > 2.4:
            continue
        if seg.get("avg_logprob", 0) < -1.0:
            continue
        filtered.append(seg)
    return filtered


def format_segments(segments: list[dict], show_timestamps: bool = True) -> str:
    """格式化段落为可读文本"""
    lines = []
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        if show_timestamps:
            ts = format_timestamp(seg["start"])
            lines.append(f"[{ts}] {text}")
        else:
            lines.append(text)
    return "\n".join(lines)


def format_srt(segments: list[dict]) -> str:
    """格式化为 SRT 字幕"""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _srt_ts(seg["start"])
        end = _srt_ts(seg["end"])
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(seg.get("text", "").strip())
        lines.append("")
    return "\n".join(lines)


def format_vtt(segments: list[dict]) -> str:
    """格式化为 WebVTT 字幕"""
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _vtt_ts(seg["start"])
        end = _vtt_ts(seg["end"])
        lines.append(f"{start} --> {end}")
        lines.append(seg.get("text", "").strip())
        lines.append("")
    return "\n".join(lines)


def _srt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _vtt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def do_transcribe(audio_path: str, model: str, language: str | None,
                  initial_prompt: str | None = None,
                  use_builtin_vocab: bool = True) -> dict:
    """核心转录函数，返回 mlx_whisper 结果"""
    import mlx_whisper
    from domain_prompts import build_prompt

    if use_builtin_vocab:
        prompt = build_prompt(initial_prompt)
    else:
        prompt = initial_prompt

    return mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model,
        language=language,
        verbose=False,
        condition_on_previous_text=False,
        word_timestamps=True,
        hallucination_silence_threshold=1.0,
        initial_prompt=prompt,
        compression_ratio_threshold=2.4,
        logprob_threshold=-1.0,
        no_speech_threshold=0.6,
    )


# ── CLI 功能 ──────────────────────────────────────────────────


def transcribe_file(audio_path: str, model: str, language: str | None,
                    output: str | None, show_timestamps: bool = False,
                    initial_prompt: str | None = None) -> None:
    """转录音频/视频文件"""
    path = Path(audio_path)
    if not path.exists():
        print(f"错误：文件不存在: {audio_path}", file=sys.stderr)
        sys.exit(1)

    print(f"模型: {model}")
    print(f"文件: {path.name}")
    if initial_prompt:
        print(f"提示词: {initial_prompt}")
    print("转录中...\n")

    start = time.time()
    result = do_transcribe(str(path), model, language, initial_prompt)
    elapsed = time.time() - start

    segments = filter_segments(result.get("segments", []))
    output_text = format_segments(segments, show_timestamps=show_timestamps)

    print("=" * 60)
    print(output_text)
    print("=" * 60)
    print(f"\n耗时: {elapsed:.1f}s | 语言: {result.get('language', '未知')} | 段落: {len(segments)}")

    if output:
        out_path = Path(output)
        ext = out_path.suffix.lower()
        if ext == ".srt":
            content = format_srt(segments)
        elif ext == ".vtt":
            content = format_vtt(segments)
        else:
            content = output_text
        out_path.write_text(content, encoding="utf-8")
        print(f"已保存到: {out_path}")


def record_and_transcribe(model: str, language: str | None, duration: int,
                          initial_prompt: str | None = None) -> None:
    """录音并转录"""
    import sounddevice as sd
    import numpy as np

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

    audio_data = audio.flatten()

    if not np.any(audio_data):
        print("录音数据为空，请检查麦克风设置。")
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    with wave.open(tmp_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        pcm = (audio_data * 32767).astype(np.int16)
        wf.writeframes(pcm.tobytes())

    try:
        start = time.time()
        result = do_transcribe(tmp_path, model, language, initial_prompt)
        elapsed = time.time() - start

        segments = filter_segments(result.get("segments", []))
        output_text = format_segments(segments, show_timestamps=True)

        print("\n" + "=" * 60)
        print(output_text)
        print("=" * 60)
        print(f"\n耗时: {elapsed:.1f}s | 语言: {result.get('language', '未知')} | 段落: {len(segments)}")
    finally:
        os.unlink(tmp_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="本地语音转文字 (MLX Whisper, Apple Silicon)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 转录文件（带时间戳）
  python transcribe.py audio.mp3 -t

  # 提供领域词汇提升准确率
  python transcribe.py meeting.m4a -p "星巴克,SAP,数字化转型"

  # 导出为 SRT 字幕
  python transcribe.py audio.mp3 -o output.srt

  # 导出为 VTT 字幕
  python transcribe.py audio.mp3 -o output.vtt

  # 麦克风录音转录
  python transcribe.py --record --duration 60
        """,
    )

    parser.add_argument("file", nargs="?", help="音频/视频文件路径")
    parser.add_argument("--record", "-r", action="store_true", help="从麦克风录音")
    parser.add_argument("--duration", "-d", type=int, default=30, help="录音时长（秒，默认30）")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help=f"模型（默认: {DEFAULT_MODEL}）")
    parser.add_argument("--lang", "-l", default="zh", help="语言代码，如 zh/en/ja（默认中文）")
    parser.add_argument("--output", "-o", default=None, help="保存结果（.txt/.srt/.vtt）")
    parser.add_argument("--timestamps", "-t", action="store_true", help="显示时间戳")
    parser.add_argument("--initial-prompt", "-p", default=None, help="初始提示词（领域词汇，逗号分隔）")

    args = parser.parse_args()

    if not args.file and not args.record:
        parser.print_help()
        sys.exit(0)

    if args.record:
        record_and_transcribe(args.model, args.lang, args.duration, args.initial_prompt)
    else:
        transcribe_file(args.file, args.model, args.lang, args.output,
                        args.timestamps, args.initial_prompt)


if __name__ == "__main__":
    main()
