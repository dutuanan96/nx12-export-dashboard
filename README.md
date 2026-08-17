# NX12 Export Dashboard

A high-reliability, dark-themed utility for batch exporting Siemens NX 12.0 models to PDF, STEP, IGES, and DWG with exact manifest verification.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![NX](https://img.shields.io/badge/Siemens%20NX-12.0%20(Verified)-green)
![Version](https://img.shields.io/badge/Release-v1.0.0-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

- **Batch PRT → PDF**: Automatic Drafting application switch and multi-sheet drawing export.
- **Batch PRT → STEP (AP214)**: Solid and surface export with dynamic settings resolution (`ugstep214.def`).
- **Batch STP/STEP → IGES**: Automatic part creation and export with true structural sanity validation (verifies Section cards `G`, `D`, `P`, `T` at column 72).
- **Batch PRT → DWG**: Multi-sheet drawing export using official NX `DrawingList` selection with indexed collision-free filenames (`Part_01_SheetName.dwg`) and customizable size limits (`MAX_PRT_SIZE_MB = 3.0`).
- **Exact Manifest Reporting**: Every journal outputs an atomic `export_result.json` tracking per-file status: `success`, `failed`, or `skipped`.
- **Run ID Integrity**: Dashboard generates a unique `run_id` per batch run and validates the matching journal manifest, eliminating stale manifest bugs.
- **Stale Output Protection**: Pre-cleans existing output files per file before invoking NX translators to prevent false positive successes.
- **Robust Resource Management**: Strict `try...finally` blocks ensure builder destruction (`Destroy()`), undo mark cleanup (`DeleteUndoMark`), and part closing (`CloseWholeTree`) even upon exceptions.
- **Automatic Log Cleanup**: Eliminates temporary NX translator logs (`.log`) after execution.
- **Portable Dynamic Detection**: Automatically discovers active NX installation via `UGII_BASE_DIR` or system directories.
- **Modern Dark UI**: Compact `490x385` layout, responsive horizontal scaling, 2-tier Status Card, placeholder inputs, and Windows High-DPI scaling support.

---

## Compatibility

| Platform / CAD | Status | Details |
| :--- | :--- | :--- |
| **Siemens NX 12.0** | **VERIFIED / TESTED** | 100% PASS on automated regression test suite via `run_journal.exe`. |
| **Siemens NX 2406** | **PATH DETECTION INCLUDED** | Dynamic path search includes NX 2406 paths; runtime translation compatibility should be separately validated. |

---

## UI Layout

```
┌─────────────────────────────────────────────────────────┐
│ ⚙  NX12 批量导出工具                            俞俊安  │
├─────────────────────────────────────────────────────────┤
│ 工作文件夹                                              │
│ [ D:\CAD\Models\ProjectA                          ] [📂 浏览]│
│                                                         │
│ ┌───────────────────────────┬─────────────────────────┐ │
│ │ 📄  导出 PRT → PDF         │ 📦  导出 PRT → STEP     │ │
│ ├───────────────────────────┼─────────────────────────┤ │
│ │ 🔄  导入 STP → IGES        │ 📐  导出 PRT → DWG      │ │
│ └───────────────────────────┴─────────────────────────┘ │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ●  导出全部成功                           [📋 查看详情] │ │
│ │    最近结果: 10 成功 · 0 失败 · 共 10 个文件           │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│     NX12 Export Dashboard v1.0.0  ·  Developed by 俞俊安 │
└─────────────────────────────────────────────────────────┘
```

---

## Requirements

- **OS**: Windows 10 / 11 (64-bit)
- **CAD**: Siemens NX 12.0 (with `run_journal.exe`)
- **Python**: 3.11+ (for development/source mode)
- **PyInstaller**: (for compiling standalone executable)

---

## Installation & Usage

### Option 1: Standalone Executable (Recommended)
Download `NX12_Dashboard_new.exe` from the latest [Releases](https://github.com/dutuanan96/nx12-export-dashboard/releases) and run directly without Python installation.

### Option 2: Run from Source
```bash
git clone https://github.com/dutuanan96/nx12-export-dashboard.git
cd nx12-export-dashboard
pip install -r requirements.txt
python src/nx12_dashboard.py
```

### Option 3: Build Standalone Executable
```bash
python -m PyInstaller --onefile --windowed --add-data "src;src" --name NX12_Dashboard_new src/nx12_dashboard.py
```

---

## Project Structure

```
nx12-export-dashboard/
├── src/
│   ├── nx12_dashboard.py              # Main dashboard (Tkinter Dark GUI & Manifest parser)
│   ├── export_pdf_NX12.py             # NX12 Journal: PRT → PDF
│   ├── export_step_NX12.py            # NX12 Journal: PRT → STEP (AP214)
│   ├── export_dwg_NX12.py             # NX12 Journal: PRT → DWG (Multi-sheet indexed)
│   └── import_stp_export_iges_NX12.py # NX12 Journal: STP → IGES (Structural validation)
├── requirements.txt                   # Build dependencies
├── README.md                          # Documentation
├── .hermes.md                         # Architecture & coding guidelines
├── .gitignore                         # Git exclusion rules
└── LICENSE                            # MIT License
```

---

## Manifest Schema (`export_result.json`)

Each export operation writes an atomic manifest file `export_result.json` in the respective subfolder:

```json
{
  "operation": "prt_to_dwg",
  "run_id": "a1b2c3d4e5f6",
  "total": 3,
  "success": 2,
  "failed": 0,
  "skipped": 1,
  "files": [
    {
      "input": "Part_MultiSheet.prt",
      "output": [
        "DWG/Part_MultiSheet_01_Sheet1.dwg",
        "DWG/Part_MultiSheet_02_Sheet2.dwg"
      ],
      "status": "success",
      "error": null
    },
    {
      "input": "Part_Large.prt",
      "output": null,
      "status": "skipped",
      "error": "Skipped: 4.2 MB > 3.0 MB (manual export required)"
    }
  ]
}
```

---

## Author & Attribution

- **Developed by**: **俞俊安** (Yu Jun'an)
- **Target CAD Environment**: Siemens NX 12.0 (金汰家具 / SONGMICS HOME manufacturing workflow)

---

## License

[MIT License](LICENSE)
