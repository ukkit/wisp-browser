"""Build Wisp and publish it to GitHub after double confirmation."""
import argparse
import configparser
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

REPO = "ukkit/wisp-browser"
REPO_ROOT = Path(__file__).parent.resolve()


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("librewolf_dir", help="path to the LibreWolf app folder")
    p.add_argument(
        "--version",
        default=datetime.date.today().strftime("%Y.%m%d"),
        help="Wisp version string (default: today as YYYY.mmdd)",
    )
    p.add_argument("--output-dir", default=str(REPO_ROOT / "dist"))
    p.add_argument("--iscc", default=None, help="override path to ISCC.exe")
    p.add_argument("--rcedit", default=None, help="override path to rcedit-x64.exe")
    return p.parse_args()


def check_gh():
    if not shutil.which("gh"):
        sys.exit("error: 'gh' (GitHub CLI) not found — install from https://cli.github.com/")
    result = subprocess.run(["gh", "auth", "status"], capture_output=True)
    if result.returncode != 0:
        sys.exit("error: gh is not authenticated — run 'gh auth login' first")


def check_no_existing_release(version):
    result = subprocess.run(
        ["gh", "release", "view", f"v{version}", "--repo", REPO],
        capture_output=True,
    )
    if result.returncode == 0:
        sys.exit(
            f"error: release v{version} already exists on GitHub.\n"
            f"       Delete it first or pass a different --version."
        )


def run_build(args):
    cmd = [sys.executable, str(REPO_ROOT / "build.py"), args.librewolf_dir,
           "--version", args.version,
           "--output-dir", args.output_dir]
    if args.iscc:
        cmd += ["--iscc", args.iscc]
    if args.rcedit:
        cmd += ["--rcedit", args.rcedit]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(f"Build failed (exit {result.returncode}).")
    output_dir = Path(args.output_dir).resolve()
    exe = output_dir / f"Wisp-Setup-{args.version}.exe"
    sha256_file = exe.with_suffix(exe.suffix + ".sha256")
    if not exe.exists() or not sha256_file.exists():
        sys.exit(f"error: expected outputs not found after build:\n  {exe}\n  {sha256_file}")
    return exe, sha256_file


def get_librewolf_version(librewolf_dir):
    app_dir = Path(librewolf_dir).resolve()
    if not (app_dir / "application.ini").exists():
        nested = app_dir / "LibreWolf" / "application.ini"
        if nested.exists():
            app_dir = app_dir / "LibreWolf"
    cfg = configparser.ConfigParser()
    cfg.read(app_dir / "application.ini")
    return cfg.get("App", "Version", fallback="unknown")


def confirm_and_publish(version, exe, sha256_file, lw_version):
    size_mb = exe.stat().st_size / 1024 / 1024
    sha256 = sha256_file.read_text(encoding="utf-8").split()[0]
    print(f"\n{'=' * 62}")
    print(f"  Ready to publish")
    print(f"  Version : Wisp {version}  (built on LibreWolf {lw_version})")
    print(f"  File    : {exe.name}  ({size_mb:.1f} MB)")
    print(f"  SHA-256 : {sha256}")
    print(f"  Target  : github.com/{REPO}/releases/tag/v{version}")
    print(f"{'=' * 62}\n")

    answer = input(f"Push v{version} to GitHub as a public release? [y/N] ").strip().lower()
    if answer != "y":
        print("Aborted.")
        sys.exit(1)

    confirm = input(f"Type the version to confirm ({version}): ").strip()
    if confirm != version:
        print(f"Confirmation failed — expected '{version}', got '{confirm}'. Aborted.")
        sys.exit(1)

    print(f"\nPublishing v{version} to {REPO}...")
    result = subprocess.run(
        [
            "gh", "release", "create", f"v{version}",
            str(exe), str(sha256_file),
            "--repo", REPO,
            "--title", f"Wisp {version}",
            "--notes", f"Built on LibreWolf {lw_version}.",
        ]
    )
    if result.returncode != 0:
        sys.exit(f"error: gh release create failed (exit {result.returncode}).")
    print(f"\nDone. https://github.com/{REPO}/releases/tag/v{version}")


if __name__ == "__main__":
    args = parse_args()
    check_gh()
    check_no_existing_release(args.version)
    exe, sha256_file = run_build(args)
    lw_version = get_librewolf_version(args.librewolf_dir)
    confirm_and_publish(args.version, exe, sha256_file, lw_version)
