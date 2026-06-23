#define MyAppName "VPS 3x-ui Oneclick"
#define MyAppVersion GetEnv("VPS_3XUI_APP_VERSION")
#if MyAppVersion == ""
#define MyAppVersion "0.0.0"
#endif
#define MyAppPublisher "vps-3xui-oneclick-ui"
#define MyAppExeName "VPS 3x-ui Oneclick.exe"
#define MyAppSourceDir "..\\dist\\VPS 3x-ui Oneclick"

[Setup]
AppId={{D1C61F7F-8A38-4A46-A6F4-9F3A0501C001}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=VPS-3x-ui-Oneclick-Windows-Setup-{#MyAppVersion}-unsigned
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
