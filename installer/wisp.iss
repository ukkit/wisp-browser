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

[Registry]
; Per-user (HKCU, matching the no-admin install) Windows default-browser
; candidate registration — StartMenuInternet client + Capabilities +
; RegisteredApplications. Without this, Wisp doesn't appear in Windows'
; Default Apps page or in Wisp's own Settings > General "Make Default"
; section at all (Firefox checks for a valid shell registration before
; exposing that UI) — found missing during Task 10's clean-VM test, since
; Inno doesn't write any of this on its own the way a real browser
; installer does. Uses absolute paths (not WorkingDir-relative like the
; shortcuts) since shell\open\command has no working-directory concept.
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Wisp, a privacy-hardened browser built on LibreWolf"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities"; ValueType: string; ValueName: "ApplicationIcon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#MyAppName}"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities\FileAssociations"; ValueType: string; ValueName: ".htm"; ValueData: "WispHTML"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities\FileAssociations"; ValueType: string; ValueName: ".html"; ValueData: "WispHTML"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities\FileAssociations"; ValueType: string; ValueName: ".shtml"; ValueData: "WispHTML"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities\FileAssociations"; ValueType: string; ValueName: ".xht"; ValueData: "WispHTML"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities\FileAssociations"; ValueType: string; ValueName: ".xhtml"; ValueData: "WispHTML"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities\URLAssociations"; ValueType: string; ValueName: "ftp"; ValueData: "WispURL"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities\URLAssociations"; ValueType: string; ValueName: "http"; ValueData: "WispURL"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities\URLAssociations"; ValueType: string; ValueName: "https"; ValueData: "WispURL"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" -app ""{app}\browser\application.ini"""

Root: HKCU; Subkey: "Software\Classes\WispHTML"; ValueType: string; ValueName: ""; ValueData: "Wisp HTML Document"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\WispHTML\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\WispHTML\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" -app ""{app}\browser\application.ini"" ""%1"""

Root: HKCU; Subkey: "Software\Classes\WispURL"; ValueType: string; ValueName: ""; ValueData: "Wisp URL"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\WispURL"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\WispURL\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\WispURL\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" -app ""{app}\browser\application.ini"" ""%1"""

Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities"; Flags: uninsdeletevalue

[Code]
// If a previous Wisp install (e.g. a test install at C:\Temp\WispVerify) left
// its uninstall registry entry behind, Inno reads it at startup and treats
// that path as the upgrade target — silently updating the wrong directory.
// Delete any AppId registration that doesn't point to the canonical install
// path before Inno gets a chance to read it.
//
// Otherwise (the common case: a real previous Wisp install at the canonical
// path), Inno itself gives no indication anywhere in the wizard that this is
// an upgrade rather than a fresh install — it just silently overwrites files.
// Read the previous DisplayVersion and ask before proceeding, so upgrading
// over an existing install isn't indistinguishable from installing fresh.
// Skipped under /SILENT and /VERYSILENT — a scripted install has already
// decided to proceed, and MsgBox would either block forever or, under
// /SUPPRESSMSGBOXES, auto-answer in a way that isn't safely predictable here.
function InitializeSetup(): Boolean;
var
  UninstKey: String;
  InstallLocation: String;
  OldVersion: String;
begin
  Result := True;
  UninstKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' +
               '{B6E6E6C0-6E6E-4B0F-9C9A-77B6F1B6E6C0}_is1';
  if RegQueryStringValue(HKCU, UninstKey, 'InstallLocation', InstallLocation) then
  begin
    if CompareText(InstallLocation, ExpandConstant('{localappdata}\Wisp\')) <> 0 then
      RegDeleteKeyIncludingSubkeys(HKCU, UninstKey)
    else if not WizardSilent() then
      if RegQueryStringValue(HKCU, UninstKey, 'DisplayVersion', OldVersion) then
        if OldVersion <> '{#MyAppVersion}' then
          if MsgBox('Wisp ' + OldVersion + ' is already installed.' + #13#10 + #13#10 +
                     'Update it to version {#MyAppVersion}?',
                     mbConfirmation, MB_YESNO) = IDNO then
            Result := False;
  end;
end;

// Kill any running librewolf.exe before file extraction so in-place upgrades
// reliably overwrite all files. Without this, /SILENT suppresses Inno's
// "please close the app" dialog and locked files (xul.dll, librewolf.cfg, etc.)
// are silently skipped, leaving the old installation partially in place.
// Delete all Wisp-Wisp-* and Mozilla-LibreWolf-* entries from the startup Run
// key. The browser writes these itself (keyed by install-path hash) when "Open
// on startup" is enabled; stale entries from old or test installs accumulate
// and cause multiple browser instances on reboot. The browser re-registers the
// correct entry on first launch after this install completes.
procedure CleanStaleStartupEntries();
var
  RunKey: String;
  Names: TArrayOfString;
  I: Integer;
begin
  RunKey := 'Software\Microsoft\Windows\CurrentVersion\Run';
  if RegGetValueNames(HKCU, RunKey, Names) then
    for I := 0 to GetArrayLength(Names) - 1 do
      if (Pos('Wisp-Wisp-', Names[I]) = 1) or (Pos('Mozilla-LibreWolf-', Names[I]) = 1) then
        RegDeleteValue(HKCU, RunKey, Names[I]);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
  begin
    Exec('taskkill.exe', '/F /IM librewolf.exe', '', SW_HIDE,
         ewWaitUntilTerminated, ResultCode);
    // taskkill exits before the OS finishes releasing memory-mapped handles
    // (xul.dll, librewolf.exe). Wait 2 s so the kernel cleanup completes
    // before Inno Setup tries to overwrite those files.
    Sleep(2000);
    CleanStaleStartupEntries();
  end;
end;

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
