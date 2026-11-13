#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef PortableDir
  #define PortableDir "dist\SDTrimSP-2D_GUI"
#endif
#ifndef OutputDirPath
  #define OutputDirPath "dist"
#endif
#ifndef ChineseMessages
  #define ChineseMessages "assets\installer\ChineseSimplified.isl"
#endif
[Setup]
AppId={{1B9C27E5-591F-4C79-87A6-902E61C673CC}
AppName=SDTrimSP-2D GUI
AppVersion={#AppVersion}
AppPublisher=Muxc99
AppPublisherURL=https://github.com/Muxc99/SDTrimSP-2D-GUI
DefaultDirName={localappdata}\Programs\SDTrimSP-2D_GUI
DefaultGroupName=SDTrimSP-2D GUI
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDirPath}
OutputBaseFilename=SDTrimSP-2D-GUI-{#AppVersion}-Windows-Setup
SetupIconFile=assets\SDTrimSP-2D_GUI.ico
UninstallDisplayIcon={app}\SDTrimSP-2D_GUI.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=no
RestartApplications=no
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "{#ChineseMessages}"
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
[Files]
Source: "{#PortableDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\SDTrimSP-2D GUI"; Filename: "{app}\SDTrimSP-2D_GUI.exe"
Name: "{autodesktop}\SDTrimSP-2D GUI"; Filename: "{app}\SDTrimSP-2D_GUI.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\SDTrimSP-2D_GUI.exe"; Description: "{cm:LaunchProgram,SDTrimSP-2D GUI}"; Flags: nowait postinstall skipifsilent
