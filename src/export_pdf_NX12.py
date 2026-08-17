# -*- coding: utf-8 -*-
# NX12 Journal - Export PRT -> PDF
# Python 2.x / IronPython and Python 3 compatible

try:
    import NXOpen
    import NXOpen.Drawings
except ImportError:
    NXOpen = None
import os
import sys
import json

def write_result_json(pdf_folder, result_data, lw=None):
    """Write export_result.json atomically using a temporary file."""
    try:
        json_path = os.path.join(pdf_folder, "export_result.json")
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

def cleanup_logs(pdf_folder):
    """Clean up any temporary .log files in the output directory."""
    if not os.path.exists(pdf_folder):
        return
    for f in os.listdir(pdf_folder):
        if f.lower().endswith(".log"):
            try:
                os.remove(os.path.join(pdf_folder, f))
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

    lw.WriteLine("========================================")
    lw.WriteLine("  EXPORT PRT -> PDF (NX 12.0)")
    lw.WriteLine("========================================")
    lw.WriteLine("Directory: " + folder)
    if run_id:
        lw.WriteLine("Run ID: " + str(run_id))

    if not os.path.exists(folder):
        lw.WriteLine("ERROR: Directory not found!")
        lw.Close()
        return

    pdfFolder = os.path.join(folder, "PDF")
    if not os.path.exists(pdfFolder):
        os.makedirs(pdfFolder)

    prtFiles = [f for f in os.listdir(folder) if f.lower().endswith(".prt")]

    result_data = {
        "operation": "prt_to_pdf",
        "run_id": run_id,
        "total": len(prtFiles),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "files": []
    }

    if len(prtFiles) == 0:
        lw.WriteLine("No .prt files found!")
        write_result_json(pdfFolder, result_data)
        lw.Close()
        return

    lw.WriteLine("Found %d PRT files." % len(prtFiles))
    lw.WriteLine("Exporting PDF to: " + pdfFolder)
    lw.WriteLine("")

    for prtFile in prtFiles:
        prtPath = os.path.join(folder, prtFile)
        baseName = os.path.splitext(prtFile)[0]
        pdfPath = os.path.join(pdfFolder, baseName + ".pdf")

        lw.WriteLine("--- " + prtFile + " ---")

        # ── Pre-clean stale per-file output ──
        if os.path.exists(pdfPath):
            try:
                os.remove(pdfPath)
                lw.WriteLine("  Removed stale output: " + os.path.basename(pdfPath))
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
        pdfBuilder = None
        markId1 = None

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
                lw.WriteLine("  No drawing sheets found - skipping.")
                result_data["failed"] += 1
                result_data["files"].append({
                    "input": prtFile,
                    "output": None,
                    "status": "failed",
                    "error": "No drawing sheets in part"
                })
                continue

            lw.WriteLine("  4/4 Exporting PDF ...")
            markId1 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "Export PDF")

            pdfBuilder = workPart.PlotManager.CreatePrintPdfbuilder()
            pdfBuilder.Filename = pdfPath
            pdfBuilder.Colors = NXOpen.PrintPDFBuilder.Color.BlackOnWhite
            pdfBuilder.Widths = NXOpen.PrintPDFBuilder.Width.CustomThreeWidths
            pdfBuilder.Size = NXOpen.PrintPDFBuilder.SizeOption.ScaleFactor
            pdfBuilder.Scale = 1.0
            pdfBuilder.XDimension = 215.9
            pdfBuilder.YDimension = 279.4
            pdfBuilder.OutputText = NXOpen.PrintPDFBuilder.OutputTextOption.Polylines
            pdfBuilder.RasterImages = True
            pdfBuilder.ImageResolution = NXOpen.PrintPDFBuilder.ImageResolutionOption.Medium
            pdfBuilder.Watermark = ""
            pdfBuilder.Append = False

            nxSheets = []
            for s in sheetList:
                nxSheets.append(s)
            pdfBuilder.SourceBuilder.SetSheets(nxSheets)

            pdfBuilder.Commit()

            if os.path.exists(pdfPath) and os.path.getsize(pdfPath) > 0:
                lw.WriteLine("     OK: " + os.path.basename(pdfPath))
                result_data["success"] += 1
                rel_output = os.path.join("PDF", os.path.basename(pdfPath)).replace("\\", "/")
                result_data["files"].append({
                    "input": prtFile,
                    "output": rel_output,
                    "status": "success",
                    "error": None
                })
                lw.WriteLine("  COMPLETED: " + prtFile)
            else:
                lw.WriteLine("  WARN: PDF file was not created or empty!")
                result_data["failed"] += 1
                result_data["files"].append({
                    "input": prtFile,
                    "output": None,
                    "status": "failed",
                    "error": "PDF output file not generated or 0 bytes"
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
            if pdfBuilder is not None:
                try:
                    pdfBuilder.Destroy()
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

        lw.WriteLine("")

    # Clean up logs and write manifest
    cleanup_logs(pdfFolder)
    write_result_json(pdfFolder, result_data, lw)

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
