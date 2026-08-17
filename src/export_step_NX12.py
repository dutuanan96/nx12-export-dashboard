# -*- coding: utf-8 -*-
# NX12 Journal - Export PRT -> STEP (AP214)
# Python 2.x / IronPython and Python 3 compatible

try:
    import NXOpen
except ImportError:
    NXOpen = None
import os
import sys
import time
import json

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

def write_result_json(step_folder, result_data, lw=None):
    """Write export_result.json atomically using a temporary file."""
    try:
        json_path = os.path.join(step_folder, "export_result.json")
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

def delete_with_retry(filepath, lw, max_attempts=5, base_delay=0.3):
    """Delete file with exponential retry."""
    for attempt in range(1, max_attempts + 1):
        try:
            if not os.path.exists(filepath):
                return True
            os.remove(filepath)
            return True
        except Exception as ex:
            if attempt < max_attempts:
                time.sleep(base_delay * (2 ** (attempt - 1)))
    return False

def cleanup_logs(step_folder, lw):
    """Clean up all .log files in the STEP output folder."""
    if not os.path.exists(step_folder):
        return
    for f in os.listdir(step_folder):
        if f.lower().endswith(".log"):
            fpath = os.path.join(step_folder, f)
            delete_with_retry(fpath, lw)

def main():
    theSession = NXOpen.Session.GetSession()
    lw = theSession.ListingWindow
    lw.Open()

    folder = ""
    run_id = None
    if len(sys.argv) > 1 and sys.argv[1]:
        folder = sys.argv[1]
    else:
        folder = os.getcwd()

    if len(sys.argv) > 2 and sys.argv[2]:
        run_id = sys.argv[2]

    lw.WriteLine("========================================")
    lw.WriteLine("  EXPORT PRT -> STEP (NX 12.0)")
    lw.WriteLine("========================================")
    lw.WriteLine("Directory: " + folder)
    if run_id:
        lw.WriteLine("Run ID: " + str(run_id))

    if not os.path.exists(folder):
        lw.WriteLine("ERROR: Directory not found!")
        lw.Close()
        return

    stepFolder = os.path.join(folder, "STEP")
    if not os.path.exists(stepFolder):
        os.makedirs(stepFolder)

    prtFiles = [f for f in os.listdir(folder) if f.lower().endswith(".prt")]

    result_data = {
        "operation": "prt_to_step",
        "run_id": run_id,
        "total": len(prtFiles),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "files": []
    }

    if len(prtFiles) == 0:
        lw.WriteLine("No .prt files found!")
        write_result_json(stepFolder, result_data)
        lw.Close()
        return

    lw.WriteLine("Found %d PRT files." % len(prtFiles))
    lw.WriteLine("Exporting STEP to: " + stepFolder)
    lw.WriteLine("")

    # Dynamically locate settings file
    ugii_base = get_ugii_base_dir()
    settingsFile = os.path.join(ugii_base, "step214ug", "ugstep214.def")
    if not os.path.exists(settingsFile):
        settingsFile = r"C:\Program Files\Siemens\NX 12.0\step214ug\ugstep214.def"

    for prtFile in prtFiles:
        prtPath = os.path.join(folder, prtFile)
        baseName = os.path.splitext(prtFile)[0]
        stepPath = os.path.join(stepFolder, baseName + ".stp")

        lw.WriteLine("--- " + prtFile + " ---")

        # ── Pre-clean stale per-file output ──
        if os.path.exists(stepPath):
            try:
                os.remove(stepPath)
                lw.WriteLine("  Removed stale output: " + os.path.basename(stepPath))
            except Exception as ex_del:
                err_msg = "Cannot delete stale output file: " + str(ex_del)
                lw.WriteLine("  ERROR: " + err_msg)
                result_data["failed"] += 1
                result_data["files"].append({
                    "input": prtFile,
                    "output": None,
                    "status": "failed",
                    "error": err_msg
                })
                lw.WriteLine("")
                continue

        workPart = None
        stepCreator = None
        markId1 = None

        try:
            lw.WriteLine("  1/3 Opening PRT ...")
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

            lw.WriteLine("  2/3 Exporting STEP ...")
            markId1 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "Export STEP")

            stepCreator = theSession.DexManager.CreateStepCreator()
            stepCreator.ExportAs = NXOpen.StepCreator.ExportAsOption.Ap214
            stepCreator.InputFile = workPart.FullPath
            stepCreator.OutputFile = stepPath
            stepCreator.SettingsFile = settingsFile
            stepCreator.FileSaveFlag = False
            stepCreator.LayerMask = "1-256"

            stepCreator.Commit()

            # Poll for asynchronous translator completion (up to 10s)
            for _ in range(30):
                if os.path.exists(stepPath) and os.path.getsize(stepPath) > 0:
                    break
                time.sleep(0.3)

            # Check output
            if os.path.exists(stepPath) and os.path.getsize(stepPath) > 0:
                lw.WriteLine("     OK: " + os.path.basename(stepPath))
                result_data["success"] += 1
                rel_output = os.path.join("STEP", os.path.basename(stepPath)).replace("\\", "/")
                result_data["files"].append({
                    "input": prtFile,
                    "output": rel_output,
                    "status": "success",
                    "error": None
                })
                lw.WriteLine("  COMPLETED: " + prtFile)
            else:
                lw.WriteLine("  WARN: STEP file was not created or empty!")
                result_data["failed"] += 1
                result_data["files"].append({
                    "input": prtFile,
                    "output": None,
                    "status": "failed",
                    "error": "STEP output file not generated or 0 bytes"
                })

        except Exception as ex:
            lw.WriteLine("  ERROR: " + str(ex))
            result_data["failed"] += 1
            result_data["files"].append({
                "input": prtFile,
                "output": None,
                "status": "failed",
                "error": str(ex)
            })

        finally:
            if stepCreator is not None:
                try:
                    stepCreator.Destroy()
                except:
                    pass
            if markId1 is not None:
                try:
                    theSession.DeleteUndoMark(markId1, None)
                except:
                    pass
            if workPart is not None:
                try:
                    workPart.Close(NXOpen.BasePart.CloseWholeTree.TrueValue, NXOpen.BasePart.CloseModified.CloseModified, None)
                except:
                    pass

        # Clean per-file log
        logPath = os.path.join(stepFolder, baseName + ".log")
        delete_with_retry(logPath, lw)
        lw.WriteLine("")

    # Final cleanup of all log files in STEP directory
    cleanup_logs(stepFolder, lw)
    write_result_json(stepFolder, result_data, lw)

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
