; Inno setup file to create a windows installer for IEP

[Setup]
AppName=iep
AppId=iep
AppVerName=iep version 2.3
DefaultDirName={pf}\iep
DefaultGroupName=iep

SourceDir=../frozen/
OutputDir=../
OutputBaseFilename = iep-2.3.win32

ChangesEnvironment = no
DisableProgramGroupPage = no
Compression=lzma
SolidCompression=yes


[Files]
Source: "*.*"; DestDir: "{app}"; Flags: recursesubdirs;

[Tasks]
Name: icon; Description: "Desktop Icon"

[Icons]
Name: "{commondesktop}\iep"; Filename: "{app}\iep.exe"; IconFilename: "{app}\iep.exe"; Workingdir: "{app}"; Tasks: icon;





