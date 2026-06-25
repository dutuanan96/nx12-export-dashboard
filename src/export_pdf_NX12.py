# NX12 Journal - Xuat PRT -> PDF
# Python 2.x compatible (IronPython)

import NXOpen
import NXOpen.Drawings
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
    lw.WriteLine("  XUAT PRT -> PDF (NX 12.0)")
    lw.WriteLine("========================================")
    lw.WriteLine("Thu muc: " + folder)

    if not os.path.exists(folder):
        lw.WriteLine("LOI: Khong tim thay thu muc!")
        lw.Close()
        return

    pdfFolder = os.path.join(folder, "PDF")
    if not os.path.exists(pdfFolder):
        os.makedirs(pdfFolder)

    prtFiles = [f for f in os.listdir(folder) if f.lower().endswith(".prt")]

    if len(prtFiles) == 0:
        lw.WriteLine("KHONG tim thay file .prt nao!")
        lw.Close()
        return

    lw.WriteLine("Tim thay %d file PRT." % len(prtFiles))
    lw.WriteLine("Xuat PDF vao: " + pdfFolder)
    lw.WriteLine("")

    successCount = 0
    failCount = 0

    for prtFile in prtFiles:
        prtPath = os.path.join(folder, prtFile)
        baseName = os.path.splitext(prtFile)[0]
        pdfPath = os.path.join(pdfFolder, baseName + ".pdf")

        lw.WriteLine("--- " + prtFile + " ---")

        try:
            lw.WriteLine("  1/4 Mo PRT ...")

            basePart1 = theSession.Parts.OpenBaseDisplay(prtPath)

            if basePart1 is None:
                lw.WriteLine("  LOI: Khong mo duoc!")
                failCount += 1
                continue

            workPart = theSession.Parts.Work
            lw.WriteLine("     OK: " + workPart.Name)

            lw.WriteLine("  2/4 Switch Drafting ...")

            try:
                theSession.ApplicationSwitchImmediate("UG_APP_DRAFTING")
                workPart.Drafting.EnterDraftingApplication()
                lw.WriteLine("     OK: Drafting mode")
            except Exception as exDraft:
                lw.WriteLine("     WARN: " + str(exDraft))

            lw.WriteLine("  3/4 Tim drawing sheets ...")

            sheetList = []
            for ds in workPart.DrawingSheets:
                sheetList.append(ds)
                lw.WriteLine("     Sheet: " + ds.Name)

            lw.WriteLine("     Tong: %d sheet" % len(sheetList))

            if len(sheetList) == 0:
                lw.WriteLine("  KHONG co drawing sheet - bo qua.")
                workPart.Close(1, 1, None)
                failCount += 1
                continue

            lw.WriteLine("  4/4 Xuat PDF ...")

            markId1 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "Xuat PDF")

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
            pdfBuilder.Destroy()

            theSession.DeleteUndoMark(markId1, None)

            if os.path.exists(pdfPath):
                lw.WriteLine("     OK: " + os.path.basename(pdfPath))
                successCount += 1
            else:
                lw.WriteLine("  WARN: File PDF khong duoc tao!")
                failCount += 1

            workPart.Close(1, 1, None)

            lw.WriteLine("  HOAN THANH: " + prtFile)
            lw.WriteLine("")

        except Exception as ex:
            lw.WriteLine("  LOI: " + str(ex))
            failCount += 1
            lw.WriteLine("")

    lw.WriteLine("========================================")
    lw.WriteLine("  KET QUA:")
    lw.WriteLine("  Thanh cong: %d / %d" % (successCount, successCount + failCount))
    lw.WriteLine("  That bai: %d" % failCount)
    lw.WriteLine("========================================")
    lw.Close()

main()
