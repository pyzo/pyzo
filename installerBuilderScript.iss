; Inno setup file to create an installer for IEP

[Setup]
AppName=iep
AppId=iep
AppVerName=iep version 2.0.1
DefaultDirName={pf}\iep
DefaultGroupName=iep

SourceDir=frozen/
OutputDir=../../
OutputBaseFilename = setup_iep_2.0.1

ChangesEnvironment = no
DisableProgramGroupPage = yes
Compression=lzma
SolidCompression=yes


[Files]
Source: "*.*"; DestDir: "{app}"; Flags: recursesubdirs;
;Source: "photoshow.ico"; DestDir: "{app}";

[Tasks]
Name: icon; Description: "Desktop Icon"

[Icons]
Name: "{commondesktop}\iep"; Filename: "{app}\iep.exe"; IconFilename: "{app}\icon.ico"; Workingdir: "{app}"; Tasks: icon;





