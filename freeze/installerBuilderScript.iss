; Inno setup file to create a windows installer for Pyzo

[Setup]
AppName = pyzo
AppId = pyzo
AppVerName = pyzo version X.Y.Z
AppPublisher = The Pyzo team
AppPublisherURL = https://pyzo.org

ArchitecturesInstallIn64BitMode = x64
DefaultDirName = {pf}\pyzo
DefaultGroupName = pyzo

SourceDir = ../frozen/pyzo
OutputDir = ..
OutputBaseFilename = pyzo-X.Y.Z-win64

WizardImageBackColor=$d28b26
WizardImageStretch=no
WizardImageFile=source\pyzo\resources\appicons\pyzologo128.bmp
WizardSmallImageFile=source\pyzo\resources\appicons\pyzologo48.bmp

; When set to none, Setup will only run with administrative privileges if it
; was started by a member of the Administrators group.
; On pre vista: will *not* run with administrative privileges
PrivilegesRequired = none

; If True, Setup will refresh env/associations in explorer after install
ChangesEnvironment = no
ChangesAssociations = yes

DisableProgramGroupPage = yes
AllowNoIcons = yes
Compression = lzma
SolidCompression = yes

[Files]
Source: "*.*"; DestDir: "{app}"; Flags: recursesubdirs;

[Tasks]
Name: icon; Description: "Desktop Icon"
Name: startmenu; Description: "Create shortcut in start menu"
Name: mypAssociation; Description: "Associate "".py"" extension (need admin privileges)"

[Icons]
Name: "{commondesktop}\pyzo"; Filename: "{app}\pyzo.exe"; IconFilename: "{app}\pyzo.exe"; Workingdir: "{app}"; Tasks: icon;
Name: "{group}\Pyzo"; Filename: "{app}\pyzo.exe"; Tasks: startmenu;

[Registry]
Root: HKCR; Subkey: ".py"; ValueType: string; ValueName: ""; ValueData: "PYZO_python"; Flags: uninsdeletevalue; Tasks: mypAssociation

Root: HKCR; Subkey: "PYZO_python"; ValueType: string; ValueName: ""; ValueData: "Interactive Editor for Python"; Flags: uninsdeletekey;  Tasks: mypAssociation
Root: HKCR; Subkey: "PYZO_python\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\source\pyzo\resources\appicons\py.ico";  Tasks: mypAssociation
Root: HKCR; Subkey: "PYZO_python\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\pyzo.exe"" ""%1""";  Tasks: mypAssociation

