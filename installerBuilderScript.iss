; Inno setup file to create a windows installer for IEP

[Setup]
AppName = iep
AppId = iep
AppVerName = iep version X.Y.Z
DefaultDirName = {pf}\iep
DefaultGroupName = iep

SourceDir = frozen/
OutputDir = ../
OutputBaseFilename = iep-X.Y.Z.win32

; When set to none, Setup will only run with administrative privileges if it 
; was started by a member of the Administrators group.
; On pre vista: will *not* run with administrative privileges
PrivilegesRequired = none 

; If True, Setup will refresh env/associations in explorer after install
ChangesEnvironment = no
ChangesAssociations = yes

DisableProgramGroupPage = no
AllowNoIcons = yes
Compression = lzma
SolidCompression = yes

[Files]
Source: "*.*"; DestDir: "{app}"; Flags: recursesubdirs;

[Tasks]
Name: icon; Description: "Desktop Icon"
Name: mypAssociation; Description: "Associate "".py"" extension (need admin privileges)"

[Icons]
Name: "{commondesktop}\iep"; Filename: "{app}\iep.exe"; IconFilename: "{app}\iep.exe"; Workingdir: "{app}"; Tasks: icon;

[Registry]
Root: HKCR; Subkey: ".py"; ValueType: string; ValueName: ""; ValueData: "IEP_python"; Flags: uninsdeletevalue; Tasks: mypAssociation 

Root: HKCR; Subkey: "IEP_python"; ValueType: string; ValueName: ""; ValueData: "Interactive Editor for Python"; Flags: uninsdeletekey;  Tasks: mypAssociation 
Root: HKCR; Subkey: "IEP_python\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\source\iep\resources\appicons\py.ico";  Tasks: mypAssociation 
Root: HKCR; Subkey: "IEP_python\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\iep.exe"" ""%1""";  Tasks: mypAssociation 

