# NX12 Export Dashboard

A dark-themed Tkinter dashboard for automating Siemens NX 12.0 file exports.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![NX](https://img.shields.io/badge/Siemens%20NX-12.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Export PRT → PDF** (with auto Drafting mode switch)
- **Export PRT → STEP** (AP214 format)
- **Import STP → IGES** (batch conversion)
- **Export PRT → DWG** (AutoCAD R2004, auto size optimization)
- **Auto cleanup** log files after export
- **Size limit** for DWG exports (>3MB PRT files skipped with notification)

## Screenshots

Dark theme UI with 2x2 button layout:

```
┌──────────────┬──────────────┐
│ 📄 PRT → PDF │ 📦 PRT → STEP│
├──────────────┼──────────────┤
│ 🔄 STP → IGES│ 📐 PRT → DWG│
└──────────────┴──────────────┘
```

## Requirements

- Windows 10/11
- Siemens NX 12.0 (or NX2406)
- Python 3.11+
- PyInstaller (for building .exe)

## Installation

### Option 1: Run from source

```bash
pip install pyinstaller
python nx12_dashboard.py
```

### Option 2: Build .exe

```bash
pyinstaller --onefile --windowed --name NX12_Dashboard_new src/nx12_dashboard.py
```

The .exe will be in `dist/NX12_Dashboard_new.exe`

## Project Structure

```
nx12-export-dashboard/
├── src/
│   ├── nx12_dashboard.py          # Main dashboard (Tkinter GUI)
│   ├── export_pdf_NX12.py         # NX12 Journal: PRT → PDF
│   ├── export_step_NX12.py        # NX12 Journal: PRT → STEP
│   ├── export_dwg_NX12.py         # NX12 Journal: PRT → DWG
│   ├── import_stp_export_iges_NX12.py  # NX12 Journal: STP → IGES
│   └── cleanup_step_logs.cs       # NX12 Journal: Cleanup log files
├── README.md
├── requirements.txt
├── .gitignore
└── LICENSE
```

## How It Works

1. User selects a folder containing .prt files
2. Dashboard calls `run_journal.exe` to execute NX12 Journal scripts
3. NX12 opens each .prt file, switches to Drafting mode, and exports
4. Dashboard monitors progress and displays status
5. Log files are automatically cleaned up

## Configuration

Edit `export_dwg_NX12.py` to change DWG export settings:

```python
MAX_PRT_SIZE_MB = 3.0       # Skip PRT files > 3MB
```

## Author

**俞俊安** (Yu Jun'an)

Developed at 金汰家具 (Jintai Furniture) for SONGMICS HOME manufacturing.

## License

MIT License - feel free to use and modify.

## Notes

- Requires Siemens NX 12.0 installed at `C:\Program Files\Siemens\NX 12.0`
- For NX2406, update the path in `export_dwg_NX12.py`
- Dashboard runs on Windows only (Tkinter + NX12 API)
