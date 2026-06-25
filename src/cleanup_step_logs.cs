using System;
using System.IO;
using System.Threading;
using NXOpen;

public class CleanupStepLogs
{
    static bool DeleteWithRetry(string path, ListingWindow lw,
                                int maxAttempts = 10, int baseDelayMs = 500)
    {
        for (int i = 1; i <= maxAttempts; i++)
        {
            if (!File.Exists(path)) return true;

            try
            {
                File.Delete(path);
                return true;
            }
            catch (Exception ex)
            {
                lw.WriteLine("  [retry " + i + "/" + maxAttempts + "] " + Path.GetFileName(path) + ": " + ex.Message);
            }

            if (i < maxAttempts)
                Thread.Sleep(baseDelayMs * (int)Math.Pow(2, i - 1));
        }
        return false;
    }

    public static void Main(string[] args)
    {
        Session theSession = Session.GetSession();
        ListingWindow lw = theSession.ListingWindow;
        lw.Open();

        string folder = (args.Length > 0 && !string.IsNullOrEmpty(args[0]))
                        ? args[0] : Directory.GetCurrentDirectory();

        lw.WriteLine("--- Don dep file log ---");

        // Wait for NX to release handles
        Thread.Sleep(8000);

        int deleted = 0;

        // Cleanup STEP folder
        string stepFolder = Path.Combine(folder, "STEP");
        if (Directory.Exists(stepFolder))
        {
            foreach (string f in Directory.GetFiles(stepFolder, "*.log"))
            {
                if (DeleteWithRetry(f, lw))
                {
                    lw.WriteLine("  Da xoa: " + Path.GetFileName(f));
                    deleted++;
                }
            }
        }

        // Cleanup DWG folder
        string dwgFolder = Path.Combine(folder, "DWG");
        if (Directory.Exists(dwgFolder))
        {
            foreach (string f in Directory.GetFiles(dwgFolder, "*.log"))
            {
                if (DeleteWithRetry(f, lw))
                {
                    lw.WriteLine("  Da xoa: " + Path.GetFileName(f));
                    deleted++;
                }
            }
        }

        // Cleanup PDF folder
        string pdfFolder = Path.Combine(folder, "PDF");
        if (Directory.Exists(pdfFolder))
        {
            foreach (string f in Directory.GetFiles(pdfFolder, "*.log"))
            {
                if (DeleteWithRetry(f, lw))
                {
                    lw.WriteLine("  Da xoa: " + Path.GetFileName(f));
                    deleted++;
                }
            }
        }

        lw.WriteLine("  Tong da xoa: " + deleted + " file log.");
        lw.Close();
    }

    public static int GetUnloadOption(string dummy)
    {
        return (int)Session.LibraryUnloadOption.Immediately;
    }
}
