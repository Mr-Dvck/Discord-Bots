' Detached Jamie launcher — survives closing the parent shell
Set sh = CreateObject("WScript.Shell")
dir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir
sh.Run """" & dir & "\venv\Scripts\python.exe"" -u main.py", 0, False
