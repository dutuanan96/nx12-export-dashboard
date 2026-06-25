# NX12 Journal - Xuat PRT -> DWG
# Python 2.x compatible (IronPython)
# VERSION 4: Skip file PRT > 3MB + cleanup .log + tiếng Trung

import NXOpen
import os
import sys

# ── Cau hinh ──────────────────────────────────────────────────
MAX_PRT_SIZE_MB = 3.0       # Bo qua PRT > 3MB (can xuat thu cong)

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
    lw.WriteLine("  导出 PRT -> DWG")
    lw.WriteLine("  跳过 > %d MB 的文件" % MAX_PRT_SIZE_MB)
    lw.WriteLine("========================================")
    lw.WriteLine("目录: " + folder)

    if not os.path.exists(folder):
        lw.WriteLine("错误: 找不到目录!")
        lw.Close()
        return

    dwgFolder = os.path.join(folder, "DWG")
    if not os.path.exists(dwgFolder):
        os.makedirs(dwgFolder)

    prtFiles = [f for f in os.listdir(folder) if f.lower().endswith(".prt")]

    if len(prtFiles) == 0:
        lw.WriteLine("未找到 .prt 文件!")
        lw.Close()
        return

    lw.WriteLine("找到 %d 个 PRT 文件" % len(prtFiles))
    lw.WriteLine("导出到: " + dwgFolder)
    lw.WriteLine("")

    settingsFile = "C:\\Program Files\\Siemens\\NX 12.0\\dxfdwg\\dxfdwg.def"

    successCount = 0
    failCount = 0
    skipCount = 0
    skipFiles = []

    for prtFile in prtFiles:
        prtPath = os.path.join(folder, prtFile)
        baseName = os.path.splitext(prtFile)[0]

        lw.WriteLine("--- " + prtFile + " ---")

        # ── 检查 PRT 文件大小 ──
        prtSize = os.path.getsize(prtPath)
        prtMB = prtSize / 1024.0 / 1024.0

        if prtMB > MAX_PRT_SIZE_MB:
            lw.WriteLine("  跳过: %.1f MB > %d MB (需手动导出)" % (prtMB, MAX_PRT_SIZE_MB))
            skipCount += 1
            skipFiles.append(prtFile)
            lw.WriteLine("")
            continue

        try:
            # 打开 PRT
            lw.WriteLine("  1/4 打开 PRT ...")

            basePart1 = theSession.Parts.OpenBaseDisplay(prtPath)

            if basePart1 is None:
                lw.WriteLine("  错误: 无法打开!")
                failCount += 1
                continue

            workPart = theSession.Parts.Work
            lw.WriteLine("     完成: " + workPart.Name)

            # 切换到制图模式
            lw.WriteLine("  2/4 切换制图模式 ...")

            try:
                theSession.ApplicationSwitchImmediate("UG_APP_DRAFTING")
                workPart.Drafting.EnterDraftingApplication()
                lw.WriteLine("     完成: 制图模式")
            except Exception as exDraft:
                lw.WriteLine("     警告: " + str(exDraft))

            # 获取图纸
            lw.WriteLine("  3/4 查找图纸 ...")

            sheetList = []
            for ds in workPart.DrawingSheets:
                sheetList.append(ds)
                lw.WriteLine("     图纸: " + ds.Name)

            lw.WriteLine("     共 %d 张" % len(sheetList))

            if len(sheetList) == 0:
                lw.WriteLine("  无图纸 - 跳过")
                workPart.Close(1, 1, None)
                failCount += 1
                continue

            # 导出 DWG
            lw.WriteLine("  4/4 导出 DWG ...")

            sheetOkCount = 0
            for idx, sheet in enumerate(sheetList):
                sheetName = sheet.Name
                safeName = sheetName.replace("/", "-").replace("\\", "-") \
                                    .replace(":", "-").replace("*", "-") \
                                    .replace("?", "-")

                if len(sheetList) == 1:
                    sheetDwgPath = os.path.join(dwgFolder, baseName + ".dwg")
                else:
                    sheetDwgPath = os.path.join(dwgFolder, baseName + "_" + safeName + ".dwg")

                lw.WriteLine("     [%d/%d] 图纸: %s" % (idx + 1, len(sheetList), sheetName))

                ok = exportDwg(theSession, workPart, sheet, sheetDwgPath, settingsFile, lw)

                if ok:
                    fileSize = os.path.getsize(sheetDwgPath)
                    sizeMB = fileSize / 1024.0 / 1024.0
                    lw.WriteLine("       成功: %.1f MB" % sizeMB)
                    sheetOkCount += 1
                else:
                    lw.WriteLine("       失败!")

            if sheetOkCount > 0:
                successCount += 1
                lw.WriteLine("  导出完成 %d/%d 张图纸" % (sheetOkCount, len(sheetList)))
            else:
                failCount += 1

            workPart.Close(1, 1, None)

            # ── 清理日志文件 ──
            cleanupLogs(dwgFolder, baseName)

            lw.WriteLine("  完成: " + prtFile)
            lw.WriteLine("")

        except Exception as ex:
            lw.WriteLine("  错误: " + str(ex))
            failCount += 1
            lw.WriteLine("")

    # ── 清理所有日志 ──
    cleanupAllLogs(dwgFolder)

    lw.WriteLine("========================================")
    lw.WriteLine("  结果:")
    lw.WriteLine("  成功: %d / %d" % (successCount, successCount + failCount))
    lw.WriteLine("  失败: %d" % failCount)
    if skipCount > 0:
        lw.WriteLine("  跳过 (> %d MB): %d" % (MAX_PRT_SIZE_MB, skipCount))
        for sf in skipFiles:
            lw.WriteLine("    - " + sf)
    lw.WriteLine("========================================")
    lw.Close()


def exportDwg(theSession, workPart, sheet, outputPath, settingsFile, lw):
    """导出1张图纸为DWG。成功返回True。"""
    try:
        markId = theSession.SetUndoMark(
            NXOpen.Session.MarkVisibility.Visible,
            "导出 DWG " + sheet.Name)

        dxfdwgCreator = theSession.DexManager.CreateDxfdwgCreator()
        dxfdwgCreator.InputFile = workPart.FullPath
        dxfdwgCreator.OutputFile = outputPath
        dxfdwgCreator.ExportData = NXOpen.DxfdwgCreator.ExportDataOption.Drawing
        dxfdwgCreator.OutputFileType = NXOpen.DxfdwgCreator.OutputFileTypeOption.Dwg
        dxfdwgCreator.AutoCADRevision = NXOpen.DxfdwgCreator.AutoCADRevisionOptions.R2004
        dxfdwgCreator.SettingsFile = settingsFile
        dxfdwgCreator.ViewEditMode = True
        dxfdwgCreator.FlattenAssembly = False
        dxfdwgCreator.ExportScaleValue = "1:1"
        dxfdwgCreator.LayerMask = "1-256"
        dxfdwgCreator.WidthFactorMode = NXOpen.DxfdwgCreator.WidthfactorMethodOptions.AutomaticCalculation

        dxfdwgCreator.Commit()
        dxfdwgCreator.Destroy()

        theSession.DeleteUndoMark(markId, None)
        return os.path.exists(outputPath)

    except Exception as ex:
        lw.WriteLine("       错误: " + str(ex))
        return False


def cleanupLogs(dwgFolder, baseName):
    """清理与baseName相关的日志文件。"""
    for f in os.listdir(dwgFolder):
        if f.lower().endswith(".log") and baseName in f:
            try:
                os.remove(os.path.join(dwgFolder, f))
            except:
                pass


def cleanupAllLogs(dwgFolder):
    """清理DWG目录中所有日志文件。"""
    for f in os.listdir(dwgFolder):
        if f.lower().endswith(".log"):
            try:
                os.remove(os.path.join(dwgFolder, f))
            except:
                pass


main()
