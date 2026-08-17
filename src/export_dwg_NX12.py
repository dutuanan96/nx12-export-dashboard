# -*- coding: utf-8 -*-
# NX12 Journal - Export PRT -> DWG
# Python 2.x / IronPython and Python 3 compatible

try:
    import NXOpen
except ImportError:
    NXOpen = None
import os
import sys
import re
import time
import json

# ── Configuration ────────────────────────────────────────────────────────────
MAX_PRT_SIZE_MB = 3.0  # Skip PRT files > MAX_PRT_SIZE_MB (manual export required)

def get_ugii_base_dir():
    """Get the active NX installation directory dynamically."""
    base = os.environ.get("UGII_BASE_DIR")
    if base and os.path.exists(base):
        return base
    candidates = [
        r"C:\Program Files\Siemens\NX 12.0",
        r"C:\Program Files\Siemens\NX2406",
        r"C:\Program Files\Siemens\NX 2406",
        r"C:\Program Files\Siemens\NX",
    ]
    for cand in candidates:
        if os.path.exists(cand):
            return cand
    return r"C:\Program Files\Siemens\NX 12.0"

def sanitize_sheet_name(name):
    """Sanitize sheet name for safe Windows file names."""
    cleaned = re.sub(r'[\\/*?:"<>|]', '-', name)
    cleaned = cleaned.strip()
    return cleaned if cleaned else "Sheet"

def write_result_json(dwg_folder, result_data, lw=None):
    """Write export_result.json atomically using a temporary file."""
    try:
        json_path = os.path.join(dwg_folder, "export_result.json")
        tmp_path = json_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(result_data, f, indent=2)
        if os.path.exists(json_path):
            try:
                os.remove(json_path)
            except:
                pass
        os.rename(tmp_path, json_path)
    except Exception as e:
        if lw is not None:
            try:
                lw.WriteLine("  ERROR writing export_result.json: " + str(e))
            except:
                pass

def cleanup_logs(dwg_folder, base_name=None):
    """Clean up .log files in the DWG directory."""
    if not os.path.exists(dwg_folder):
        return
    for f in os.listdir(dwg_folder):
        if f.lower().endswith(".log"):
            if base_name is None or base_name in f:
                try:
                    os.remove(os.path.join(dwg_folder, f))
                except:
                    pass

def export_single_sheet(theSession, workPart, sheet, output_path, settings_file, lw):
    """Export one drawing sheet to DWG. Returns (success: bool, error_msg: str)."""
    # Pre-clean stale per-file output
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
            lw.WriteLine("       Removed stale output: " + os.path.basename(output_path))
        except Exception as ex_del:
            lw.WriteLine("       ERROR: Cannot delete stale output: " + str(ex_del))
            return False, "Cannot delete stale output: " + str(ex_del)

    dxfdwgCreator = None
    markId = None
    try:
        sheet.Open()
        markId = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "Export DWG " + sheet.Name)

        dxfdwgCreator = theSession.DexManager.CreateDxfdwgCreator()
        dxfdwgCreator.InputFile = workPart.FullPath
        dxfdwgCreator.OutputFile = output_path
        dxfdwgCreator.ExportData = NXOpen.DxfdwgCreator.ExportDataOption.Drawing
        dxfdwgCreator.OutputFileType = NXOpen.DxfdwgCreator.OutputFileTypeOption.Dwg
        dxfdwgCreator.AutoCADRevision = NXOpen.DxfdwgCreator.AutoCADRevisionOptions.R2004
        dxfdwgCreator.SettingsFile = settings_file
        dxfdwgCreator.DrawingList = sheet.Name
        dxfdwgCreator.ViewEditMode = False
        dxfdwgCreator.FlattenAssembly = False
        dxfdwgCreator.ExportScaleValue = "1:1"
        dxfdwgCreator.LayerMask = "1-256"
        dxfdwgCreator.WidthFactorMode = NXOpen.DxfdwgCreator.WidthfactorMethodOptions.AutomaticCalculation

        dxfdwgCreator.Commit()

        # Poll for async DWG translator output (up to 120s)
        for _ in range(240):
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                time.sleep(0.3)
                return True, None
            time.sleep(0.5)

        return False, "DXF/DWG translator completed without output file after 120s"

    except Exception as ex:
        lw.WriteLine("       Error: " + str(ex))
        return False, str(ex)
    finally:
        if dxfdwgCreator is not None:
            try:
                dxfdwgCreator.Destroy()
            except:
                pass
        if markId is not None:
            try:
                theSession.DeleteUndoMark(markId, None)
            except:
                pass

def main():
    theSession = NXOpen.Session.GetSession()
    lw = theSession.ListingWindow
    lw.Open()

    folder = ""
    run_id = None
    specific_file = None

    if len(sys.argv) > 1 and sys.argv[1]:
        first_arg = sys.argv[1]
        if first_arg.lower().endswith(".json") and os.path.exists(first_arg):
            try:
                with open(first_arg, "r", encoding="utf-8") as f_cfg:
                    cfg = json.load(f_cfg)
                folder = cfg.get("folder", "")
                run_id = cfg.get("run_id")
                specific_file = cfg.get("target_file")
            except Exception as e:
                lw.WriteLine("Warning reading task config json: " + str(e))
        else:
            folder = first_arg
    else:
        folder = os.getcwd()

    if not run_id and len(sys.argv) > 2 and sys.argv[2]:
        run_id = sys.argv[2]

    if not specific_file and len(sys.argv) > 3 and sys.argv[3]:
        specific_file = sys.argv[3]

    lw.WriteLine("========================================")
    lw.WriteLine("  EXPORT PRT -> DWG (NX 12.0)")
    lw.WriteLine("  Skip files > %.1f MB" % MAX_PRT_SIZE_MB)
    lw.WriteLine("========================================")
    lw.WriteLine("Directory: " + folder)
    if run_id:
        lw.WriteLine("Run ID: " + str(run_id))

    if not os.path.exists(folder):
        lw.WriteLine("ERROR: Directory not found!")
        lw.Close()
        return

    dwgFolder = os.path.join(folder, "DWG")
    if not os.path.exists(dwgFolder):
        os.makedirs(dwgFolder)

    prtFiles = []
    if specific_file:
        if os.path.exists(os.path.join(folder, specific_file)):
            prtFiles.append(specific_file)
        elif os.path.exists(specific_file):
            prtFiles.append(os.path.basename(specific_file))
        else:
            # Check for direct basename match in folder
            for f in os.listdir(folder):
                if f == specific_file or os.path.splitext(f)[0] == os.path.splitext(specific_file)[0]:
                    prtFiles.append(f)
                    break
    else:
        prtFiles = [f for f in os.listdir(folder) if f.lower().endswith(".prt")]

    result_data = {
        "operation": "prt_to_dwg",
        "run_id": run_id,
        "total": len(prtFiles),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "files": []
    }

    if len(prtFiles) == 0:
        lw.WriteLine("No .prt files found!")
        write_result_json(dwgFolder, result_data)
        lw.Close()
        return

    lw.WriteLine("Found %d PRT files." % len(prtFiles))
    lw.WriteLine("Exporting to: " + dwgFolder)
    lw.WriteLine("")

    # Dynamically locate settings file
    ugii_base = get_ugii_base_dir()
    settingsFile = os.path.join(ugii_base, "dxfdwg", "dxfdwg.def")
    if not os.path.exists(settingsFile):
        settingsFile = r"C:\Program Files\Siemens\NX 12.0\dxfdwg\dxfdwg.def"

    for prtFile in prtFiles:
        prtPath = os.path.join(folder, prtFile)
        baseName = os.path.splitext(prtFile)[0]

        lw.WriteLine("--- " + prtFile + " ---")

        workPart = None

        try:
            lw.WriteLine("  1/4 Opening PRT ...")
            basePart1 = theSession.Parts.OpenBaseDisplay(prtPath)

            if basePart1 is None:
                lw.WriteLine("  ERROR: Could not open part!")
                result_data["failed"] += 1
                result_data["files"].append({
                    "input": prtFile,
                    "output": None,
                    "status": "failed",
                    "error": "Could not open PRT file"
                })
                continue

            workPart = theSession.Parts.Work
            lw.WriteLine("     OK: " + workPart.Name)

            lw.WriteLine("  2/4 Switching to Drafting ...")
            try:
                theSession.ApplicationSwitchImmediate("UG_APP_DRAFTING")
                workPart.Drafting.EnterDraftingApplication()
                lw.WriteLine("     OK: Drafting mode")
            except Exception as exDraft:
                lw.WriteLine("     WARN: " + str(exDraft))

            lw.WriteLine("  3/4 Finding drawing sheets ...")
            sheetList = []
            for ds in workPart.DrawingSheets:
                sheetList.append(ds)
                lw.WriteLine("     Sheet: " + ds.Name)

            lw.WriteLine("     Total: %d sheets" % len(sheetList))

            if len(sheetList) == 0:
                lw.WriteLine("  No drawing sheets - skipping.")
                result_data["skipped"] += 1
                result_data["files"].append({
                    "input": prtFile,
                    "output": None,
                    "status": "skipped",
                    "error": "Skipped: No drawing sheets in part"
                })
                continue

            lw.WriteLine("  4/4 Exporting DWG ...")
            sheetOkOutputs = []
            sheetErrors = []

            for idx, sheet in enumerate(sheetList):
                safeSheetName = sanitize_sheet_name(sheet.Name)
                if len(sheetList) == 1:
                    sheetDwgPath = os.path.join(dwgFolder, baseName + ".dwg")
                else:
                    sheetDwgPath = os.path.join(dwgFolder, "%s_%02d_%s.dwg" % (baseName, idx + 1, safeSheetName))

                lw.WriteLine("     [%d/%d] Sheet: %s" % (idx + 1, len(sheetList), sheet.Name))

                ok, err_sheet = export_single_sheet(theSession, workPart, sheet, sheetDwgPath, settingsFile, lw)

                if ok:
                    fileSize = os.path.getsize(sheetDwgPath)
                    sizeMB = fileSize / 1024.0 / 1024.0
                    lw.WriteLine("       OK: %.1f MB" % sizeMB)
                    rel_output = os.path.join("DWG", os.path.basename(sheetDwgPath)).replace("\\", "/")
                    sheetOkOutputs.append(rel_output)
                else:
                    lw.WriteLine("       Failed: " + str(err_sheet))
                    sheetErrors.append("Sheet '%s': %s" % (sheet.Name, str(err_sheet)))

            if len(sheetOkOutputs) == len(sheetList) and len(sheetList) > 0:
                result_data["success"] += 1
                result_data["files"].append({
                    "input": prtFile,
                    "output": sheetOkOutputs[0] if len(sheetOkOutputs) == 1 else sheetOkOutputs,
                    "status": "success",
                    "error": None
                })
                lw.WriteLine("  Exported %d/%d sheets successfully" % (len(sheetOkOutputs), len(sheetList)))
            else:
                result_data["failed"] += 1
                err_summary = "; ".join(sheetErrors) if sheetErrors else "All sheet exports failed"
                result_data["files"].append({
                    "input": prtFile,
                    "output": sheetOkOutputs if sheetOkOutputs else None,
                    "status": "failed",
                    "error": err_summary
                })
                lw.WriteLine("  Failed to export sheets: " + err_summary)

            lw.WriteLine("  COMPLETED: " + prtFile)
            lw.WriteLine("")

        except Exception as ex:
            lw.WriteLine("  ERROR: " + str(ex))
            result_data["failed"] += 1
            result_data["files"].append({
                "input": prtFile,
                "output": None,
                "status": "failed",
                "error": str(ex)
            })
            lw.WriteLine("")

        finally:
            if workPart is not None:
                try:
                    workPart.Close(NXOpen.BasePart.CloseWholeTree.TrueValue, NXOpen.BasePart.CloseModified.CloseModified, None)
                except:
                    pass

    # Clean up log files only if 100% success; keep logs if there are failures for debugging
    if result_data["failed"] == 0:
        cleanup_logs(dwgFolder)

    write_result_json(dwgFolder, result_data, lw)

    lw.WriteLine("========================================")
    lw.WriteLine("  RESULTS:")
    lw.WriteLine("  Total: %d" % result_data["total"])
    lw.WriteLine("  Success: %d" % result_data["success"])
    lw.WriteLine("  Failed: %d" % result_data["failed"])
    lw.WriteLine("  Skipped: %d" % result_data["skipped"])
    lw.WriteLine("========================================")
    lw.Close()

if __name__ in ("__main__", "__builtin__", "builtins"):
    if NXOpen is not None:
        main()
