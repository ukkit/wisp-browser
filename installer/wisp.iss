; Wisp installer script.
;
; Version, the branded/overlaid build directory to package, and the output
; directory are all passed in as preprocessor defines from build.py (Task 9):
;   ISCC.exe /DMyAppVersion=2026.0618 /DSourceDir=C:\path\to\branded-build ^
;            /DOutputDir=C:\CODE\git\wisp\dist installer\wisp.iss
; The #ifndef defaults below exist only so this script can be compiled
; standalone for manual testing (Task 8) without build.py.

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif
#ifndef SourceDir
  #define SourceDir "..\test-build"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif

#define MyAppName "Wisp"
#define MyAppPublisher "Wisp Project"
#define MyAppExeName "librewolf.exe"

[Setup]
; Fixed AppId (GUID) so future versions are recognized as upgrades, not
; separate installs, even though MyAppVersion changes every rebuild.
AppId={{B6E6E6C0-6E6E-4B0F-9C9A-77B6F1B6E6C0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Per-user install: no admin/UAC elevation, avoids stacking a UAC prompt on
; top of the unsigned-binary SmartScreen warning (see Decisions).
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=Wisp-Setup-{#MyAppVersion}
SetupIconFile=..\rebrand\icon\wisp.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Unsigned for v1 — SmartScreen warning is documented in README, not suppressed here.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; Flat recursive copy of the branded+overlaid build dir build.py assembled —
; the one exception is librewolf.cfg.append, which build.py appends into
; librewolf.cfg itself before this step runs, not copied as a separate file.
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
; Both shortcuts must launch via -app "browser\application.ini", not the bare
; exe — required for Wisp's app-identity/profile-separation override (Task 4)
; to actually take effect.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "-app ""browser\application.ini"""; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "-app ""browser\application.ini"""; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "-app ""browser\application.ini"""; WorkingDir: "{app}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// Inno only removes the files it explicitly installed via [Files]; the
// profile directory is created at runtime and survives a normal uninstall
// (browser data isn't something to delete silently by default). Ask once,
// post-uninstall, whether to delete it — default answer is "Yes" (delete),
// matching the same default under /SUPPRESSMSGBOXES silent uninstalls.
// Phrased as a direct question (not "keep it? choose No to delete") after a
// manual test showed the double-negative phrasing caused a misclick.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ProfilesDir: String;
  Answer: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    ProfilesDir := ExpandConstant('{localappdata}\Wisp\Profiles');
    if DirExists(ProfilesDir) then
    begin
      Answer := MsgBox(
        'Delete your Wisp profile data (bookmarks, history, saved logins) now?' + #13#10 + #13#10 +
        'Choose Yes to permanently delete it, or No to keep it for next time you install Wisp.',
        mbConfirmation, MB_YESNO);
      if Answer = IDYES then
        DelTree(ExpandConstant('{localappdata}\Wisp'), True, True, True);
    end;
  end;
end;
