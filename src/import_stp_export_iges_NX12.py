# -*- coding: utf-8 -*-
# NX12 Journal - Import STP -> Export IGES
# Python 2.x / IronPython and Python 3 compatible

try:
    import NXOpen
except ImportError:
    NXOpen = None
import os
import sys
import time
import json

def is_valid_iges(filepath, min_size=500):
    """
    Structural sanity check for exported IGES file.
    IGES files have standard 80-char card images with section identifiers (S, G, D, P, T) in col 72 (index 72).
    A valid IGES file must contain at least the G, D, P, and T sections and meet min_size.
    """
    try:
        size = os.path.getsize(filepath)
        if size < min_size:
            return False
        sections = set()
        with open(filepath, "rb") as f:
            for line in f:
                line_bytes = line.rstrip(b"\r\n")
                if len(line_bytes) >= 73:
                    sec_byte = line_bytes[72:73]
                    if sec_byte in (b"S", b"G", b"D", b"P", b"T"):
                        sections.add(sec_byte.decode("ascii", errors="ignore"))
        required_sections = {"G", "D", "P", "T"}
        return required_sections.issubset(sections)
    except Exception:
        return False

def cleanup_temp_files(folder, iges_folder, lw=None):
    """
    Clean up all intermediate PRT and LOG files generated during STP->IGES translation.
    In the STP folder, keeps ONLY .stp and .step files.
    In the IGES folder, keeps ONLY .igs and export_result.json.
    """
    deleted_count = 0
    if os.path.exists(folder):
        for f in os.listdir(folder):
            fpath = os.path.join(folder, f)
            if os.path.isdir(fpath):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext not in (".stp", ".step"):
                for _ in range(5):
                    try:
                        os.remove(fpath)
                        if lw:
                            lw.WriteLine("  Deleted temp file: " + f)
                        deleted_count += 1
                        break
                    except Exception:
                        time.sleep(0.2)

    if os.path.exists(iges_folder):
        for f in os.listdir(iges_folder):
            fpath = os.path.join(iges_folder, f)
            if os.path.isdir(fpath):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext not in (".igs", ".json", ".tmp"):
                for _ in range(5):
                    try:
                        os.remove(fpath)
                        if lw:
                            lw.WriteLine("  Deleted in IGES folder: " + f)
                        deleted_count += 1
                        break
                    except Exception:
                        time.sleep(0.2)

    return deleted_count

def write_result_json(iges_folder, result_data, lw=None):
    """Write export_result.json atomically using a temporary file."""
    try:
        json_path = os.path.join(iges_folder, "export_result.json")
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

    igesFolder = os.path.join(folder, "IGES")
    if not os.path.exists(igesFolder):
        os.makedirs(igesFolder)

    result_data = {
        "operation": "stp_to_iges",
        "run_id": run_id,
        "total": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "files": []
    }

    lw.WriteLine("========================================")
    lw.WriteLine("  NX12 BATCH IMPORT STP -> EXPORT IGES")
    lw.WriteLine("  Folder: " + folder)
    if run_id:
        lw.WriteLine("  Run ID: " + str(run_id))
    lw.WriteLine("========================================")
    lw.WriteLine("")

    # Tim tat ca file .stp / .step trong folder
    stpFiles = []
    for f in os.listdir(folder):
        ext = os.path.splitext(f)[1].lower()
        if ext in (".stp", ".step"):
            stpFiles.append(f)

    result_data["total"] = len(stpFiles)

    if len(stpFiles) == 0:
        lw.WriteLine("Khong tim thay file .stp / .step nao!")
        lw.Close()
        write_result_json(igesFolder, result_data, lw)
        return

    lw.WriteLine("Tim thay %d file STP can chuyen doi:" % len(stpFiles))
    for f in stpFiles:
        lw.WriteLine("  - " + f)
    lw.WriteLine("")

    # Ghi nhan file truoc khi xu ly de cleanup
    filesBefore = set(os.listdir(folder))

    for i, stpFile in enumerate(stpFiles):
        baseName = os.path.splitext(stpFile)[0]
        stpPath = os.path.join(folder, stpFile)
        igesPath = os.path.join(igesFolder, baseName + ".igs")

        lw.WriteLine("----------------------------------------")
        lw.WriteLine("[%d/%d] Dang xu ly: %s" % (i + 1, len(stpFiles), stpFile))

        # Stale output pre-cleanup
        if os.path.exists(igesPath):
            try:
                os.remove(igesPath)
                lw.WriteLine("  Cleaned up stale output: " + os.path.basename(igesPath))
            except Exception as e_del:
                lw.WriteLine("  ERROR: Could not remove stale IGES file: " + str(e_del))
                result_data["failed"] += 1
                result_data["files"].append({
                    "input": stpFile,
                    "output": None,
                    "status": "failed",
                    "error": "Could not remove stale output file: " + str(e_del)
                })
                continue

        workPart = None
        igesCreator = None
        markId1 = None

        try:
            lw.WriteLine("  1/2 Opening STP ...")
            res = theSession.Parts.OpenActiveDisplay(stpPath, NXOpen.DisplayPartOption.AllowAdditional)
            loadStatus = None
            if isinstance(res, tuple):
                basePart1 = res[0]
                if len(res) > 1:
                    loadStatus = res[1]
            else:
                basePart1 = res

            if loadStatus is not None and hasattr(loadStatus, "Dispose"):
                try:
                    loadStatus.Dispose()
                except:
                    pass

            workPart = theSession.Parts.Work or theSession.Parts.Display or basePart1

            if workPart is None:
                lw.WriteLine("  ERROR: Could not open STP file!")
                result_data["failed"] += 1
                result_data["files"].append({
                    "input": stpFile,
                    "output": None,
                    "status": "failed",
                    "error": "Could not open STP file"
                })
                continue

            lw.WriteLine("     OK: " + workPart.Name)

            lw.WriteLine("  2/2 Exporting IGES ...")
            markId1 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "Export IGES")

            igesCreator = theSession.DexManager.CreateIgesCreator()
            igesCreator.InputFile = workPart.FullPath
            igesCreator.OutputFile = igesPath
            igesCreator.ExportModelData = True
            igesCreator.ExportDrawings = True
            igesCreator.ObjectTypes.Curves = True
            igesCreator.ObjectTypes.Surfaces = True
            igesCreator.ObjectTypes.Solids = True
            igesCreator.ObjectTypes.Annotations = True
            igesCreator.ObjectTypes.Structures = True
            igesCreator.MapTabCylToBSurf = True
            igesCreator.BcurveTol = 0.0508
            igesCreator.IdenticalPointResolution = 0.001
            igesCreator.MaxThreeDMdlSpace = 10000.0
            igesCreator.MapRevolvedFacesTo = NXOpen.IgesCreator.MapRevolvedFacesOption.BSurfaces
            igesCreator.MapCrossHatchTo = NXOpen.IgesCreator.CrossHatchMapEnum.SectionArea
            igesCreator.FileSaveFlag = False
            igesCreator.LayerMask = "1-256"
            igesCreator.DrawingList = ""
            igesCreator.ViewList = "Top,Front,Right,Back,Bottom,Left,Isometric,Trimetric,User Defined"
            settingsFile = r"C:\Program Files\Siemens\NX 12.0\iges\igesexport.def"
            if os.path.exists(settingsFile):
                igesCreator.SettingsFile = settingsFile

            igesCreator.Commit()

            # Poll for async completion (up to 60s)
            for _ in range(120):
                if is_valid_iges(igesPath, min_size=500):
                    time.sleep(0.3)
                    break
                time.sleep(0.5)

            if is_valid_iges(igesPath, min_size=500):
                size_bytes = os.path.getsize(igesPath)
                lw.WriteLine("     OK: %s (%d bytes)" % (os.path.basename(igesPath), size_bytes))
                result_data["success"] += 1
                rel_output = os.path.join("IGES", os.path.basename(igesPath)).replace("\\", "/")
                result_data["files"].append({
                    "input": stpFile,
                    "output": rel_output,
                    "status": "success",
                    "error": None
                })
                lw.WriteLine("  COMPLETED: " + stpFile)
            else:
                lw.WriteLine("  WARN: IGES file was not created or invalid structure/size!")
                result_data["failed"] += 1
                result_data["files"].append({
                    "input": stpFile,
                    "output": None,
                    "status": "failed",
                    "error": "IGES output file not generated or invalid (< 500 bytes)"
                })

        except Exception as ex:
            lw.WriteLine("  ERROR: " + str(ex))
            result_data["failed"] += 1
            result_data["files"].append({
                "input": stpFile,
                "output": None,
                "status": "failed",
                "error": str(ex)
            })

        finally:
            if igesCreator is not None:
                try:
                    igesCreator.Destroy()
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
            try:
                theSession.Parts.CloseAll(NXOpen.BasePart.CloseModified.CloseModified, None)
            except:
                pass

        lw.WriteLine("")

    # Clean up all temporary files generated during conversion
    lw.WriteLine("--- Cleaning temporary files ---")
    deletedCount = cleanup_temp_files(folder, igesFolder, lw)
    lw.WriteLine("  Total temporary files deleted: %d" % deletedCount)
    lw.WriteLine("")

    write_result_json(igesFolder, result_data, lw)

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
