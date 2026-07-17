; Inno Setup script for Omni Verte.
;
; Build (from the repo root, with Inno Setup 6 installed):
;   ISCC /DAppVersion=0.1.7 installer\OmniVerte.iss
; Output:
;   dist\installer\OmniVerte-Setup-<version>.exe
;
; The PyInstaller onedir build (dist\OmniVerte\) must exist first —
; run `pyinstaller OmniVerte.spec` or scripts\build.ps1.

; AppVersion is normally passed with /DAppVersion=... by the build script / CI
; (source of truth is the VERSION file). Fall back to a placeholder for ad-hoc
; manual compiles.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "Omni Verte"
#define AppPublisher "Arsenii Bandurin"
#define AppExeName "OmniVerte.exe"
#define AppUrl "https://github.com/OmniNeurons/OmniVerte"

[Setup]
; Stable AppId — DO NOT change between releases (drives upgrade-in-place and
; uninstall). Generated once for this app.
AppId={{A7F3C2E1-9B4D-4E6A-8C12-2F5D7B9E4A30}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
VersionInfoVersion={#AppVersion}

; Per-user install — no admin / UAC prompt. With PrivilegesRequired=lowest,
; {autopf} resolves to {localappdata}\Programs.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

LicenseFile=..\LICENSE
SetupIconFile=..\favicon.ico
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
OutputDir=..\dist\installer
OutputBaseFilename=OmniVerte-Setup-{#AppVersion}
; The app is x64-only (faster-whisper / ctranslate2 / PySide6).
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start Omni Verte automatically when I sign in"; GroupDescription: "Startup:"

[Files]
; The whole PyInstaller onedir output (exe + _internal/ with all DLLs and datas).
Source: "..\dist\OmniVerte\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Per-user autostart (HKCU Run). Removed automatically on uninstall.
; The in-app "Launch on Windows startup" toggle manages this same value at
; runtime — keep ValueName "OmniVerte" in sync with
; services/autostart.py::VALUE_NAME, or the two will create competing entries.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "OmniVerte"; ValueData: """{app}\{#AppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

; Note: user config in %APPDATA%\OmniVerte and secrets in Windows
; Credential Manager are intentionally left in place on uninstall — they are
; user-owned data, not part of the installed program.
