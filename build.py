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

LibreWolf fetch stays manual in v1 (see wisp-v1-build-plan.md Decisions) —
this script does not download anything itself.
"""
import argparse
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
OVERLAY_FILES = [
    "distribution/policies.json",
    "defaults/pref/wisp.js",
    "browser/application.ini",
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
        "download it (see wisp-v1-build-plan.md Task 1) or pass --rcedit"
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

    build_dir = Path(tempfile.mkdtemp(prefix="wisp-build-"))
    try:
        copy_source(app_dir, build_dir)
        apply_overlay(build_dir)
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
