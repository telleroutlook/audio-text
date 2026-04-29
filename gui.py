#!/usr/bin/env python3
"""
audio-text GUI: 本地语音转文字图形界面
基于 MLX Whisper (Apple Silicon 加速)
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import time
import os
import tempfile
import wave
from pathlib import Path

from transcribe import (
    DEFAULT_MODEL, do_transcribe, filter_segments,
    format_segments, format_srt, format_vtt,
)
from domain_prompts import PRESET_PROMPTS

MODELS = [
    ("large-v3-turbo (推荐，中文最佳)", "mlx-community/whisper-large-v3-turbo"),
    ("large-v3 (最高精度，较慢)", "mlx-community/whisper-large-v3"),
    ("medium (速度与精度均衡)", "mlx-community/whisper-medium"),
    ("small (速度快，精度稍低)", "mlx-community/whisper-small"),
]

LANGUAGES = [
    ("中文", "zh"),
    ("自动检测", None),
    ("英文", "en"),
    ("日文", "ja"),
    ("粤语", "yue"),
]


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("语音转文字 · MLX Whisper")
        self.resizable(True, True)
        self.minsize(640, 560)

        self._recording = False
        self._transcribing = False
        self._transcribe_start: float = 0.0
        self._record_thread: threading.Thread | None = None
        self._record_start: float = 0.0
        self._last_segments: list[dict] = []

        self._build_ui()
        self._center_window()

    def _center_window(self) -> None:
        self.update_idletasks()
        w, h = 720, 620
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        # ── 顶部设置区 ──────────────────────────────
        cfg = ttk.LabelFrame(self, text="设置", padding=10)
        cfg.pack(fill="x", padx=12, pady=(12, 4))

        # 模型选择
        ttk.Label(cfg, text="模型:").grid(row=0, column=0, sticky="w")
        self._model_var = tk.StringVar(value=DEFAULT_MODEL)
        model_cb = ttk.Combobox(cfg, textvariable=self._model_var, width=42, state="readonly")
        model_cb["values"] = [m[0] for m in MODELS]
        model_cb.current(0)
        model_cb.grid(row=0, column=1, columnspan=2, sticky="w", padx=(8, 0))
        model_cb.bind("<<ComboboxSelected>>", self._on_model_select)
        self._model_labels = [m[0] for m in MODELS]
        self._model_ids = [m[1] for m in MODELS]

        # 语言选择 + 时间戳开关
        ttk.Label(cfg, text="语言:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self._lang_var = tk.StringVar(value="中文")
        lang_cb = ttk.Combobox(cfg, textvariable=self._lang_var, width=12, state="readonly")
        lang_cb["values"] = [l[0] for l in LANGUAGES]
        lang_cb.current(0)
        lang_cb.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        self._lang_labels = [l[0] for l in LANGUAGES]
        self._lang_codes = [l[1] for l in LANGUAGES]

        self._timestamps_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cfg, text="显示时间戳", variable=self._timestamps_var).grid(
            row=1, column=2, sticky="w", padx=(16, 0), pady=(8, 0))

        # 提示词预设 + 自定义输入
        ttk.Label(cfg, text="提示词:").grid(row=2, column=0, sticky="w", pady=(8, 0))

        prompt_frame = ttk.Frame(cfg)
        prompt_frame.grid(row=2, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=(8, 0))

        self._preset_var = tk.StringVar(value="无")
        self._preset_labels = [p[0] for p in PRESET_PROMPTS]
        self._preset_values = [p[1] for p in PRESET_PROMPTS]
        preset_cb = ttk.Combobox(prompt_frame, textvariable=self._preset_var,
                                  width=18, state="readonly")
        preset_cb["values"] = self._preset_labels
        preset_cb.current(0)
        preset_cb.pack(side="left")
        preset_cb.bind("<<ComboboxSelected>>", self._on_preset_select)

        ttk.Label(prompt_frame, text="或自定义:").pack(side="left", padx=(8, 4))
        self._prompt_var = tk.StringVar(value="")
        ttk.Entry(prompt_frame, textvariable=self._prompt_var, width=24).pack(side="left")

        # ── 文件转录区 ──────────────────────────────
        file_frame = ttk.LabelFrame(self, text="文件转录", padding=10)
        file_frame.pack(fill="x", padx=12, pady=4)

        self._file_var = tk.StringVar(value="")
        ttk.Entry(file_frame, textvariable=self._file_var, width=52).pack(
            side="left", fill="x", expand=True)
        ttk.Button(file_frame, text="选择文件", command=self._pick_file).pack(side="left", padx=(6, 0))
        ttk.Button(file_frame, text="开始转录", command=self._start_file_transcribe).pack(side="left", padx=(6, 0))

        # ── 录音区 ──────────────────────────────────
        rec_frame = ttk.LabelFrame(self, text="麦克风录音", padding=10)
        rec_frame.pack(fill="x", padx=12, pady=4)

        ttk.Label(rec_frame, text="时长(秒):").pack(side="left")
        self._duration_var = tk.IntVar(value=30)
        ttk.Spinbox(rec_frame, from_=5, to=300, textvariable=self._duration_var, width=6).pack(
            side="left", padx=(4, 16))

        self._rec_btn = ttk.Button(rec_frame, text="开始录音", command=self._toggle_record)
        self._rec_btn.pack(side="left")

        self._rec_label = ttk.Label(rec_frame, text="", foreground="red")
        self._rec_label.pack(side="left", padx=(12, 0))

        # ── 进度条 ──────────────────────────────────
        self._progress = ttk.Progressbar(self, mode="indeterminate")
        self._progress.pack(fill="x", padx=12, pady=(4, 0))

        # ── 结果区 ──────────────────────────────────
        result_frame = ttk.LabelFrame(self, text="转录结果", padding=10)
        result_frame.pack(fill="both", expand=True, padx=12, pady=(4, 4))

        self._result_text = scrolledtext.ScrolledText(
            result_frame, wrap="word", font=("PingFang SC", 13), state="disabled"
        )
        self._result_text.pack(fill="both", expand=True)

        # ── 底部按钮 ────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=12, pady=(0, 12))

        self._status_var = tk.StringVar(value="就绪")
        self._status_label = tk.Label(btn_frame, textvariable=self._status_var, fg="gray", bg=self.cget("bg"))
        self._status_label.pack(side="left")
        ttk.Button(btn_frame, text="复制结果", command=self._copy_result).pack(side="right")
        ttk.Button(btn_frame, text="保存文本", command=self._save_result).pack(side="right", padx=(0, 6))
        ttk.Button(btn_frame, text="清空", command=self._clear_result).pack(side="right", padx=(0, 6))

    # ── 事件处理 ──────────────────────────────────────

    def _on_model_select(self, _event: tk.Event) -> None:
        label = self._model_var.get()
        idx = self._model_labels.index(label)
        self._model_var.set(self._model_ids[idx])

    def _on_preset_select(self, _event: tk.Event) -> None:
        label = self._preset_var.get()
        idx = self._preset_labels.index(label)
        preset_text = self._preset_values[idx]
        self._prompt_var.set(preset_text)

    def _get_prompt(self) -> str | None:
        text = self._prompt_var.get().strip()
        return text or None

    def _get_model(self) -> str:
        val = self._model_var.get()
        if val in self._model_ids:
            return val
        try:
            idx = self._model_labels.index(val)
            return self._model_ids[idx]
        except ValueError:
            return DEFAULT_MODEL

    def _get_lang(self) -> str | None:
        label = self._lang_var.get()
        try:
            idx = self._lang_labels.index(label)
            return self._lang_codes[idx]
        except ValueError:
            return None

    def _pick_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择音频/视频文件",
            filetypes=[
                ("音频/视频文件", "*.mp3 *.m4a *.wav *.ogg *.flac *.mp4 *.mov *.mkv *.aac"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            self._file_var.set(path)

    def _start_file_transcribe(self) -> None:
        path = self._file_var.get().strip()
        if not path:
            self._set_status("请先选择文件", "red")
            return
        if not Path(path).exists():
            self._set_status("文件不存在", "red")
            return
        self._run_in_thread(lambda: self._do_transcribe(path))

    # ── 录音 ──────────────────────────────────────────

    def _toggle_record(self) -> None:
        if not self._recording:
            self._start_record()
        else:
            self._stop_record()

    def _start_record(self) -> None:
        self._recording = True
        self._rec_btn.config(text="停止录音")
        self._record_start = time.time()
        self._record_thread = threading.Thread(target=self._do_record, daemon=True)
        self._record_thread.start()
        self._update_rec_label()

    def _stop_record(self) -> None:
        self._recording = False
        self._rec_btn.config(text="开始录音")
        self._rec_label.config(text="")

    def _update_rec_label(self) -> None:
        if self._recording:
            elapsed = int(time.time() - self._record_start)
            self._rec_label.config(text=f"录音中 {elapsed}s")
            self.after(500, self._update_rec_label)

    def _do_record(self) -> None:
        import sounddevice as sd
        import numpy as np

        SAMPLE_RATE = 16000
        duration = self._duration_var.get()
        self._set_status("录音中...", "red")

        chunks = []
        block_size = SAMPLE_RATE // 2

        def callback(indata: "np.ndarray", frames: int, t, status) -> None:
            chunks.append(indata.copy())

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            blocksize=block_size, callback=callback):
            start_time = time.time()
            while self._recording and (time.time() - start_time) < duration:
                time.sleep(0.1)

        self._recording = False
        self.after(0, lambda: self._rec_btn.config(text="开始录音"))
        self.after(0, lambda: self._rec_label.config(text=""))

        if not chunks:
            self._set_status("录音失败", "red")
            return

        import numpy as np
        audio = np.concatenate(chunks, axis=0).flatten()
        self._set_status("录音完成，转录中...", "blue")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        with wave.open(tmp_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            pcm = (audio * 32767).astype(np.int16)
            wf.writeframes(pcm.tobytes())

        try:
            self.after(0, lambda: self._progress.start(10))
            self._do_transcribe(tmp_path)
        finally:
            os.unlink(tmp_path)

    # ── 转录 ──────────────────────────────────────────

    def _run_in_thread(self, fn) -> None:
        self._progress.start(10)
        self._set_status("准备中，首次运行需下载模型（约1.5GB），请耐心等待...", "blue")
        self._transcribe_start = time.time()
        self._transcribing = True
        self._tick_timer()
        threading.Thread(target=fn, daemon=True).start()

    def _tick_timer(self) -> None:
        if self._transcribing:
            elapsed = int(time.time() - self._transcribe_start)
            self._set_status(f"转录中... 已用时 {elapsed}s，请耐心等待", "blue")
            self.after(1000, self._tick_timer)

    def _do_transcribe(self, audio_path: str) -> None:
        try:
            model = self._get_model()
            lang = self._get_lang()
            prompt = self._get_prompt()

            self._set_status("模型加载中...", "blue")
            self._transcribe_start = time.time()
            self._transcribing = True

            result = do_transcribe(audio_path, model, lang, prompt)

            self._transcribing = False
            elapsed = time.time() - self._transcribe_start

            segments = filter_segments(result.get("segments", []))
            self._last_segments = segments
            show_ts = self._timestamps_var.get()
            text = format_segments(segments, show_timestamps=show_ts)
            detected = result.get("language", "未知")

            self.after(0, lambda: self._show_result(text, elapsed, detected, len(segments)))
        except Exception as e:
            self._transcribing = False
            err = str(e)
            self.after(0, lambda: self._set_status(f"错误: {err}", "red"))
        finally:
            self._transcribing = False
            self.after(0, self._progress.stop)

    def _show_result(self, text: str, elapsed: float, detected: str, seg_count: int) -> None:
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.insert("end", text)
        self._result_text.config(state="disabled")
        self._set_status(f"完成  耗时 {elapsed:.1f}s  语言: {detected}  段落: {seg_count}", "green")

    # ── 工具按钮 ──────────────────────────────────────

    def _copy_result(self) -> None:
        text = self._result_text.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status("已复制到剪贴板", "green")

    def _save_result(self) -> None:
        text = self._result_text.get("1.0", "end").strip()
        if not text:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("文本文件", "*.txt"),
                ("SRT字幕", "*.srt"),
                ("VTT字幕", "*.vtt"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            ext = Path(path).suffix.lower()
            if ext == ".srt" and self._last_segments:
                content = format_srt(self._last_segments)
            elif ext == ".vtt" and self._last_segments:
                content = format_vtt(self._last_segments)
            else:
                content = text
            Path(path).write_text(content, encoding="utf-8")
            self._set_status(f"已保存: {Path(path).name}", "green")

    def _clear_result(self) -> None:
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.config(state="disabled")
        self._last_segments = []
        self._set_status("就绪", "gray")

    def _set_status(self, msg: str, color: str = "gray") -> None:
        def _update():
            self._status_var.set(msg)
            self._status_label.config(fg=color)
        self.after(0, _update)


if __name__ == "__main__":
    app = App()
    app.mainloop()
