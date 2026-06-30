import sys
import os

theSession = NXOpen.Session.GetSession()
lw = theSession.ListingWindow
lw.Open()

lw.WriteLine("=== ARGS TEST ===")
lw.WriteLine("sys.argv count: " + str(len(sys.argv)))
for i, arg in enumerate(sys.argv):
    lw.WriteLine("  argv[" + str(i) + "] = " + repr(arg))
lw.WriteLine("cwd: " + os.getcwd())
lw.Close()
