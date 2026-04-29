#!/usr/bin/env python3
"""
audio-text GUI: 本地语音转文字图形界面
基于 MLX Whisper (Apple Silicon 加速)
"""

import tkinter as tk
from tkinter import filedialog
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
from domain_prompts import build_prompt

# ── 颜色系统 ──────────────────────────────────────────────────
BG        = "#1C1C1E"   # 主背景（macOS 深色）
PANEL     = "#2C2C2E"   # 卡片背景
PANEL2    = "#3A3A3C"   # 次级卡片 / hover
BORDER    = "#48484A"   # 边框
ACCENT    = "#0A84FF"   # 主色调（Apple Blue）
ACCENT_H  = "#409CFF"   # hover
SUCCESS   = "#30D158"   # 绿
DANGER    = "#FF453A"   # 红
TEXT      = "#F2F2F7"   # 主文字
TEXT2     = "#8E8E93"   # 次要文字
TEXT3     = "#636366"   # 提示文字

MODELS = [
    ("large-v3-turbo  ·  推荐，中文最佳", "mlx-community/whisper-large-v3-turbo"),
    ("large-v3  ·  最高精度，较慢",        "mlx-community/whisper-large-v3"),
    ("medium  ·  速度与精度均衡",           "mlx-community/whisper-medium"),
    ("small  ·  速度快，精度稍低",          "mlx-community/whisper-small"),
]

LANGUAGES = [
    ("中文",   "zh"),
    ("自动检测", None),
    ("英文",   "en"),
    ("日文",   "ja"),
    ("粤语",   "yue"),
]


# ── 自定义控件 ────────────────────────────────────────────────

class FlatButton(tk.Label):
    """扁平风格按钮"""
    def __init__(self, parent, text, command, bg=ACCENT, fg=TEXT,
                 hover_bg=ACCENT_H, padx=16, pady=7, radius=8, font_size=13, **kw):
        super().__init__(parent, text=text, bg=bg, fg=fg,
                         font=("PingFang SC", font_size, "normal"),
                         padx=padx, pady=pady, cursor="hand2", **kw)
        self._bg = bg
        self._hover_bg = hover_bg
        self._command = command
        self.bind("<Enter>",    lambda e: self.config(bg=hover_bg))
        self.bind("<Leave>",    lambda e: self.config(bg=bg))
        self.bind("<Button-1>", lambda e: command())

    def set_bg(self, bg, hover_bg):
        self._bg = bg
        self._hover_bg = hover_bg
        self.config(bg=bg)
        self.bind("<Enter>", lambda e: self.config(bg=hover_bg))
        self.bind("<Leave>", lambda e: self.config(bg=bg))


class StyledCombo(tk.Frame):
    """自定义下拉框"""
    def __init__(self, parent, values, width=200, **kw):
        super().__init__(parent, bg=PANEL2, highlightbackground=BORDER,
                         highlightthickness=1, **kw)
        self._values = values
        self._var = tk.StringVar(value=values[0])
        self._menu_open = False

        self._label = tk.Label(self, textvariable=self._var, bg=PANEL2, fg=TEXT,
                               font=("PingFang SC", 13), anchor="w",
                               width=width, cursor="hand2", padx=10, pady=6)
        self._label.pack(side="left", fill="x", expand=True)

        arrow = tk.Label(self, text="▾", bg=PANEL2, fg=TEXT2,
                         font=("PingFang SC", 11), padx=6, cursor="hand2")
        arrow.pack(side="right")

        self._label.bind("<Button-1>", self._toggle)
        arrow.bind("<Button-1>", self._toggle)

    def get(self):
        return self._var.get()

    def set(self, v):
        self._var.set(v)

    def _toggle(self, event=None):
        menu = tk.Toplevel(self)
        menu.overrideredirect(True)
        menu.config(bg=PANEL2)
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()
        menu.geometry(f"{w}x{min(len(self._values)*36, 216)}+{x}+{y}")

        frame = tk.Frame(menu, bg=PANEL2)
        frame.pack(fill="both", expand=True)

        for v in self._values:
            item = tk.Label(frame, text=v, bg=PANEL2, fg=TEXT,
                            font=("PingFang SC", 13), anchor="w",
                            padx=12, pady=6, cursor="hand2")
            item.pack(fill="x")
            item.bind("<Enter>", lambda e, w=item: w.config(bg=PANEL))
            item.bind("<Leave>", lambda e, w=item: w.config(bg=PANEL2))
            item.bind("<Button-1>", lambda e, val=v, m=menu: self._select(val, m))

        menu.bind("<FocusOut>", lambda e: menu.destroy())
        menu.focus_set()

    def _select(self, val, menu):
        self._var.set(val)
        menu.destroy()
        if hasattr(self, "_on_select"):
            self._on_select(val)


class ToggleSwitch(tk.Canvas):
    """iOS 风格开关"""
    def __init__(self, parent, variable: tk.BooleanVar, **kw):
        super().__init__(parent, width=44, height=24, bg=PANEL,
                         highlightthickness=0, cursor="hand2", **kw)
        self._var = variable
        self._draw()
        self.bind("<Button-1>", self._toggle)
        variable.trace_add("write", lambda *_: self._draw())

    def _draw(self):
        self.delete("all")
        on = self._var.get()
        track_color = ACCENT if on else BORDER
        self.create_rounded_rect(2, 4, 42, 20, 8, fill=track_color, outline="")
        knob_x = 28 if on else 6
        self.create_oval(knob_x, 3, knob_x + 18, 21, fill=TEXT, outline="")

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kw):
        self.create_arc(x1, y1, x1+2*r, y1+2*r, start=90,  extent=90,  **kw)
        self.create_arc(x2-2*r, y1, x2, y1+2*r, start=0,   extent=90,  **kw)
        self.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90,  **kw)
        self.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90,  **kw)
        self.create_rectangle(x1+r, y1, x2-r, y2, **kw)
        self.create_rectangle(x1, y1+r, x2, y2-r, **kw)

    def _toggle(self, _=None):
        self._var.set(not self._var.get())


# ── 主应用 ────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("语音转文字")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(780, 600)

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
        w, h = 860, 660
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _card(self, parent, **kw) -> tk.Frame:
        return tk.Frame(parent, bg=PANEL, **kw)

    def _label(self, parent, text, size=13, color=TEXT, bold=False, **kw) -> tk.Label:
        weight = "bold" if bold else "normal"
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("PingFang SC", size, weight), **kw)

    def _section_title(self, parent, text) -> tk.Label:
        return self._label(parent, text, size=11, color=TEXT3)

    def _build_ui(self) -> None:
        # ── 顶部标题栏 ─────────────────────────────────
        header = tk.Frame(self, bg=PANEL, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        self._label(header, "语音转文字", size=17, bold=True).pack(side="left", padx=20)
        self._label(header, "MLX Whisper · Apple Silicon", size=12, color=TEXT3).pack(
            side="left", padx=(0, 0), pady=(4, 0))

        # ── 主体：左侧控制 + 右侧结果 ──────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        left = tk.Frame(body, bg=BG, width=280)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_right(right)

        # ── 状态栏 ─────────────────────────────────────
        status_bar = tk.Frame(self, bg=PANEL, height=30)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)

        self._status_var = tk.StringVar(value="就绪")
        self._status_dot = tk.Label(status_bar, text="●", bg=PANEL, fg=TEXT3,
                                    font=("PingFang SC", 10))
        self._status_dot.pack(side="left", padx=(12, 4))
        self._status_label = tk.Label(status_bar, textvariable=self._status_var,
                                      bg=PANEL, fg=TEXT2, font=("PingFang SC", 11))
        self._status_label.pack(side="left")

    def _build_left(self, parent) -> None:
        # ── 模型卡片 ───────────────────────────────────
        card1 = self._card(parent)
        card1.pack(fill="x", pady=(0, 8))
        inner1 = tk.Frame(card1, bg=PANEL)
        inner1.pack(fill="x", padx=14, pady=12)

        self._section_title(inner1, "模型").pack(anchor="w")
        self._model_labels = [m[0] for m in MODELS]
        self._model_ids    = [m[1] for m in MODELS]
        self._model_combo  = StyledCombo(inner1, self._model_labels, width=22)
        self._model_combo.pack(fill="x", pady=(4, 0))

        sep1 = tk.Frame(card1, bg=BORDER, height=1)
        sep1.pack(fill="x")

        # ── 语言 + 时间戳 ──────────────────────────────
        inner2 = tk.Frame(card1, bg=PANEL)
        inner2.pack(fill="x", padx=14, pady=12)

        row_lang = tk.Frame(inner2, bg=PANEL)
        row_lang.pack(fill="x")
        self._section_title(row_lang, "语言").pack(side="left")

        self._lang_labels = [l[0] for l in LANGUAGES]
        self._lang_codes  = [l[1] for l in LANGUAGES]
        self._lang_combo  = StyledCombo(row_lang, self._lang_labels, width=10)
        self._lang_combo.pack(side="right")

        row_ts = tk.Frame(inner2, bg=PANEL)
        row_ts.pack(fill="x", pady=(10, 0))
        self._section_title(row_ts, "显示时间戳").pack(side="left")
        self._timestamps_var = tk.BooleanVar(value=True)
        ToggleSwitch(row_ts, self._timestamps_var).pack(side="right")

        sep2 = tk.Frame(card1, bg=BORDER, height=1)
        sep2.pack(fill="x")

        # ── 词汇设置 ───────────────────────────────────
        inner3 = tk.Frame(card1, bg=PANEL)
        inner3.pack(fill="x", padx=14, pady=12)

        row_vocab = tk.Frame(inner3, bg=PANEL)
        row_vocab.pack(fill="x")
        self._section_title(row_vocab, "内置词汇").pack(side="left")
        self._builtin_var = tk.StringVar(value="数字化")
        self._builtin_combo = StyledCombo(row_vocab, ["数字化", "无"], width=8)
        self._builtin_combo.pack(side="right")

        self._section_title(inner3, "自定义词汇（逗号分隔）").pack(anchor="w", pady=(10, 4))
        self._prompt_var = tk.StringVar(value="")
        prompt_entry = tk.Entry(inner3, textvariable=self._prompt_var,
                                bg=PANEL2, fg=TEXT, insertbackground=TEXT,
                                relief="flat", font=("PingFang SC", 12),
                                highlightbackground=BORDER, highlightthickness=1)
        prompt_entry.pack(fill="x", ipady=5)

        # ── 文件转录卡片 ───────────────────────────────
        card2 = self._card(parent)
        card2.pack(fill="x", pady=(0, 8))
        inner4 = tk.Frame(card2, bg=PANEL)
        inner4.pack(fill="x", padx=14, pady=12)

        self._section_title(inner4, "转录音频文件").pack(anchor="w")

        self._file_var = tk.StringVar(value="")
        file_row = tk.Frame(inner4, bg=PANEL)
        file_row.pack(fill="x", pady=(6, 8))

        file_entry = tk.Entry(file_row, textvariable=self._file_var,
                              bg=PANEL2, fg=TEXT2, insertbackground=TEXT,
                              relief="flat", font=("PingFang SC", 11),
                              highlightbackground=BORDER, highlightthickness=1)
        file_entry.pack(side="left", fill="x", expand=True, ipady=4)

        FlatButton(file_row, "浏览", self._pick_file,
                   bg=PANEL2, fg=TEXT, hover_bg=BORDER,
                   padx=10, pady=4, font_size=12).pack(side="left", padx=(6, 0))

        FlatButton(inner4, "开始转录  →", self._start_file_transcribe,
                   padx=0, pady=8, font_size=13).pack(fill="x")

        # ── 麦克风录音卡片 ─────────────────────────────
        card3 = self._card(parent)
        card3.pack(fill="x", pady=(0, 8))
        inner5 = tk.Frame(card3, bg=PANEL)
        inner5.pack(fill="x", padx=14, pady=12)

        self._section_title(inner5, "麦克风录音").pack(anchor="w", pady=(0, 6))

        self._rec_btn = FlatButton(inner5, "● 开始录音", self._toggle_record,
                                   bg=DANGER, hover_bg="#FF6961",
                                   padx=0, pady=8, font_size=13)
        self._rec_btn.pack(fill="x")

        self._rec_label = tk.Label(inner5, text="", bg=PANEL, fg=DANGER,
                                   font=("PingFang SC", 12))
        self._rec_label.pack(pady=(6, 0))

        hint_text = ("提示：Voice Memos 录音请在备忘录 App\n"
                     "长按录音 → 共享 → 存储到「下载」\n"
                     "再点「浏览」选择文件转录")
        self._label(inner5, hint_text, size=11, color=TEXT3).pack(
            anchor="w", pady=(8, 0))

        # ── 进度条 ─────────────────────────────────────
        self._progress_var = tk.DoubleVar(value=0)
        self._progress_active = False
        self._progress_canvas = tk.Canvas(parent, height=3, bg=BG,
                                          highlightthickness=0)
        self._progress_canvas.pack(fill="x", pady=(0, 4))

    def _build_right(self, parent) -> None:
        # ── 结果标题行 ─────────────────────────────────
        title_row = tk.Frame(parent, bg=BG)
        title_row.pack(fill="x", pady=(0, 8))
        self._label(title_row, "转录结果", size=15, bold=True).pack(side="left")

        btn_row = tk.Frame(title_row, bg=BG)
        btn_row.pack(side="right")
        FlatButton(btn_row, "清空",   self._clear_result,
                   bg=PANEL2, fg=TEXT2, hover_bg=BORDER,
                   padx=12, pady=5, font_size=12).pack(side="left", padx=(0, 6))
        FlatButton(btn_row, "保存",   self._save_result,
                   bg=PANEL2, fg=TEXT, hover_bg=BORDER,
                   padx=12, pady=5, font_size=12).pack(side="left", padx=(0, 6))
        FlatButton(btn_row, "复制",   self._copy_result,
                   bg=ACCENT, fg=TEXT, hover_bg=ACCENT_H,
                   padx=12, pady=5, font_size=12).pack(side="left")

        # ── 结果文本区 ─────────────────────────────────
        text_frame = tk.Frame(parent, bg=PANEL,
                              highlightbackground=BORDER, highlightthickness=1)
        text_frame.pack(fill="both", expand=True)

        self._result_text = tk.Text(
            text_frame, wrap="word",
            font=("PingFang SC", 14),
            bg=PANEL, fg=TEXT,
            insertbackground=TEXT,
            selectbackground=ACCENT,
            selectforeground=TEXT,
            relief="flat",
            padx=16, pady=14,
            state="disabled",
            spacing1=3, spacing3=3,
        )
        scrollbar = tk.Scrollbar(text_frame, orient="vertical",
                                 command=self._result_text.yview,
                                 bg=PANEL, troughcolor=PANEL,
                                 activebackground=BORDER)
        self._result_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._result_text.pack(side="left", fill="both", expand=True)

    # ── 进度动画 ──────────────────────────────────────────────

    def _start_progress(self) -> None:
        self._progress_active = True
        self._progress_pos = 0.0
        self._animate_progress()

    def _stop_progress(self) -> None:
        self._progress_active = False
        self._progress_canvas.delete("all")

    def _animate_progress(self) -> None:
        if not self._progress_active:
            return
        c = self._progress_canvas
        w = c.winfo_width() or 300
        c.delete("all")
        c.create_rectangle(0, 0, w, 3, fill=PANEL2, outline="")
        bar_w = int(w * 0.3)
        x = int((self._progress_pos % 1.0) * (w + bar_w)) - bar_w
        c.create_rectangle(x, 0, x + bar_w, 3, fill=ACCENT, outline="")
        self._progress_pos += 0.012
        self.after(16, self._animate_progress)

    # ── 事件处理 ──────────────────────────────────────────────

    def _get_model(self) -> str:
        label = self._model_combo.get()
        try:
            return self._model_ids[self._model_labels.index(label)]
        except ValueError:
            return DEFAULT_MODEL

    def _get_lang(self) -> str | None:
        label = self._lang_combo.get()
        try:
            return self._lang_codes[self._lang_labels.index(label)]
        except ValueError:
            return None

    def _get_prompt(self) -> tuple[str | None, bool]:
        use_builtin = self._builtin_combo.get() == "数字化"
        custom = self._prompt_var.get().strip()
        return (custom or None, use_builtin)

    def _pick_file(self) -> None:
        init_dir = str(Path.home() / "Downloads")
        path = filedialog.askopenfilename(
            title="选择音频/视频文件",
            initialdir=init_dir,
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
            self._set_status("请先选择音频文件", "warn")
            return
        if not Path(path).exists():
            self._set_status("文件不存在", "error")
            return
        self._run_in_thread(lambda: self._do_transcribe(path))

    # ── 录音 ──────────────────────────────────────────────────

    def _toggle_record(self) -> None:
        if not self._recording:
            self._start_record()
        else:
            self._stop_record()

    def _start_record(self) -> None:
        self._recording = True
        self._rec_btn.config(text="■  停止录音")
        self._rec_btn.set_bg("#636366", "#7C7C80")
        self._record_start = time.time()
        self._record_thread = threading.Thread(target=self._do_record, daemon=True)
        self._record_thread.start()
        self._update_rec_label()

    def _stop_record(self) -> None:
        self._recording = False

    def _update_rec_label(self) -> None:
        if self._recording:
            elapsed = int(time.time() - self._record_start)
            m, s = divmod(elapsed, 60)
            self._rec_label.config(text=f"录音中  {m:02d}:{s:02d}", fg=DANGER)
            self.after(500, self._update_rec_label)

    def _do_record(self) -> None:
        import sounddevice as sd
        import numpy as np

        SAMPLE_RATE = 16000
        self._set_status("录音中...", "error")

        chunks: list = []
        block_size = SAMPLE_RATE // 2

        def callback(indata, frames, t, status) -> None:
            chunks.append(indata.copy())

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            blocksize=block_size, callback=callback):
            while self._recording:
                time.sleep(0.1)

        self._recording = False
        self.after(0, lambda: self._rec_btn.config(text="● 开始录音"))
        self.after(0, lambda: self._rec_btn.set_bg(DANGER, "#FF6961"))
        self.after(0, lambda: self._rec_label.config(text=""))

        if not chunks:
            self._set_status("录音失败", "error")
            return

        audio = np.concatenate(chunks, axis=0).flatten()
        self._set_status("录音完成，转录中...", "info")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        with wave.open(tmp_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            pcm = (audio * 32767).astype(np.int16)
            wf.writeframes(pcm.tobytes())

        try:
            self.after(0, self._start_progress)
            self._do_transcribe(tmp_path)
        finally:
            os.unlink(tmp_path)

    # ── 转录 ──────────────────────────────────────────────────

    def _run_in_thread(self, fn) -> None:
        self._start_progress()
        self._set_status("准备中，首次运行需下载模型（约1.5 GB）...", "info")
        self._transcribe_start = time.time()
        self._transcribing = True
        self._tick_timer()
        threading.Thread(target=fn, daemon=True).start()

    def _tick_timer(self) -> None:
        if self._transcribing:
            elapsed = int(time.time() - self._transcribe_start)
            m, s = divmod(elapsed, 60)
            self._set_status(f"转录中  {m:02d}:{s:02d}", "info")
            self.after(1000, self._tick_timer)

    def _do_transcribe(self, audio_path: str) -> None:
        try:
            model = self._get_model()
            lang = self._get_lang()
            prompt, use_builtin = self._get_prompt()

            self._transcribe_start = time.time()
            self._transcribing = True

            result = do_transcribe(audio_path, model, lang, prompt, use_builtin)

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
            self.after(0, lambda: self._set_status(f"错误: {err}", "error"))
        finally:
            self._transcribing = False
            self.after(0, self._stop_progress)

    def _show_result(self, text: str, elapsed: float, detected: str, seg_count: int) -> None:
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.insert("end", text)
        self._result_text.config(state="disabled")
        m, s = divmod(int(elapsed), 60)
        self._set_status(
            f"完成  耗时 {m:02d}:{s:02d}  ·  语言: {detected}  ·  {seg_count} 段", "success")

    # ── 工具按钮 ──────────────────────────────────────────────

    def _copy_result(self) -> None:
        text = self._result_text.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status("已复制到剪贴板", "success")

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
            self._set_status(f"已保存: {Path(path).name}", "success")

    def _clear_result(self) -> None:
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.config(state="disabled")
        self._last_segments = []
        self._set_status("就绪", "idle")

    def _set_status(self, msg: str, level: str = "idle") -> None:
        colors = {
            "idle":    (TEXT3,   TEXT2),
            "info":    (ACCENT,  TEXT),
            "success": (SUCCESS, TEXT),
            "error":   (DANGER,  TEXT),
            "warn":    ("#FF9F0A", TEXT),
        }
        dot_color, text_color = colors.get(level, (TEXT3, TEXT2))
        def _update():
            self._status_var.set(msg)
            self._status_dot.config(fg=dot_color)
            self._status_label.config(fg=text_color)
        self.after(0, _update)


if __name__ == "__main__":
    app = App()
    app.mainloop()
