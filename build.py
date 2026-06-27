"""Wisp's build pipeline orchestrator (Task 9).

Takes a local LibreWolf install and produces a Wisp-branded, hardened,
installable Setup.exe in one pass: copy the install tree -> apply the
overlay (policies/cfg/prefs/app-identity) -> rebrand omni.ja (strings +
icons) -> swap the .exe icon -> compile the Inno Setup installer -> write
its SHA-256 checksum.

Usage:
    .venv/Scripts/python.exe build.py <path-to-LibreWolf-app-dir> [options]

<path-to-LibreWolf-app-dir> is the actual application folder (contains
librewolf.exe, application.ini, distribution/, etc) — i.e. the "LibreWolf"
subfolder inside the downloaded portable distribution, not the top-level
portable-mode folder. If pointed at the top-level folder by mistake, this
script auto-detects and descends into the nested LibreWolf/ subfolder.

LibreWolf fetch is manual — this script does not download anything itself.
"""
import argparse
import configparser
import datetime
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.resolve()
OVERLAY_DIR = REPO_ROOT / "overlay"
REBRAND_DIR = REPO_ROOT / "rebrand"
ICON_DIR = REBRAND_DIR / "icon"
INSTALLER_SCRIPT = REPO_ROOT / "installer" / "wisp.iss"

# Explicit allowlist, not a blind directory walk — overlay/ also contains
# build_policies.py (a one-off rebase helper, not an install-tree file) and
# may grow more tooling later. librewolf.cfg.append is handled separately
# below since it's appended into librewolf.cfg, not copied as its own file.
# browser/application.ini is NOT in this list — it's generated dynamically
# by write_application_ini() instead of copied statically, since its Version
# field needs to be Wisp's own per-build version, not a fixed copy.
OVERLAY_FILES = [
    "distribution/policies.json",
    "defaults/pref/wisp.js",
    "distribution/extensions/uBlock0@raymondhill.net.xpi",
    "distribution/extensions/sponsorBlocker@ajay.app.xpi",
    "distribution/extensions/{446900e4-71c2-419f-a6a7-df9c091e268b}.xpi",
    "distribution/extensions/clearcache@michel.de.almeida.xpi",
]
CFG_APPEND = OVERLAY_DIR / "librewolf.cfg.append"

# Portable-mode tooling that must never end up in the shipped build (see
# Decisions: shipping the updater would undermine "no auto-update in v1").
# Defensive — normally absent already, since callers should point this
# script at the LibreWolf/ app subfolder, not the portable distribution's
# top-level folder, but checked either way.
PORTABLE_MODE_FILES = [
    "LibreWolf-Portable.exe",
    "LibreWolf-WinUpdater.exe",
    "ScheduledTask-Create.ps1",
    "ScheduledTask-Remove.ps1",
]

DEFAULT_ISCC_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
]


def find_app_dir(given):
    """Accept either the LibreWolf app dir itself or its portable-distribution
    parent folder, and resolve to the actual app dir either way."""
    given = Path(given).resolve()
    if (given / "librewolf.exe").exists():
        return given
    nested = given / "LibreWolf"
    if (nested / "librewolf.exe").exists():
        return nested
    sys.exit(
        f"error: no librewolf.exe found at {given} or {nested} — "
        "pass the path to LibreWolf's actual app folder (or its portable-"
        "distribution parent folder)"
    )


def find_iscc(override):
    if override:
        path = Path(override)
        if not path.exists():
            sys.exit(f"error: --iscc path does not exist: {path}")
        return path
    for candidate in DEFAULT_ISCC_CANDIDATES:
        if candidate.exists():
            return candidate
    sys.exit(
        "error: ISCC.exe not found in the usual Inno Setup install locations — "
        "pass --iscc explicitly"
    )


def find_rcedit(override):
    if override:
        path = Path(override)
        if not path.exists():
            sys.exit(f"error: --rcedit path does not exist: {path}")
        return path
    default = REPO_ROOT / "rcedit-x64.exe"
    if default.exists():
        return default
    sys.exit(
        f"error: rcedit-x64.exe not found at {default} — "
        "download it from https://github.com/electron/rcedit/releases or pass --rcedit"
    )


def copy_source(app_dir, build_dir):
    print(f"copying {app_dir} -> {build_dir}")
    shutil.copytree(app_dir, build_dir, dirs_exist_ok=True)
    removed = []
    for name in PORTABLE_MODE_FILES:
        path = build_dir / name
        if path.exists():
            path.unlink()
            removed.append(name)
    if removed:
        print(f"removed portable-mode files that shouldn't ship: {removed}")


def apply_overlay(build_dir):
    print("applying overlay")
    for rel_path in OVERLAY_FILES:
        src = OVERLAY_DIR / rel_path
        dst = build_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  {rel_path}")

    cfg_path = build_dir / "librewolf.cfg"
    with open(cfg_path, "a", encoding="utf-8") as f:
        f.write(CFG_APPEND.read_text(encoding="utf-8"))
    print("  librewolf.cfg.append -> librewolf.cfg (appended)")


def read_librewolf_app_info(app_dir):
    """Reads the source build's own top-level application.ini (the unused
    stub LibreWolf ships — see Task 4) for the fields that must track the
    actual LibreWolf build being packaged: Version, BuildID, SourceRepository,
    SourceStamp, ID, and Gecko Min/MaxVersion. Read dynamically rather than
    hardcoded, so a future LibreWolf rebase doesn't leave these stale in a
    static overlay file the way browser/application.ini used to be.
    """
    parser = configparser.ConfigParser()
    parser.read(app_dir / "application.ini", encoding="utf-8")
    return {
        "version": parser["App"]["Version"],
        "build_id": parser["App"]["BuildID"],
        "source_repository": parser["App"]["SourceRepository"],
        "source_stamp": parser["App"]["SourceStamp"],
        "id": parser["App"]["ID"],
        "gecko_min_version": parser["Gecko"]["MinVersion"],
        "gecko_max_version": parser["Gecko"]["MaxVersion"],
    }


def write_application_ini(build_dir, librewolf_info):
    """Generates browser/application.ini (the one Gecko actually loads, via
    -app "browser\\application.ini" — see Task 4) with Wisp's own identity,
    but the *actual* LibreWolf engine version — not Wisp's own build version.

    Tried setting this to Wisp's own version first; reverted after discovering
    the About dialog's displayed version doesn't even read this field at
    runtime — it reads AppConstants.MOZ_APP_VERSION_DISPLAY, a constant
    compiled into LibreWolf's own build, which this overlay-only project
    cannot change without recompiling (out of scope per the project's "no
    engine work" constraint). Setting Version here to anything other than the
    real engine version would just risk a mismatch against that compiled
    constant for zero visible benefit. Wisp's own build version is shown via
    distribution.ini instead (see write_distribution_ini), which *is* read at
    runtime via Services.prefs.
    """
    print(f"writing browser/application.ini (LibreWolf version {librewolf_info['version']})")
    ini_path = build_dir / "browser" / "application.ini"
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    ini_path.write_text(
        "[App]\n"
        "Vendor=Wisp\n"
        "Name=Wisp\n"
        "RemotingName=wisp\n"
        f"Version={librewolf_info['version']}\n"
        "Profile=Wisp\n"
        f"BuildID={librewolf_info['build_id']}\n"
        f"SourceRepository={librewolf_info['source_repository']}\n"
        f"SourceStamp={librewolf_info['source_stamp']}\n"
        f"ID={librewolf_info['id']}\n"
        "\n"
        "[Gecko]\n"
        f"MinVersion={librewolf_info['gecko_min_version']}\n"
        f"MaxVersion={librewolf_info['gecko_max_version']}\n"
        "\n"
        "[XRE]\n"
        "EnableProfileMigrator=1\n",
        encoding="utf-8",
    )


def write_distribution_ini(build_dir, wisp_version):
    """distribution/distribution.ini doesn't exist upstream — adding it (not
    overwriting anything) is the only runtime-readable place left to surface
    Wisp's own build version in the About dialog, since application.ini's
    Version field can't be repurposed for this (see write_application_ini) —
    the dialog's main version line is a compiled constant, but its
    #distributionId label reads distribution.id/.version via Services.prefs
    at runtime, which this file does populate.

    Format is INI, not JSON — confirmed by reading modules/distribution.sys.mjs
    inside omni.ja. That module's applyPrefDefaults() requires id, version,
    AND about to all be present under [Global] — if any one is missing, the
    whole customization step bails out before setting distribution.id at all
    (verified by reading the actual shipped logic, not just guessing from the
    omitted-key idea tried first). So id and version must be separate keys
    rather than baking "Wisp v<version>" into id alone. aboutDialog.js then
    renders distributionId as "<id> - <version>", and the about text as a
    second, always-shown line.
    """
    print(f"writing distribution.ini (Wisp v{wisp_version})")
    ini_path = build_dir / "distribution" / "distribution.ini"
    ini_path.write_text(
        "[Global]\n"
        "id=Wisp\n"
        f"version={wisp_version}\n"
        "about=Wisp, a privacy-hardened browser built on LibreWolf\n",
        encoding="utf-8",
    )


def run_rebrand(build_dir):
    print("rebranding omni.ja")
    sys.path.insert(0, str(REBRAND_DIR))
    import rebrand_strings

    omni_path = build_dir / "browser" / "omni.ja"
    tmp_path = omni_path.with_suffix(".ja.tmp")
    report, unexpected = rebrand_strings.rebrand_zip(omni_path, tmp_path)
    tmp_path.replace(omni_path)

    print(f"  files patched: {report['files_patched']}")
    print(f"  substitutions: {report['substitutions']}")
    print(f"  icons replaced: {report['icons_replaced']}")
    print(f"  aboutDialog.css icon: {report['css_icon_replaced']}")
    print(f"  aboutDialog website link: {report['website_link_replaced']}")
    print(f"  newtab background injected: {report['newtab_bg_injected']}")
    if unexpected:
        sys.exit("error: rebrand found unexpected results:\n  " + "\n  ".join(unexpected))


def rebrand_exe(build_dir, rcedit_path):
    print("rebranding .exe (icon + version-info identity strings)")
    exe_path = build_dir / "librewolf.exe"
    # FileDescription/ProductName/InternalName are what Windows surfaces in
    # the taskbar right-click context menu, separate from both the icon
    # resource and application.ini's Name — found still showing "LibreWolf"
    # there during Task 9 testing despite everything else being rebranded.
    # CompanyName/LegalCopyright/LegalTrademarks deliberately left as
    # Mozilla's own — accurate attribution of the underlying engine, matching
    # NOTICE's MPL-2.0 stance, not something Wisp claims as its own.
    subprocess.run(
        [
            str(rcedit_path),
            str(exe_path),
            "--set-icon", str(ICON_DIR / "wisp.ico"),
            "--set-version-string", "FileDescription", "Wisp",
            "--set-version-string", "ProductName", "Wisp",
            "--set-version-string", "InternalName", "Wisp",
        ],
        check=True,
    )

    # Standalone install-root .ico, separate from the .exe's own embedded
    # icon — flagged in Task 7/8 as a stray LibreWolf-icon artifact in the
    # shipped tree. Overwritten rather than deleted, in case anything
    # references the filename directly.
    standalone_ico = build_dir / "librewolf.ico"
    if standalone_ico.exists():
        shutil.copy2(ICON_DIR / "wisp.ico", standalone_ico)
        print(f"  overwrote stray {standalone_ico.name} with Wisp's icon")


def compile_installer(build_dir, version, output_dir, iscc_path):
    print(f"compiling installer (version {version})")
    output_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(iscc_path),
            f"/DMyAppVersion={version}",
            f"/DSourceDir={build_dir}",
            f"/DOutputDir={output_dir}",
            str(INSTALLER_SCRIPT),
        ],
        check=True,
    )
    return output_dir / f"Wisp-Setup-{version}.exe"


def write_checksum(setup_exe):
    print("computing SHA-256 checksum")
    digest = hashlib.sha256(setup_exe.read_bytes()).hexdigest()
    checksum_path = setup_exe.with_suffix(setup_exe.suffix + ".sha256")
    # standard sha256sum format: "<hash>  <filename>" (two spaces), so it
    # verifies with `sha256sum -c` cross-platform as well as a manual
    # Get-FileHash comparison on Windows (see README).
    checksum_path.write_text(f"{digest}  {setup_exe.name}\n", encoding="utf-8")
    print(f"  {checksum_path}")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("librewolf_dir", help="path to the LibreWolf app folder")
    parser.add_argument(
        "--version",
        default=datetime.date.today().strftime("%Y.%m%d"),
        help="Wisp version string (default: today as YYYY.mmdd)",
    )
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "dist"))
    parser.add_argument("--iscc", default=None, help="override path to ISCC.exe")
    parser.add_argument("--rcedit", default=None, help="override path to rcedit-x64.exe")
    parser.add_argument(
        "--keep-build-dir",
        action="store_true",
        help="don't delete the intermediate build directory afterward",
    )
    args = parser.parse_args()

    app_dir = find_app_dir(args.librewolf_dir)
    iscc_path = find_iscc(args.iscc)
    rcedit_path = find_rcedit(args.rcedit)
    output_dir = Path(args.output_dir).resolve()

    librewolf_info = read_librewolf_app_info(app_dir)

    build_dir = Path(tempfile.mkdtemp(prefix="wisp-build-"))
    try:
        copy_source(app_dir, build_dir)
        apply_overlay(build_dir)
        write_application_ini(build_dir, librewolf_info)
        write_distribution_ini(build_dir, args.version)
        run_rebrand(build_dir)
        rebrand_exe(build_dir, rcedit_path)
        setup_exe = compile_installer(build_dir, args.version, output_dir, iscc_path)
        digest = write_checksum(setup_exe)
    finally:
        if args.keep_build_dir:
            print(f"build dir kept at {build_dir}")
        else:
            shutil.rmtree(build_dir, ignore_errors=True)

    print(f"\ndone: {setup_exe}")
    print(f"sha256: {digest}")


if __name__ == "__main__":
    main()
