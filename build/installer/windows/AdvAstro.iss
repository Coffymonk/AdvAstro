; Inno Setup script for the Advanced Astrophoto Analyzer Windows installer.
;
; build/build.py compiles this automatically on Windows when Inno Setup 6 is installed
; (free: https://jrsoftware.org/isinfo.php, or  winget install JRSoftware.InnoSetup).
; It passes these values on the command line:
;   AppVersion      display version, e.g. 0.1.0.dev0
;   NumericVersion  four-part version for Windows, e.g. 0.1.0.0
;   AppDir          the PyInstaller folder of the desktop app
;   CliExe          the command-line tool (optional)
;   RootDir         the repository folder
;   OutputDir       where Setup.exe is written
;   OutputName      file name of Setup.exe without .exe

#define AppName "Advanced Astrophoto Analyzer"
#define AppExe "Advanced Astrophoto Analyzer.exe"
#define Publisher "Miklosoft"

[Setup]
; The AppId identifies the program for upgrades and uninstall. Never change it.
AppId={{6F2C8B1E-4A7D-4C39-9E2B-5D1A3F8C7B42}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
VersionInfoVersion={#NumericVersion}
VersionInfoProductName={#AppName}
VersionInfoCompany={#Publisher}
VersionInfoCopyright=Copyright (C) 2026 Miklosoft. GNU GPL v3.0.
AppPublisher={#Publisher}
AppPublisherURL=https://miklosoft.se/main
AppSupportURL=https://github.com/Coffymonk/AdvAstro/issues
AppUpdatesURL=https://github.com/Coffymonk/AdvAstro/releases
AppCopyright=Copyright (C) 2026 Miklosoft
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile={#RootDir}\LICENSE
SetupIconFile={#RootDir}\build\icons\advastro.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir={#OutputDir}
OutputBaseFilename={#OutputName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
; Install for all users (asks for administrator rights) or just for me.
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ChangesEnvironment=yes
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
#if FileExists(AddBackslash(CompilerPath) + "Languages\Swedish.isl")
  #define HaveSwedish
Name: "swedish"; MessagesFile: "compiler:Languages\Swedish.isl"
#endif

[CustomMessages]
english.AddToPath=Add the advastro command-line tool to PATH
english.CommandLine=Command line:
#ifdef HaveSwedish
swedish.AddToPath=Lägg till kommandoradsverktyget advastro i PATH
swedish.CommandLine=Kommandorad:
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
#ifdef CliExe
Name: "addtopath"; Description: "{cm:AddToPath}"; GroupDescription: "{cm:CommandLine}"; Flags: unchecked
#endif

[Files]
Source: "{#AppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#ifdef CliExe
Source: "{#CliExe}"; DestDir: "{app}\cli"; Flags: ignoreversion
#endif
Source: "{#RootDir}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#RootDir}\CREDITS.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
// The command-line tool goes on the user's own PATH (no system-wide change), and is
// taken off again when AdvAstro is uninstalled.
const
  EnvKey = 'Environment';

function CliDir(): string;
begin
  Result := ExpandConstant('{app}\cli');
end;

function PathHas(const Paths, Dir: string): Boolean;
begin
  Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Paths) + ';') > 0;
end;

procedure AddToUserPath(const Dir: string);
var
  Paths: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', Paths) then
    Paths := '';
  if PathHas(Paths, Dir) then
    exit;
  if (Paths <> '') and (Copy(Paths, Length(Paths), 1) <> ';') then
    Paths := Paths + ';';
  RegWriteExpandStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', Paths + Dir);
end;

procedure RemoveFromUserPath(const Dir: string);
var
  Paths: string;
  P: Integer;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', Paths) then
    exit;
  Paths := ';' + Paths + ';';
  P := Pos(';' + Uppercase(Dir) + ';', Uppercase(Paths));
  if P = 0 then
    exit;
  Delete(Paths, P, Length(Dir) + 1);
  Paths := Copy(Paths, 2, Length(Paths) - 2);
  RegWriteExpandStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', Paths);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('addtopath') then
    AddToUserPath(CliDir());
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RemoveFromUserPath(CliDir());
end;
