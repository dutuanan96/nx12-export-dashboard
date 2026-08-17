"""
NX12 Export Dashboard - 俞俊安
A dark-themed Tkinter dashboard to run NX12 export tools with exact manifest reporting.
"""

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import subprocess
import threading
import os
import sys
import json
import time
import uuid

# ── High-DPI Awareness on Windows ───────────────────────────────────────────
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ── Color Palette ───────────────────────────────────────────────────────────
BG           = "#121420"
PANEL        = "#1b1e34"
PANEL_ACTIVE = "#222642"
BORDER       = "#2a2f4f"
TEXT         = "#f1f2f6"
SUBTEXT      = "#8a94a6"
MUTED        = "#747d8c"   # Clean, readable placeholder/secondary color
FOOTER_FG    = "#808e9b"   # Clear branding & version contrast

# Secondary utility button (Browse)
BTN_BROWSE   = "#252b48"
BTN_HOV_BROWSE = "#323a61"

# Primary action colors (Balanced saturation, distinct identities)
BTN_PDF      = "#d64545"   # Soft Crimson
BTN_HOV_PDF  = "#e05656"
BTN_STEP     = "#575fcf"   # Royal Indigo
BTN_HOV_STEP = "#6a72e5"
BTN_IGES     = "#0984e3"   # Cerulean
BTN_HOV_IGES = "#2495eb"
BTN_DWG      = "#05c46b"   # Mint Emerald
BTN_HOV_DWG  = "#1dd17e"

# Accent & Status
ACCENT       = "#3867d6"
ACCENT_HOV   = "#4b7bec"
SUCCESS      = "#2ed573"
WARNING      = "#ffa502"
ERROR        = "#ff4757"

PLACEHOLDER_TEXT = "请选择或粘贴包含 PRT / STP 的工作文件夹…"


# ── Helper Functions for Portable Paths ─────────────────────────────────────
def find_nx_environment():
    """
    Locate run_journal.exe and NX installation directory.
    Searches UGII_BASE_DIR, then common default installation locations.
    """
    candidates = []
    env_base = os.environ.get("UGII_BASE_DIR")
    if env_base and os.path.exists(env_base):
        candidates.append(env_base)

    candidates.extend([
        r"C:\Program Files\Siemens\NX 12.0",
        r"C:\Program Files\Siemens\NX2406",
        r"C:\Program Files\Siemens\NX 2406",
        r"C:\Program Files\Siemens\NX",
        r"D:\Program Files\Siemens\NX 12.0",
    ])

    for nx_base in candidates:
        if not os.path.exists(nx_base):
            continue
        run_journal = os.path.join(nx_base, "NXBIN", "run_journal.exe")
        if os.path.exists(run_journal):
            return run_journal, nx_base

    return None, None


def get_script_path(script_name: str) -> str:
    """
    Get the absolute path of a script, supporting development mode
    and PyInstaller standalone executable mode (_MEIPASS).
    """
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        cand = os.path.join(base_dir, "src", script_name)
        if os.path.exists(cand):
            return cand
        cand = os.path.join(base_dir, script_name)
        if os.path.exists(cand):
            return cand

    current_dir = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.join(current_dir, script_name)
    if os.path.exists(cand):
        return cand

    cand = os.path.join(current_dir, "src", script_name)
    if os.path.exists(cand):
        return cand

    parent_dir = os.path.dirname(current_dir)
    cand = os.path.join(parent_dir, "src", script_name)
    if os.path.exists(cand):
        return cand

    return os.path.join(current_dir, script_name)


# ── Main Application Class ──────────────────────────────────────────────────
class NX12Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NX12 批量导出工具")
        self.geometry("490x385")
        self.minsize(490, 385)
        self.maxsize(900, 385)
        self.resizable(True, False)
        self.configure(bg=BG)

        self.folder_var = tk.StringVar(value="")
        self.status_title_var = tk.StringVar(value="就绪")
        self.status_sub_var = tk.StringVar(value="请选择工作文件夹并点击上方功能按钮")
        self._running = False
        self._last_result = None
        self._has_placeholder = True
        self._current_proc = None
        self._cancel_requested = False

        self._build_ui()
        self._center_window()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # ─ Header ───────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=PANEL, bd=0)
        header.pack(fill="x", padx=14, pady=(12, 0))
        self._round_border(header)

        tk.Label(
            header,
            text="⚙  NX12 批量导出工具",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT, bg=PANEL,
        ).pack(side="left", padx=12, pady=7)

        tk.Label(
            header,
            text="俞俊安",
            font=("Segoe UI", 9, "bold"),
            fg="#a4b0be", bg=PANEL,
        ).pack(side="right", padx=12, pady=7)

        # ─ Body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=8)

        # Folder Selector Group
        lbl_folder = tk.Label(
            body,
            text="工作文件夹",
            font=("Segoe UI", 9, "bold"),
            fg=SUBTEXT, bg=BG,
            anchor="w",
        )
        lbl_folder.pack(fill="x", pady=(0, 3))

        f_row = tk.Frame(body, bg=BG)
        f_row.pack(fill="x", pady=(0, 10))

        self.entry_folder = tk.Entry(
            f_row,
            textvariable=self.folder_var,
            font=("Segoe UI", 9),
            bg=PANEL, fg=MUTED,
            insertbackground=TEXT,
            bd=0, relief="flat",
            takefocus=True,
        )
        self.entry_folder.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))
        self._round_border(self.entry_folder)
        self._init_placeholder()

        self.btn_browse = tk.Button(
            f_row,
            text="📂 浏览",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT, bg=BTN_BROWSE,
            activeforeground=TEXT, activebackground=BTN_HOV_BROWSE,
            bd=0, cursor="hand2",
            takefocus=True,
            command=self._browse,
        )
        self.btn_browse.pack(side="right", ipadx=10, ipady=3)
        self._round_border(self.btn_browse)
        self._hover(self.btn_browse, BTN_BROWSE, BTN_HOV_BROWSE)
        self._bind_button_keys(self.btn_browse, self._browse)

        # 2x2 Action Button Grid
        btn_grid = tk.Frame(body, bg=BG)
        btn_grid.pack(fill="x", pady=(0, 10))

        # Row 0: PDF | STEP
        self.btn_pdf = tk.Button(
            btn_grid,
            text="📄  导出 PRT → PDF",
            font=("Segoe UI", 10, "bold"),
            fg=TEXT, bg=BTN_PDF,
            activeforeground=TEXT, activebackground=BTN_HOV_PDF,
            bd=0, cursor="hand2",
            takefocus=True,
            command=lambda: self._run_tool("pdf"),
        )
        self.btn_pdf.grid(row=0, column=0, sticky="ew", padx=(0, 3), ipady=5)
        self._hover(self.btn_pdf, BTN_PDF, BTN_HOV_PDF)
        self._bind_button_keys(self.btn_pdf, lambda: self._run_tool("pdf"))

        self.btn_step = tk.Button(
            btn_grid,
            text="📦  导出 PRT → STEP",
            font=("Segoe UI", 10, "bold"),
            fg=TEXT, bg=BTN_STEP,
            activeforeground=TEXT, activebackground=BTN_HOV_STEP,
            bd=0, cursor="hand2",
            takefocus=True,
            command=lambda: self._run_tool("step"),
        )
        self.btn_step.grid(row=0, column=1, sticky="ew", padx=(3, 0), ipady=5)
        self._hover(self.btn_step, BTN_STEP, BTN_HOV_STEP)
        self._bind_button_keys(self.btn_step, lambda: self._run_tool("step"))

        # Row 1: IGES | DWG
        self.btn_iges = tk.Button(
            btn_grid,
            text="🔄  导入 STP → IGES",
            font=("Segoe UI", 10, "bold"),
            fg=TEXT, bg=BTN_IGES,
            activeforeground=TEXT, activebackground=BTN_HOV_IGES,
            bd=0, cursor="hand2",
            takefocus=True,
            command=lambda: self._run_tool("iges"),
        )
        self.btn_iges.grid(row=1, column=0, sticky="ew", padx=(0, 3), pady=(6, 0), ipady=5)
        self._hover(self.btn_iges, BTN_IGES, BTN_HOV_IGES)
        self._bind_button_keys(self.btn_iges, lambda: self._run_tool("iges"))

        self.btn_dwg = tk.Button(
            btn_grid,
            text="📐  导出 PRT → DWG",
            font=("Segoe UI", 10, "bold"),
            fg=TEXT, bg=BTN_DWG,
            activeforeground=TEXT, activebackground=BTN_HOV_DWG,
            bd=0, cursor="hand2",
            takefocus=True,
            command=lambda: self._run_tool("dwg"),
        )
        self.btn_dwg.grid(row=1, column=1, sticky="ew", padx=(3, 0), pady=(6, 0), ipady=5)
        self._hover(self.btn_dwg, BTN_DWG, BTN_HOV_DWG)
        self._bind_button_keys(self.btn_dwg, lambda: self._run_tool("dwg"))

        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)

        # ─ Status Card ──────────────────────────────────────────────────────
        self.status_card = tk.Frame(body, bg=PANEL, bd=0)
        self.status_card.pack(fill="x", pady=(0, 0))
        self._round_border(self.status_card)

        # Top row in status card: Indicator + Title + Detail button / Cancel button
        sc_top = tk.Frame(self.status_card, bg=PANEL)
        sc_top.pack(fill="x", padx=10, pady=(8, 2))

        self.indicator = tk.Label(
            sc_top, text="●",
            font=("Segoe UI", 11), fg=SUBTEXT, bg=PANEL,
        )
        self.indicator.pack(side="left", padx=(0, 6))

        self.status_title_lbl = tk.Label(
            sc_top,
            textvariable=self.status_title_var,
            font=("Segoe UI", 10, "bold"),
            fg=TEXT, bg=PANEL,
            anchor="w",
        )
        self.status_title_lbl.pack(side="left", fill="x", expand=True)

        self.btn_detail = tk.Button(
            sc_top,
            text="📋 查看详情",
            font=("Segoe UI", 8, "bold"),
            fg=TEXT, bg=ACCENT,
            activeforeground=TEXT, activebackground=ACCENT_HOV,
            bd=0, cursor="hand2",
            takefocus=True,
            command=self._show_details,
        )
        self._hover(self.btn_detail, ACCENT, ACCENT_HOV)
        self._bind_button_keys(self.btn_detail, self._show_details)

        self.btn_cancel = tk.Button(
            sc_top,
            text="⛔ 停止",
            font=("Segoe UI", 8, "bold"),
            fg=TEXT, bg=BTN_PDF,
            activeforeground=TEXT, activebackground=BTN_HOV_PDF,
            bd=0, cursor="hand2",
            takefocus=True,
            command=self._cancel_task,
        )
        self._hover(self.btn_cancel, BTN_PDF, BTN_HOV_PDF)
        self._bind_button_keys(self.btn_cancel, self._cancel_task)

        # Bottom row in status card: Subtitle / Metrics
        self.status_sub_lbl = tk.Label(
            self.status_card,
            textvariable=self.status_sub_var,
            font=("Segoe UI", 8),
            fg=SUBTEXT, bg=PANEL,
            anchor="w",
        )
        self.status_sub_lbl.pack(fill="x", padx=26, pady=(0, 8))

        # ─ Footer ───────────────────────────────────────────────────────────
        tk.Label(
            self,
            text="NX12 Export Dashboard v1.0.0  ·  Developed by 俞俊安",
            font=("Segoe UI", 8),
            fg=FOOTER_FG, bg=BG,
        ).pack(pady=(6, 8))

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _round_border(self, widget):
        widget.configure(highlightbackground=BORDER, highlightthickness=1)

    def _hover(self, widget, normal, hovered):
        widget.bind("<Enter>", lambda e: widget.configure(bg=hovered) if widget["state"] != "disabled" else None)
        widget.bind("<Leave>", lambda e: widget.configure(bg=normal) if widget["state"] != "disabled" else None)

    def _bind_button_keys(self, widget, command):
        widget.bind("<Return>", lambda e: command() if widget["state"] != "disabled" else None)
        widget.bind("<KP_Enter>", lambda e: command() if widget["state"] != "disabled" else None)
        widget.bind("<space>", lambda e: command() if widget["state"] != "disabled" else None)

    def _init_placeholder(self):
        self.folder_var.set(PLACEHOLDER_TEXT)
        self.entry_folder.configure(fg=MUTED)
        self.entry_folder.bind("<FocusIn>", self._on_focus_in)
        self.entry_folder.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_in(self, event):
        if self._has_placeholder:
            self.folder_var.set("")
            self.entry_folder.configure(fg=TEXT)
            self._has_placeholder = False

    def _on_focus_out(self, event):
        val = self.folder_var.get().strip()
        if not val:
            self.folder_var.set(PLACEHOLDER_TEXT)
            self.entry_folder.configure(fg=MUTED)
            self._has_placeholder = True

    def _get_clean_folder(self) -> str:
        if self._has_placeholder:
            return ""
        return self.folder_var.get().strip()

    def _set_status(self, title: str, subtext: str, color=SUBTEXT, show_detail=False):
        self.status_title_var.set(title)
        self.status_sub_var.set(subtext)
        self.status_title_lbl.configure(fg=color if color != SUBTEXT else TEXT)
        self.indicator.configure(fg=color)

        if self._running:
            self.btn_detail.pack_forget()
            self.btn_cancel.pack(side="right", padx=(0, 2))
        else:
            self.btn_cancel.pack_forget()
            if show_detail and self._last_result:
                self.btn_detail.pack(side="right", padx=(0, 2))
            else:
                self.btn_detail.pack_forget()

    def _cancel_task(self):
        """Immediately terminate active export process tree."""
        if not self._running:
            return
        self._cancel_requested = True
        if self._current_proc and self._current_proc.poll() is None:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self._current_proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
            except Exception:
                pass
        self._set_status("⏹  已手动终止任务", "用户中止了当前批量导出操作", WARNING, show_detail=False)

    def _on_close(self):
        """Handle window close event and terminate child processes cleanly."""
        if self._running and self._current_proc and self._current_proc.poll() is None:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self._current_proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
            except Exception:
                pass
        self.destroy()

    # ── Actions ──────────────────────────────────────────────────────────────
    def _browse(self):
        folder = filedialog.askdirectory(title="选择工作文件夹")
        if folder:
            norm = os.path.normpath(folder)
            self._has_placeholder = False
            self.folder_var.set(norm)
            self.entry_folder.configure(fg=TEXT)
            self._set_status("已选择文件夹", f"路径: {norm}", SUBTEXT, show_detail=False)
            self._last_result = None

    def _run_tool(self, tool_key: str):
        if self._running:
            return

        folder = self._get_clean_folder()
        if not folder or not os.path.exists(folder):
            self._set_status("⚠ 请先选择有效文件夹！", "请点击 [📂 浏览] 按钮指定包含 PRT / STP 的目录", ERROR)
            return

        run_journal, nx_base = find_nx_environment()
        if not run_journal:
            self._set_status("❌ 未找到 NX 运行环境", "无法定位 run_journal.exe，请确认已安装 Siemens NX 12.0", ERROR)
            return

        tool_configs = {
            "pdf":  ("export_pdf_NX12.py", "PDF", "PRT → PDF"),
            "step": ("export_step_NX12.py", "STEP", "PRT → STEP (AP214)"),
            "iges": ("import_stp_export_iges_NX12.py", "IGES", "STP → IGES"),
            "dwg":  ("export_dwg_NX12.py", "DWG", "PRT → DWG"),
        }

        if tool_key not in tool_configs:
            return

        script_file, subfolder, label = tool_configs[tool_key]
        script_path = get_script_path(script_file)

        if not os.path.exists(script_path):
            self._set_status("❌ 脚本文件缺失", f"找不到: {script_file}", ERROR)
            return

        self._running = True
        self._cancel_requested = False
        self._current_proc = None
        self._last_result = None
        self._lock_buttons(True)
        self._set_status(f"⏳  正在导出 {label}…", "NX 正在后台处理模型，点击 [⛔ 停止] 可随时终止", WARNING, show_detail=False)

        thread = threading.Thread(
            target=self._execute_batch,
            args=(run_journal, nx_base, script_path, folder, subfolder, label),
            daemon=True
        )
        thread.start()

    def _execute_batch(self, run_journal, nx_base, script_path, folder, subfolder, label):
        """Execute journal subprocess with run_id and read atomic manifest export_result.json."""
        out_folder = os.path.join(folder, subfolder)
        result_json_path = os.path.join(out_folder, "export_result.json")
        current_run_id = uuid.uuid4().hex[:12]

        # Invalidate old result manifest strictly
        if os.path.exists(result_json_path):
            try:
                os.remove(result_json_path)
            except Exception as e_del:
                self.after(0, self._set_status, "❌ 无法清理旧结果", f"Manifest 被占用: {e_del}", ERROR)
                self._running = False
                self.after(0, self._lock_buttons, False)
                return

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            env = os.environ.copy()
            if nx_base:
                env["UGII_BASE_DIR"] = nx_base
                env["UGII_ROOT_DIR"] = os.path.join(nx_base, "UGII")
                nxbin = os.path.join(nx_base, "NXBIN")
                ugii = os.path.join(nx_base, "UGII")
                env["PATH"] = f"{nxbin};{ugii};" + env.get("PATH", "")

            # ── Process Isolation for STP -> IGES ────────────────────────────
            if subfolder == "IGES":
                stp_files = [f for f in os.listdir(folder) if f.lower().endswith((".stp", ".step"))]
                total_files = len(stp_files)

                if total_files == 0:
                    empty_res = {"operation": "stp_to_iges", "run_id": current_run_id, "total": 0, "success": 0, "failed": 0, "skipped": 0, "files": []}
                    self.after(0, self._handle_manifest_result, empty_res, label)
                    return

                aggregated = {
                    "operation": "stp_to_iges",
                    "run_id": current_run_id,
                    "total": total_files,
                    "success": 0,
                    "failed": 0,
                    "skipped": 0,
                    "files": []
                }

                for idx, stp_name in enumerate(stp_files):
                    if self._cancel_requested:
                        break

                    self.after(0, self._set_status, f"⏳ [{idx+1}/{total_files}] 正在导出 IGES…", f"当前文件: {stp_name}", WARNING, False)

                    cmd = [run_journal, script_path, "-args", folder, current_run_id, stp_name]
                    self._current_proc = subprocess.Popen(cmd, startupinfo=startupinfo, env=env)

                    try:
                        self._current_proc.wait(timeout=180)
                    except subprocess.TimeoutExpired:
                        self._cancel_task()
                        break

                    if self._cancel_requested:
                        break

                    # After NX process completely exits, safely delete known translator temp files
                    for f in os.listdir(folder):
                        fpath = os.path.join(folder, f)
                        if os.path.isfile(fpath):
                            ext = os.path.splitext(f)[1].lower()
                            if f.endswith("_stp.prt") or ext == ".log" or (ext == ".prt" and f not in stp_files):
                                try:
                                    os.remove(fpath)
                                except Exception:
                                    pass

                    # Record per-file result
                    base_name = os.path.splitext(stp_name)[0]
                    iges_out_path = os.path.join(out_folder, base_name + ".igs")
                    rel_output = os.path.join("IGES", base_name + ".igs").replace("\\", "/")

                    if os.path.exists(iges_out_path) and os.path.getsize(iges_out_path) >= 500:
                        aggregated["success"] += 1
                        aggregated["files"].append({
                            "input": stp_name,
                            "output": rel_output,
                            "status": "success",
                            "error": None
                        })
                    else:
                        aggregated["failed"] += 1
                        aggregated["files"].append({
                            "input": stp_name,
                            "output": None,
                            "status": "failed",
                            "error": "IGES output file not generated or invalid (< 500 bytes)"
                        })

                # Write final aggregated manifest
                if not self._cancel_requested:
                    try:
                        tmp_json = result_json_path + ".tmp"
                        with open(tmp_json, "w", encoding="utf-8") as f:
                            json.dump(aggregated, f, indent=2)
                        if os.path.exists(result_json_path):
                            try: os.remove(result_json_path)
                            except: pass
                        os.rename(tmp_json, result_json_path)
                    except Exception:
                        pass

                    self._last_result = aggregated
                    self.after(0, self._handle_manifest_result, aggregated, label)
                return

            # ── Single-Process Batch for PDF, STEP, DWG ─────────────────────
            cmd = [run_journal, script_path, "-args", folder, current_run_id]

            self._current_proc = subprocess.Popen(
                cmd,
                startupinfo=startupinfo,
                env=env,
            )

            try:
                returncode = self._current_proc.wait(timeout=600)
            except subprocess.TimeoutExpired:
                self._cancel_task()
                self.after(0, self._set_status, "❌ 执行超时", "任务运行超过 10 分钟已自动终止", ERROR)
                return

            if self._cancel_requested:
                return

            # Poll, read and verify export_result.json matching current_run_id
            manifest_data = None
            for _ in range(20):
                if os.path.exists(result_json_path):
                    try:
                        with open(result_json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if data.get("run_id") == current_run_id:
                            manifest_data = data
                            break
                    except Exception:
                        pass
                time.sleep(0.5)

            if manifest_data:
                self._last_result = manifest_data
                self.after(0, self._handle_manifest_result, manifest_data, label)
                return
            else:
                if returncode == 0:
                    self.after(0, self._set_status, f"⚠ {label} 结束，未生成结果", "未能生成与当前 Run ID 匹配的 manifest", WARNING)
                else:
                    self.after(0, self._set_status, f"❌ {label} 异常退出", f"NX 返回代码: {returncode}", ERROR)

        except Exception as exc:
            if not self._cancel_requested:
                self.after(0, self._set_status, "❌ 发生异常", str(exc), ERROR)
        finally:
            self._running = False
            self.after(0, self._lock_buttons, False)

    def _handle_manifest_result(self, result_data, label):
        """Update status card based on exact manifest metrics."""
        total = result_data.get("total", 0)
        success = result_data.get("success", 0)
        failed = result_data.get("failed", 0)
        skipped = result_data.get("skipped", 0)

        if total == 0:
            self._set_status(f"⚠  {label} 未找到文件", "目录中没有符合条件的输入文件", SUBTEXT, show_detail=False)
        elif failed == 0 and skipped == 0:
            self._set_status(
                "✅  导出全部成功",
                f"最近结果: {success} 成功 · 共 {total} 个文件",
                SUCCESS,
                show_detail=True
            )
        elif success > 0 or skipped > 0:
            sub = f"最近结果: {success} 成功"
            if failed > 0:
                sub += f" · {failed} 失败"
            if skipped > 0:
                sub += f" · {skipped} 跳过"
            sub += f" · 共 {total} 个文件"
            self._set_status(
                "⚠  部分完成",
                sub,
                WARNING,
                show_detail=True
            )
        else:
            self._set_status(
                "❌  导出失败",
                f"最近结果: 0 成功 · {failed} 失败 · 共 {total} 个文件",
                ERROR,
                show_detail=True
            )

    def _show_details(self):
        """Display detailed modal window of last batch results."""
        if not self._last_result:
            return

        dlg = tk.Toplevel(self)
        dlg.title("批处理执行详情")
        dlg.geometry("680x380")
        dlg.minsize(580, 280)
        dlg.resizable(True, True)
        dlg.configure(bg=BG)
        dlg.transient(self)
        dlg.grab_set()

        # Center dialog
        dlg.update_idletasks()
        w, h = 680, 380
        x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        dlg.bind("<Escape>", lambda e: dlg.destroy())

        # Summary Header
        total = self._last_result.get("total", 0)
        success = self._last_result.get("success", 0)
        failed = self._last_result.get("failed", 0)
        skipped = self._last_result.get("skipped", 0)
        op = self._last_result.get("operation", "")
        run_id = self._last_result.get("run_id", "N/A")

        hdr_frame = tk.Frame(dlg, bg=PANEL, padx=12, pady=10)
        hdr_frame.pack(fill="x", padx=12, pady=12)

        tk.Label(
            hdr_frame,
            text=f"操作: {op}  (Run ID: {run_id})",
            font=("Segoe UI", 10, "bold"),
            fg=TEXT, bg=PANEL,
        ).pack(anchor="w")

        tk.Label(
            hdr_frame,
            text=f"总计: {total}  |  成功: {success}  |  失败: {failed}  |  跳过: {skipped}",
            font=("Segoe UI", 9),
            fg=SUCCESS if failed == 0 and skipped == 0 else WARNING,
            bg=PANEL,
        ).pack(anchor="w", pady=(4, 0))

        # Treeview Table
        tree_frame = tk.Frame(dlg, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        columns = ("file", "status", "output", "error")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)

        tree.heading("file", text="输入文件")
        tree.heading("status", text="状态")
        tree.heading("output", text="输出文件")
        tree.heading("error", text="错误说明")

        tree.column("file", width=140, anchor="w")
        tree.column("status", width=70, anchor="center")
        tree.column("output", width=180, anchor="w")
        tree.column("error", width=200, anchor="w")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=PANEL,
            foreground=TEXT,
            fieldbackground=PANEL,
            rowheight=22,
            font=("Segoe UI", 9),
        )
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        for item in self._last_result.get("files", []):
            st = item.get("status", "")
            out = item.get("output", "")
            if isinstance(out, list):
                out = ", ".join(out)
            err = item.get("error", "") or ""
            tree.insert("", "end", values=(item.get("input", ""), st, out, err))

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _lock_buttons(self, locked: bool):
        st = "disabled" if locked else "normal"
        self.btn_browse.configure(state=st)
        self.btn_pdf.configure(state=st)
        self.btn_step.configure(state=st)
        self.btn_iges.configure(state=st)
        self.btn_dwg.configure(state=st)


if __name__ == "__main__":
    app = NX12Dashboard()
    app.mainloop()
