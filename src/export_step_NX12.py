# NX12 Journal - Xuat PRT -> STEP
# Python 2.x compatible (IronPython)
# Fix: cleanup logs inside same journal with retry

import NXOpen
import os
import sys
import time

def delete_with_retry(filepath, lw, max_attempts=8, base_delay=0.5):
    for attempt in range(1, max_attempts + 1):
        try:
            if not os.path.exists(filepath):
                return True
            os.remove(filepath)
            return True
        except Exception as ex:
            lw.WriteLine("  [retry %d/%d] Chua xoa duoc %s: %s" % (
                attempt, max_attempts, os.path.basename(filepath), str(ex)))
            if attempt < max_attempts:
                time.sleep(base_delay * (2 ** (attempt - 1)))
    return False

def main():
    theSession = NXOpen.Session.GetSession()
    lw = theSession.ListingWindow
    lw.Open()

    folder = ""
    if len(sys.argv) > 1 and sys.argv[1]:
        folder = sys.argv[1]
    else:
        folder = os.getcwd()

    lw.WriteLine("========================================")
    lw.WriteLine("  XUAT PRT -> STEP (NX 12.0)")
    lw.WriteLine("========================================")
    lw.WriteLine("Thu muc: " + folder)

    if not os.path.exists(folder):
        lw.WriteLine("LOI: Khong tim thay thu muc!")
        lw.Close()
        return

    stepFolder = os.path.join(folder, "STEP")
    if not os.path.exists(stepFolder):
        os.makedirs(stepFolder)

    prtFiles = [f for f in os.listdir(folder) if f.lower().endswith(".prt")]

    if len(prtFiles) == 0:
        lw.WriteLine("KHONG tim thay file .prt nao!")
        lw.Close()
        return

    lw.WriteLine("Tim thay %d file PRT." % len(prtFiles))
    lw.WriteLine("Xuat STEP vao: " + stepFolder)
    lw.WriteLine("")

    settingsFile = "C:\\Program Files\\Siemens\\NX 12.0\\step214ug\\ugstep214.def"

    successCount = 0
    failCount = 0

    for prtFile in prtFiles:
        prtPath = os.path.join(folder, prtFile)
        baseName = os.path.splitext(prtFile)[0]
        stepPath = os.path.join(stepFolder, baseName + ".stp")

        lw.WriteLine("--- " + prtFile + " ---")

        try:
            lw.WriteLine("  1/3 Mo PRT ...")

            basePart1 = theSession.Parts.OpenBaseDisplay(prtPath)

            if basePart1 is None:
                lw.WriteLine("  LOI: Khong mo duoc!")
                failCount += 1
                continue

            workPart = theSession.Parts.Work
            lw.WriteLine("     OK: " + workPart.Name)

            lw.WriteLine("  2/3 Xuat STEP ...")

            markId1 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "Xuat STEP")

            stepCreator1 = theSession.DexManager.CreateStepCreator()
            stepCreator1.ExportAs = NXOpen.StepCreator.ExportAsOption.Ap214
            stepCreator1.InputFile = workPart.FullPath
            stepCreator1.OutputFile = stepPath
            stepCreator1.SettingsFile = settingsFile
            stepCreator1.FileSaveFlag = False
            stepCreator1.LayerMask = "1-256"

            nXObject1 = stepCreator1.Commit()
            stepCreator1.Destroy()

            theSession.DeleteUndoMark(markId1, None)

            if os.path.exists(stepPath):
                lw.WriteLine("     OK: " + os.path.basename(stepPath))
                successCount += 1
            else:
                lw.WriteLine("  WARN: File STEP khong duoc tao!")
                failCount += 1

            workPart.Close(1, 1, None)

            # Xoa file log ngay lap tuc sau khi export
            lw.WriteLine("  3/3 Xoa log ...")
            logPath = os.path.join(stepFolder, baseName + ".log")
            if delete_with_retry(logPath, lw):
                lw.WriteLine("     Log da xoa.")
            else:
                lw.WriteLine("     Khong xoa duoc log.")

            lw.WriteLine("  HOAN THANH: " + prtFile)
            lw.WriteLine("")

        except Exception as ex:
            lw.WriteLine("  LOI: " + str(ex))
            failCount += 1
            lw.WriteLine("")

    # Sweep cuoi cung
    lw.WriteLine("--- Don dep file log cuoi cung ---")
    if os.path.exists(stepFolder):
        for f in os.listdir(stepFolder):
            if f.endswith(".log"):
                fpath = os.path.join(stepFolder, f)
                if delete_with_retry(fpath, lw):
                    lw.WriteLine("  Da xoa: " + f)
                else:
                    lw.WriteLine("  KHONG xoa: " + f)

    lw.WriteLine("========================================")
    lw.WriteLine("  KET QUA:")
    lw.WriteLine("  Thanh cong: %d / %d" % (successCount, successCount + failCount))
    lw.WriteLine("  That bai: %d" % failCount)
    lw.WriteLine("========================================")
    lw.Close()

main()
