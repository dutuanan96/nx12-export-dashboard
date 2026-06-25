"""
NX12 Export Dashboard - 俞俊安
A dark-themed Tkinter dashboard to run NX12 export tools.
"""

import tkinter as tk
from tkinter import filedialog, ttk
import subprocess
import threading
import os
import time

# ── 调色板 ──────────────────────────────────────────────────────────────────
BG        = "#1a1a2e"
PANEL     = "#16213e"
ACCENT1   = "#0f3460"
BTN_PDF   = "#e94560"
BTN_IGES  = "#0f7cbb"
BTN_HOV1  = "#c73652"
BTN_HOV2  = "#0a6399"
TEXT      = "#eaeaea"
SUBTEXT   = "#8892a4"
SUCCESS   = "#4caf88"
ERROR     = "#e05252"
BORDER    = "#2a2a4a"

# ── NX12 命令路径 ──────────────────────────────────────────────────────────
RUN_JOURNAL = r"C:\Program Files\Siemens\NX 12.0\NXBIN\run_journal.exe"
SCRIPT_PDF   = r"D:\tool\export_pdf_NX12.py"
SCRIPT_IGES  = r"D:\tool\import_stp_export_iges_NX12.py"
SCRIPT_STEP  = r"D:\tool\export_step_NX12.py"
SCRIPT_CLEAN = r"D:\tool\cleanup_step_logs.cs"
SCRIPT_DWG   = r"D:\tool\export_dwg_NX12.py"


class NX12Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("NX12 导出工具 - 俞俊安")
        self.resizable(False, False)
        self.configure(bg=BG)

        w, h = 520, 470
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self.folder_var  = tk.StringVar(value="")
        self.status_var  = tk.StringVar(value="")
        self._running    = False

        self._build_ui()

    # ── 界面布局 ───────────────────────────────────────────────────────────
    def _build_ui(self):
        # ─ 顶部标题栏 ─────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=ACCENT1, height=58)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(
            hdr,
            text="⚙  NX12 导出工具",
            font=("Segoe UI", 15, "bold"),
            fg=TEXT, bg=ACCENT1,
        ).pack(side="left", padx=20, pady=12)

        tk.Label(
            hdr,
            text="俞俊安",
            font=("Segoe UI", 10),
            fg="#8892a4", bg=ACCENT1,
        ).pack(side="right", padx=20, pady=12)

        # ─ 主体内容 ───────────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=22, pady=18)

        # 选择来源文件夹
        tk.Label(
            body,
            text="选择来源文件夹",
            font=("Segoe UI", 9),
            fg=SUBTEXT, bg=BG,
        ).pack(anchor="w")

        # 文件夹选择行
        pick_row = tk.Frame(body, bg=BG)
        pick_row.pack(fill="x", pady=(4, 14))

        self.path_lbl = tk.Label(
            pick_row,
            textvariable=self.folder_var,
            font=("Consolas", 9),
            fg=TEXT, bg=PANEL,
            anchor="w",
            padx=10,
            relief="flat",
            bd=0,
            width=46,
        )
        self.path_lbl.pack(side="left", ipady=8, fill="x", expand=True)
        self._round_border(pick_row, self.path_lbl)

        browse_btn = tk.Button(
            pick_row,
            text="  📂  浏览",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT, bg=ACCENT1,
            activeforeground=TEXT, activebackground="#1a4a80",
            bd=0, cursor="hand2",
            command=self._browse,
        )
        browse_btn.pack(side="right", padx=(8, 0), ipady=8, ipadx=6)
        self._hover(browse_btn, ACCENT1, "#1a4a80")

        # ─ 操作按钮 2x2 ────────────────────────────────────────────────────
        btn_grid = tk.Frame(body, bg=BG)
        btn_grid.pack(fill="x", pady=(0, 6))

        # Row 1: PDF | STEP
        self.btn_pdf = tk.Button(
            btn_grid,
            text="📄  导出 PRT → PDF",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT, bg=BTN_PDF,
            activeforeground=TEXT, activebackground=BTN_HOV1,
            bd=0, cursor="hand2",
            command=lambda: self._run_tool("pdf"),
        )
        self.btn_pdf.grid(row=0, column=0, sticky="ew", padx=(0, 4), ipady=3)
        self._hover(self.btn_pdf, BTN_PDF, BTN_HOV1)

        self.btn_step = tk.Button(
            btn_grid,
            text="📦  导出 PRT → STEP",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT, bg="#7b68ee",
            activeforeground=TEXT, activebackground="#6a5acd",
            bd=0, cursor="hand2",
            command=lambda: self._run_tool("step"),
        )
        self.btn_step.grid(row=0, column=1, sticky="ew", padx=(4, 0), ipady=3)
        self._hover(self.btn_step, "#7b68ee", "#6a5acd")

        # Row 2: IGES | DWG
        self.btn_iges = tk.Button(
            btn_grid,
            text="🔄  导入 STP → IGES",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT, bg=BTN_IGES,
            activeforeground=TEXT, activebackground=BTN_HOV2,
            bd=0, cursor="hand2",
            command=lambda: self._run_tool("iges"),
        )
        self.btn_iges.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(8, 0), ipady=3)
        self._hover(self.btn_iges, BTN_IGES, BTN_HOV2)

        self.btn_dwg = tk.Button(
            btn_grid,
            text="📐  导出 PRT → DWG",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT, bg="#2ecc71",
            activeforeground=TEXT, activebackground="#27ae60",
            bd=0, cursor="hand2",
            command=lambda: self._run_tool("dwg"),
        )
        self.btn_dwg.grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=(8, 0), ipady=3)
        self._hover(self.btn_dwg, "#2ecc71", "#27ae60")

        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)

        # ─ 底部状态栏 ───────────────────────────────────────────────────────
        status_frame = tk.Frame(body, bg=PANEL, bd=0)
        status_frame.pack(fill="x", pady=(16, 0))

        self.indicator = tk.Label(
            status_frame, text="●",
            font=("Segoe UI", 10), fg=SUBTEXT, bg=PANEL,
        )
        self.indicator.pack(side="left", padx=(10, 4), pady=10)

        self.status_lbl = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            fg=SUBTEXT, bg=PANEL,
            anchor="w",
        )
        self.status_lbl.pack(side="left", fill="x", expand=True, pady=10)

        self._set_status("就绪", SUBTEXT)

        # ─ 底部信息 ───────────────────────────────────────────────────────
        tk.Label(
            self,
            text="Developed by 俞俊安",
            font=("Segoe UI", 9, "bold"),
            fg="#8892a4", bg=BG,
        ).pack(pady=(0, 6))

    # ── 辅助方法 ─────────────────────────────────────────────────────────────
    def _round_border(self, parent, widget):
        widget.configure(highlightbackground=BORDER, highlightthickness=1)

    def _hover(self, widget, normal, hovered):
        widget.bind("<Enter>", lambda e: widget.configure(bg=hovered))
        widget.bind("<Leave>", lambda e: widget.configure(bg=normal))

    def _set_status(self, msg, color=SUBTEXT):
        self.status_var.set(msg)
        self.status_lbl.configure(fg=color)
        self.indicator.configure(fg=color)

    # ── 操作 ─────────────────────────────────────────────────────────────────
    def _browse(self):
        folder = filedialog.askdirectory(title="选择来源文件夹")
        if folder:
            self.folder_var.set(os.path.normpath(folder))
            self._set_status("文件夹已选择，请点击操作按钮。", SUBTEXT)

    def _run_tool(self, tool: str):
        if self._running:
            return

        folder = self.folder_var.get().strip()
        if not folder:
            self._set_status("⚠  请先选择文件夹！", ERROR)
            return

        self._running = True
        self._lock_buttons(True)
        self._set_status(f"⏳  执行中… {tool.upper()}", "#f0c040")

        if tool == "step":
            thread = threading.Thread(target=self._run_step_with_cleanup, args=(folder,), daemon=True)
        elif tool == "dwg":
            thread = threading.Thread(target=self._run_dwg_with_cleanup, args=(folder,), daemon=True)
        else:
            script = SCRIPT_PDF if tool == "pdf" else SCRIPT_IGES
            label = "PRT → PDF" if tool == "pdf" else "STP → IGES"
            cmd = [RUN_JOURNAL, script, "-args", folder]
            thread = threading.Thread(target=self._exec, args=(cmd, label, folder, tool), daemon=True)

        thread.start()

    def _run_dwg_with_cleanup(self, folder):
        """DWG export: run export script, then cleanup, then report."""
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            dwg_dir = os.path.join(folder, "DWG")

            # Step 1: Export DWG
            self.after(0, self._set_status, "⏳  导出 DWG…", "#f0c040")
            cmd1 = [RUN_JOURNAL, SCRIPT_DWG, "-args", folder]
            r1 = subprocess.run(cmd1, timeout=600, startupinfo=startupinfo)

            # Step 2: Cho NX ghi file xong (poll最多 30s)
            self.after(0, self._set_status, "⏳  等待文件写入…", "#f0c040")
            dwg_count = 0
            for _ in range(6):  # 6 x 5s = 30s
                time.sleep(5)
                dwg_count = len([f for f in os.listdir(dwg_dir) if f.lower().endswith(".dwg")]) if os.path.exists(dwg_dir) else 0
                if dwg_count > 0:
                    break

            # Step 3: Cleanup log files
            self.after(0, self._set_status, "⏳  清理日志文件…", "#f0c040")
            cmd2 = [RUN_JOURNAL, SCRIPT_CLEAN, "-args", folder]
            r2 = subprocess.run(cmd2, timeout=300, startupinfo=startupinfo)

            # Done - check file DWG actually exists + check skipped PRT
            dwg_files = [f for f in os.listdir(dwg_dir) if f.lower().endswith(".dwg")] if os.path.exists(dwg_dir) else []

            # Check PRT > 3MB (skipped by script)
            skipped = []
            for f in os.listdir(folder):
                if f.lower().endswith(".prt"):
                    fpath = os.path.join(folder, f)
                    if os.path.getsize(fpath) > 3 * 1024 * 1024:
                        skipped.append(f)

            if r1.returncode == 0 and len(dwg_files) > 0:
                msg = f"✅  PRT → DWG 完成！({len(dwg_files)} 文件)"
                if skipped:
                    msg += f"  ⚠ {len(skipped)} 文件>3MB需手动导出"
                self.after(0, self._set_status, msg, SUCCESS)
            elif r1.returncode == 0 and len(dwg_files) == 0:
                self.after(0, self._set_status, "❌  DWG 未生成文件", ERROR)
            else:
                self.after(0, self._set_status, "❌  PRT → DWG 出错", ERROR)

        except subprocess.TimeoutExpired:
            self.after(0, self._set_status, "❌  超时 (>10分钟)", ERROR)
        except Exception as exc:
            self.after(0, self._set_status, f"❌  {exc}", ERROR)
        finally:
            self._running = False
            self.after(0, self._lock_buttons, False)

    def _run_step_with_cleanup(self, folder):
        """STEP export: run export script, then cleanup, then report."""
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            step_dir = os.path.join(folder, "STEP")

            # Step 1: Export STEP
            self.after(0, self._set_status, "⏳  导出 STEP…", "#f0c040")
            cmd1 = [RUN_JOURNAL, SCRIPT_STEP, "-args", folder]
            r1 = subprocess.run(cmd1, timeout=600, startupinfo=startupinfo)

            # Step 2: Cleanup log files
            self.after(0, self._set_status, "⏳  清理日志文件…", "#f0c040")
            cmd2 = [RUN_JOURNAL, SCRIPT_CLEAN, "-args", folder]
            r2 = subprocess.run(cmd2, timeout=60, startupinfo=startupinfo)

            # Done - check file STEP actually exists
            step_files = [f for f in os.listdir(step_dir) if f.lower().endswith((".stp", ".step"))] if os.path.exists(step_dir) else []

            if r1.returncode == 0 and len(step_files) > 0:
                self.after(0, self._set_status,
                           f"✅  PRT → STEP 完成！({len(step_files)} 文件)", SUCCESS)
            elif r1.returncode == 0 and len(step_files) == 0:
                self.after(0, self._set_status, "❌  STEP 未生成文件", ERROR)
            else:
                self.after(0, self._set_status, "❌  PRT → STEP 出错", ERROR)

        except subprocess.TimeoutExpired:
            self.after(0, self._set_status, "❌  超时 (>10分钟)", ERROR)
        except Exception as exc:
            self.after(0, self._set_status, f"❌  {exc}", ERROR)
        finally:
            self._running = False
            self.after(0, self._lock_buttons, False)

    def _exec(self, cmd, label, folder="", tool=""):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            result = subprocess.run(
                cmd,
                timeout=600,
                startupinfo=startupinfo,
            )

            # Check output files exist
            out_files = []
            if tool == "pdf":
                pdf_dir = os.path.join(folder, "PDF")
                out_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")] if os.path.exists(pdf_dir) else []
            elif tool == "iges":
                iges_dir = os.path.join(folder, "IGES")
                out_files = [f for f in os.listdir(iges_dir) if f.lower().endswith(".igs")] if os.path.exists(iges_dir) else []

            if result.returncode == 0 and len(out_files) > 0:
                self.after(0, self._set_status,
                           f"✅  {label} 完成！({len(out_files)} 文件)", SUCCESS)
            elif result.returncode == 0 and len(out_files) == 0:
                self.after(0, self._set_status,
                           f"❌  {label} 未生成文件", ERROR)
            else:
                self.after(0, self._set_status,
                           f"❌  {label} 出错", ERROR)
        except FileNotFoundError:
            self.after(0, self._set_status,
                       "❌  找不到 run_journal.exe", ERROR)
        except subprocess.TimeoutExpired:
            self.after(0, self._set_status,
                       "❌  超时 (>10分钟)", ERROR)
        except Exception as exc:
            self.after(0, self._set_status, f"❌  {exc}", ERROR)
        finally:
            self._running = False
            self.after(0, self._lock_buttons, False)

    def _lock_buttons(self, locked: bool):
        state = "disabled" if locked else "normal"
        self.btn_pdf.configure(state=state)
        self.btn_step.configure(state=state)
        self.btn_iges.configure(state=state)
        self.btn_dwg.configure(state=state)


if __name__ == "__main__":
    app = NX12Dashboard()
    app.mainloop()
