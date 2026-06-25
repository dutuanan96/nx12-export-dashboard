# NX12 Journal - Nhap STP -> Xuat IGES
# Python 2.x compatible (IronPython)

import NXOpen
import os
import sys

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
    lw.WriteLine("  NHAP STP -> XUAT IGES (NX 12.0)")
    lw.WriteLine("========================================")
    lw.WriteLine("Thu muc: " + folder)
    lw.WriteLine("")

    if not os.path.exists(folder):
        lw.WriteLine("LOI: Khong tim thay thu muc!")
        lw.Close()
        return

    igesFolder = os.path.join(folder, "IGES")
    if not os.path.exists(igesFolder):
        os.makedirs(igesFolder)

    # Tim file STP/STEP
    stpFiles = [f for f in os.listdir(folder) if f.lower().endswith((".stp", ".step"))]

    if len(stpFiles) == 0:
        lw.WriteLine("KHONG tim thay file .stp / .step nao!")
        lw.Close()
        return

    lw.WriteLine("Tim thay %d file STP." % len(stpFiles))
    lw.WriteLine("Xuat IGES vao: " + igesFolder)
    lw.WriteLine("")

    # Luu danh sach file truoc
    filesBefore = set(os.listdir(folder))

    successCount = 0
    failCount = 0

    for stpFile in stpFiles:
        stpPath = os.path.join(folder, stpFile)
        baseName = os.path.splitext(stpFile)[0]
        igesPath = os.path.join(igesFolder, baseName + ".igs")

        lw.WriteLine("--- " + stpFile + " ---")

        try:
            # Mo STP
            lw.WriteLine("  1/2 Mo STP ...")

            basePart1 = theSession.Parts.OpenBaseDisplay(stpPath)

            if basePart1 is None:
                lw.WriteLine("  LOI: Khong mo duoc!")
                failCount += 1
                continue

            workPart = theSession.Parts.Work
            lw.WriteLine("     OK: " + workPart.Name)

            # Xuat IGES
            lw.WriteLine("  2/2 Xuat IGES ...")

            markId1 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "Xuat IGES")

            igesCreator = theSession.DexManager.CreateIgesCreator()
            igesCreator.ExportFrom = NXOpen.IgesCreator.ExportFromOption.DisplayPart
            igesCreator.OutputFile = igesPath
            igesCreator.ExportModelData = True
            igesCreator.ExportDrawings = False
            igesCreator.BcurveTol = 0.058

            igesCreator.Commit()
            igesCreator.Destroy()

            theSession.DeleteUndoMark(markId1, None)

            if os.path.exists(igesPath):
                lw.WriteLine("     OK: " + os.path.basename(igesPath))
                successCount += 1
            else:
                lw.WriteLine("  WARN: File IGES khong duoc tao!")
                failCount += 1

            workPart.Close(1, 1, None)

            lw.WriteLine("  HOAN THANH: " + stpFile)
            lw.WriteLine("")

        except Exception as ex:
            lw.WriteLine("  LOI: " + str(ex))
            failCount += 1
            lw.WriteLine("")

    # Don dep file tam (chi giu .igs, .stp/.step, bo qua file moi)
    lw.WriteLine("--- Don dep file tam ---")
    deletedCount = 0
    filesAfter = os.listdir(folder)

    for newFile in filesAfter:
        ext = os.path.splitext(newFile)[1].lower()

        if ext in (".igs", ".stp", ".step"):
            continue

        if newFile in filesBefore:
            continue

        fpath = os.path.join(folder, newFile)
        try:
            os.remove(fpath)
            lw.WriteLine("  Da xoa: " + newFile)
            deletedCount += 1
        except Exception as ex:
            lw.WriteLine("  Khong xoa duoc: " + newFile + " - " + str(ex))

    # Don dep trong IGES folder (chi giu .igs)
    if os.path.exists(igesFolder):
        for f in os.listdir(igesFolder):
            ext = os.path.splitext(f)[1].lower()
            if ext != ".igs":
                try:
                    os.remove(os.path.join(igesFolder, f))
                    lw.WriteLine("  Da xoa trong IGES: " + f)
                    deletedCount += 1
                except:
                    pass

    lw.WriteLine("  Tong da xoa: %d file tam." % deletedCount)
    lw.WriteLine("")

    lw.WriteLine("========================================")
    lw.WriteLine("  KET QUA:")
    lw.WriteLine("  Thanh cong: %d / %d" % (successCount, successCount + failCount))
    lw.WriteLine("  That bai: %d" % failCount)
    lw.WriteLine("========================================")
    lw.Close()

main()
