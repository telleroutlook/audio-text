#!/usr/bin/env python3
"""
audio-text GUI: 本地语音转文字图形界面
基于 MLX Whisper (Apple Silicon 加速)
"""

import tkinter as tk
from tkinter import ttk, filedialog
import threading
import time
from pathlib import Path

from transcribe import (
    DEFAULT_MODEL, do_transcribe, filter_segments,
    format_segments, format_srt, format_vtt,
)
from domain_prompts import build_prompt

# ── 颜色系统 ──────────────────────────────────────────────────
BG       = "#1C1C1E"
PANEL    = "#2C2C2E"
PANEL2   = "#3A3A3C"
BORDER   = "#48484A"
ACCENT   = "#0A84FF"
ACCENT_H = "#409CFF"
SUCCESS  = "#30D158"
DANGER   = "#FF453A"
TEXT     = "#F2F2F7"
TEXT2    = "#8E8E93"
TEXT3    = "#636366"

MODELS = [
    ("large-v3-turbo  ·  推荐，中文最佳", "mlx-community/whisper-large-v3-turbo"),
    ("large-v3  ·  最高精度，较慢",        "mlx-community/whisper-large-v3"),
    ("medium  ·  速度与精度均衡",           "mlx-community/whisper-medium"),
    ("small  ·  速度快，精度稍低",          "mlx-community/whisper-small"),
]

LANGUAGES = [
    ("中文",    "zh"),
    ("自动检测", None),
    ("英文",    "en"),
    ("日文",    "ja"),
    ("粤语",    "yue"),
]


# ── 自定义控件 ────────────────────────────────────────────────

class FlatButton(tk.Label):
    """扁平风格按钮"""
    def __init__(self, parent, text, command,
                 bg=ACCENT, fg=TEXT, hover_bg=ACCENT_H,
                 padx=16, pady=7, font_size=11, **kw):
        super().__init__(parent, text=text, bg=bg, fg=fg,
                         font=("PingFang SC", font_size),
                         padx=padx, pady=pady, cursor="hand2", **kw)
        self._bg = bg
        self._hover_bg = hover_bg
        self._command = command
        self.bind("<Enter>",    lambda e: self.config(bg=hover_bg))
        self.bind("<Leave>",    lambda e: self.config(bg=self._bg))
        self.bind("<Button-1>", lambda e: command())

    def set_bg(self, bg, hover_bg):
        self._bg = bg
        self._hover_bg = hover_bg
        self.config(bg=bg)


class ToggleSwitch(tk.Canvas):
    """iOS 风格开关"""
    def __init__(self, parent, variable: tk.BooleanVar, **kw):
        super().__init__(parent, width=44, height=24, bg=PANEL,
                         highlightthickness=0, cursor="hand2", **kw)
        self._var = variable
        self._draw()
        self.bind("<Button-1>", self._toggle)
        variable.trace_add("write", lambda *_: self._draw())

    def _rr(self, x1, y1, x2, y2, r, **kw):
        self.create_arc(x1,      y1,      x1+2*r, y1+2*r, start=90,  extent=90,  **kw)
        self.create_arc(x2-2*r,  y1,      x2,     y1+2*r, start=0,   extent=90,  **kw)
        self.create_arc(x1,      y2-2*r,  x1+2*r, y2,     start=180, extent=90,  **kw)
        self.create_arc(x2-2*r,  y2-2*r,  x2,     y2,     start=270, extent=90,  **kw)
        self.create_rectangle(x1+r, y1, x2-r, y2, **kw)
        self.create_rectangle(x1, y1+r, x2, y2-r, **kw)

    def _draw(self):
        self.delete("all")
        on = self._var.get()
        self._rr(2, 4, 42, 20, 8, fill=ACCENT if on else BORDER, outline="")
        kx = 28 if on else 6
        self.create_oval(kx, 3, kx+18, 21, fill=TEXT, outline="")

    def _toggle(self, _=None):
        self._var.set(not self._var.get())


def _apply_style(root: tk.Tk) -> None:
    """把 ttk.Combobox 和 Scrollbar 染成深色"""
    style = ttk.Style(root)
    style.theme_use("default")

    style.configure("Dark.TCombobox",
                    fieldbackground=PANEL2,
                    background=PANEL2,
                    foreground=TEXT,
                    selectbackground=PANEL2,
                    selectforeground=TEXT,
                    arrowcolor=TEXT2,
                    bordercolor=BORDER,
                    lightcolor=PANEL2,
                    darkcolor=PANEL2,
                    insertcolor=TEXT,
                    padding=(8, 5))
    style.map("Dark.TCombobox",
              fieldbackground=[("readonly", PANEL2)],
              foreground=[("readonly", TEXT)],
              selectbackground=[("readonly", PANEL2)])

    root.option_add("*TCombobox*Listbox.background",  PANEL2)
    root.option_add("*TCombobox*Listbox.foreground",  TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    root.option_add("*TCombobox*Listbox.font", ("PingFang SC", 11))


# ── 主应用 ────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("语音转文字")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(780, 600)
        _apply_style(self)

        self._transcribing   = False
        self._transcribe_start: float = 0.0
        self._last_segments: list[dict] = []
        self._progress_active = False
        self._progress_pos    = 0.0

        self._build_ui()
        self._center_window()

    def _center_window(self) -> None:
        self.update_idletasks()
        w, h = 860, 660
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── 小工具 ────────────────────────────────────────────────

    def _lbl(self, parent, text, size=13, color=TEXT, bold=False, **kw) -> tk.Label:
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("PingFang SC", size, "bold" if bold else "normal"), **kw)

    def _combo(self, parent, var: tk.StringVar, values: list[str], width=26) -> ttk.Combobox:
        cb = ttk.Combobox(parent, textvariable=var, values=values,
                          state="readonly", width=width, style="Dark.TCombobox")
        cb.current(0)
        return cb

    def _sep(self, parent) -> tk.Frame:
        return tk.Frame(parent, bg=BORDER, height=1)

    def _build_ui(self) -> None:
        # ── 顶部标题栏 ─────────────────────────────────
        header = tk.Frame(self, bg=PANEL, height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        self._lbl(header, "语音转文字", size=14, bold=True).pack(side="left", padx=20)
        self._lbl(header, "MLX Whisper · Apple Silicon",
                  size=11, color=TEXT3).pack(side="left", pady=(5, 0))

        # ── 主体 ───────────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        left = tk.Frame(body, bg=BG, width=290)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_right(right)

        # ── 状态栏 ─────────────────────────────────────
        bar = tk.Frame(self, bg=PANEL, height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self._status_dot = tk.Label(bar, text="●", bg=PANEL, fg=TEXT3,
                                    font=("PingFang SC", 9))
        self._status_dot.pack(side="left", padx=(12, 4))
        self._status_var = tk.StringVar(value="就绪")
        self._status_lbl = tk.Label(bar, textvariable=self._status_var,
                                    bg=PANEL, fg=TEXT2, font=("PingFang SC", 11))
        self._status_lbl.pack(side="left")

    def _build_left(self, parent) -> None:
        # 卡片 1：模型 / 语言 / 时间戳 / 词汇
        c1 = tk.Frame(parent, bg=PANEL)
        c1.pack(fill="x", pady=(0, 8))
        p = tk.Frame(c1, bg=PANEL)
        p.pack(fill="x", padx=14, pady=12)

        # 模型
        self._lbl(p, "模型", size=11, color=TEXT3).pack(anchor="w")
        self._model_labels = [m[0] for m in MODELS]
        self._model_ids    = [m[1] for m in MODELS]
        self._model_var    = tk.StringVar()
        self._combo(p, self._model_var, self._model_labels, width=28).pack(
            fill="x", pady=(4, 0))

        self._sep(c1).pack(fill="x", pady=(8, 0))

        p2 = tk.Frame(c1, bg=PANEL)
        p2.pack(fill="x", padx=14, pady=10)

        # 语言
        row = tk.Frame(p2, bg=PANEL)
        row.pack(fill="x")
        self._lbl(row, "语言", size=11, color=TEXT3).pack(side="left")
        self._lang_labels = [l[0] for l in LANGUAGES]
        self._lang_codes  = [l[1] for l in LANGUAGES]
        self._lang_var    = tk.StringVar()
        self._combo(row, self._lang_var, self._lang_labels, width=10).pack(side="right")

        # 时间戳
        row2 = tk.Frame(p2, bg=PANEL)
        row2.pack(fill="x", pady=(10, 0))
        self._lbl(row2, "显示时间戳", size=11, color=TEXT3).pack(side="left")
        self._timestamps_var = tk.BooleanVar(value=True)
        ToggleSwitch(row2, self._timestamps_var).pack(side="right")

        self._sep(c1).pack(fill="x", pady=(8, 0))

        p3 = tk.Frame(c1, bg=PANEL)
        p3.pack(fill="x", padx=14, pady=10)

        # 内置词汇
        row3 = tk.Frame(p3, bg=PANEL)
        row3.pack(fill="x")
        self._lbl(row3, "内置词汇", size=11, color=TEXT3).pack(side="left")
        self._builtin_var = tk.StringVar()
        self._combo(row3, self._builtin_var, ["数字化", "无"], width=8).pack(side="right")

        # 自定义词汇
        self._lbl(p3, "自定义词汇（逗号分隔）", size=11, color=TEXT3).pack(
            anchor="w", pady=(10, 4))
        self._prompt_var = tk.StringVar(value="")
        tk.Entry(p3, textvariable=self._prompt_var,
                 bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat",
                 font=("PingFang SC", 11),
                 highlightbackground=BORDER, highlightthickness=1).pack(
            fill="x", ipady=5)

        # 卡片 2：文件转录
        c2 = tk.Frame(parent, bg=PANEL)
        c2.pack(fill="x", pady=(0, 8))
        p4 = tk.Frame(c2, bg=PANEL)
        p4.pack(fill="x", padx=14, pady=12)

        self._lbl(p4, "转录音频文件", size=11, color=TEXT3).pack(anchor="w")

        file_row = tk.Frame(p4, bg=PANEL)
        file_row.pack(fill="x", pady=(6, 8))
        self._file_var = tk.StringVar(value="")
        tk.Entry(file_row, textvariable=self._file_var,
                 bg=PANEL2, fg=TEXT2, insertbackground=TEXT, relief="flat",
                 font=("PingFang SC", 11),
                 highlightbackground=BORDER, highlightthickness=1).pack(
            side="left", fill="x", expand=True, ipady=4)
        FlatButton(file_row, "浏览", self._pick_file,
                   bg=PANEL2, fg=TEXT, hover_bg=BORDER,
                   padx=10, pady=4, font_size=11).pack(side="left", padx=(6, 0))

        FlatButton(p4, "开始转文字  →", self._start_file_transcribe,
                   padx=0, pady=8, font_size=11).pack(fill="x")

        # Voice Memos 提示卡片
        c3 = tk.Frame(parent, bg=PANEL)
        c3.pack(fill="x", pady=(0, 8))
        p5 = tk.Frame(c3, bg=PANEL)
        p5.pack(fill="x", padx=14, pady=12)

        self._lbl(p5, "如何转录 Voice Memos 录音", size=11, color=TEXT3).pack(anchor="w", pady=(0, 6))
        self._lbl(p5,
                  "① 打开「备忘录」App\n"
                  "② 长按录音 → 共享\n"
                  "③ 存储到「下载」文件夹\n"
                  "④ 点「浏览」选择文件后转录",
                  size=11, color=TEXT2).pack(anchor="w")

        # 进度条
        self._prog_canvas = tk.Canvas(parent, height=3, bg=BG, highlightthickness=0)
        self._prog_canvas.pack(fill="x", pady=(0, 2))

    def _build_right(self, parent) -> None:
        # 标题 + 操作按钮
        top = tk.Frame(parent, bg=BG)
        top.pack(fill="x", pady=(0, 8))
        self._lbl(top, "转录结果", size=14, bold=True).pack(side="left")

        btns = tk.Frame(top, bg=BG)
        btns.pack(side="right")
        FlatButton(btns, "清空", self._clear_result,
                   bg=PANEL2, fg=TEXT2, hover_bg=BORDER,
                   padx=12, pady=5, font_size=11).pack(side="left", padx=(0, 6))
        FlatButton(btns, "另存为", self._save_result,
                   bg=PANEL2, fg=TEXT, hover_bg=BORDER,
                   padx=12, pady=5, font_size=11).pack(side="left", padx=(0, 6))
        FlatButton(btns, "↓ 下载", self._quick_save,
                   bg=PANEL2, fg=TEXT, hover_bg=BORDER,
                   padx=12, pady=5, font_size=11).pack(side="left", padx=(0, 6))
        FlatButton(btns, "复制", self._copy_result,
                   bg=ACCENT, fg=TEXT, hover_bg=ACCENT_H,
                   padx=12, pady=5, font_size=11).pack(side="left")

        # 文本区
        frame = tk.Frame(parent, bg=PANEL,
                         highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=True)

        self._result_text = tk.Text(
            frame, wrap="word",
            font=("PingFang SC", 11),
            bg=PANEL, fg=TEXT,
            insertbackground=TEXT,
            selectbackground=ACCENT,
            selectforeground=TEXT,
            relief="flat", padx=16, pady=14,
            state="disabled",
            spacing1=3, spacing3=3,
        )
        sb = tk.Scrollbar(frame, orient="vertical",
                          command=self._result_text.yview,
                          bg=PANEL, troughcolor=PANEL, activebackground=BORDER)
        self._result_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._result_text.pack(side="left", fill="both", expand=True)

    # ── 进度动画 ──────────────────────────────────────────────

    def _start_progress(self) -> None:
        self._progress_active = True
        self._progress_pos = 0.0
        self._animate_progress()

    def _stop_progress(self) -> None:
        self._progress_active = False
        self._prog_canvas.delete("all")

    def _animate_progress(self) -> None:
        if not self._progress_active:
            return
        c = self._prog_canvas
        w = c.winfo_width() or 300
        c.delete("all")
        c.create_rectangle(0, 0, w, 3, fill=PANEL2, outline="")
        bw = int(w * 0.3)
        x = int((self._progress_pos % 1.0) * (w + bw)) - bw
        c.create_rectangle(x, 0, x + bw, 3, fill=ACCENT, outline="")
        self._progress_pos += 0.012
        self.after(16, self._animate_progress)

    # ── 事件处理 ──────────────────────────────────────────────

    def _get_model(self) -> str:
        label = self._model_var.get()
        try:
            return self._model_ids[self._model_labels.index(label)]
        except ValueError:
            return DEFAULT_MODEL

    def _get_lang(self) -> str | None:
        label = self._lang_var.get()
        try:
            return self._lang_codes[self._lang_labels.index(label)]
        except ValueError:
            return None

    def _get_prompt(self) -> tuple[str | None, bool]:
        use_builtin = self._builtin_var.get() == "数字化"
        custom = self._prompt_var.get().strip()
        return (custom or None, use_builtin)

    def _pick_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择音频/视频文件",
            initialdir=str(Path.home() / "Downloads"),
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
            model  = self._get_model()
            lang   = self._get_lang()
            prompt, use_builtin = self._get_prompt()
            self._transcribe_start = time.time()
            self._transcribing = True

            result = do_transcribe(audio_path, model, lang, prompt, use_builtin)

            self._transcribing = False
            elapsed  = time.time() - self._transcribe_start
            segments = filter_segments(result.get("segments", []))
            self._last_segments = segments
            text     = format_segments(segments, show_timestamps=self._timestamps_var.get())
            detected = result.get("language", "未知")
            self.after(0, lambda: self._show_result(text, elapsed, detected, len(segments)))
        except Exception as e:
            self._transcribing = False
            err = str(e)
            self.after(0, lambda: self._set_status(f"错误: {err}", "error"))
        finally:
            self._transcribing = False
            self.after(0, self._stop_progress)

    def _show_result(self, text, elapsed, detected, seg_count) -> None:
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

    def _quick_save(self) -> None:
        text = self._result_text.get("1.0", "end").strip()
        if not text:
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = Path.home() / "Downloads" / f"transcript_{ts}.txt"
        path.write_text(text, encoding="utf-8")
        self._set_status(f"已保存到下载: transcript_{ts}.txt", "success")

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
        if not path:
            return
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
            "idle":    (TEXT3,    TEXT2),
            "info":    (ACCENT,   TEXT),
            "success": (SUCCESS,  TEXT),
            "error":   (DANGER,   TEXT),
            "warn":    ("#FF9F0A", TEXT),
        }
        dot, txt = colors.get(level, (TEXT3, TEXT2))
        def _update():
            self._status_var.set(msg)
            self._status_dot.config(fg=dot)
            self._status_lbl.config(fg=txt)
        self.after(0, _update)


if __name__ == "__main__":
    app = App()
    app.mainloop()
