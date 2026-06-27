"""Build Wisp and publish it to GitHub after double confirmation."""
import argparse
import configparser
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
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


def get_librewolf_info(librewolf_dir):
    app_dir = Path(librewolf_dir).resolve()
    if not (app_dir / "application.ini").exists():
        nested = app_dir / "LibreWolf" / "application.ini"
        if nested.exists():
            app_dir = app_dir / "LibreWolf"
    cfg = configparser.ConfigParser()
    cfg.read(app_dir / "application.ini")
    return {
        "version": cfg.get("App", "Version", fallback="unknown"),
        "build_id": cfg.get("App", "BuildID", fallback="unknown"),
    }


def edit_release_notes(version, lw_version):
    """Pre-fill release notes with git log since last tag, open editor, return result."""
    last_tag = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if last_tag.returncode == 0:
        since = last_tag.stdout.strip()
        log = subprocess.run(
            ["git", "log", f"{since}..HEAD", "--oneline"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        ).stdout.strip()
    else:
        log = subprocess.run(
            ["git", "log", "--oneline", "-20"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        ).stdout.strip()

    draft = (
        f"Built on LibreWolf {lw_version}.\n\n"
        f"## Changes\n\n"
        f"{log}\n"
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(draft)
        tmp = f.name

    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "notepad"
    subprocess.run([editor, tmp])

    notes = Path(tmp).read_text(encoding="utf-8").strip()
    Path(tmp).unlink(missing_ok=True)
    return notes


def update_docs(version, lw_info):
    """Update the pinned version references in README.md and docs/BUILD.md."""
    release_url = f"https://github.com/{REPO}/releases/tag/v{version}"

    readme = REPO_ROOT / "README.md"
    content = readme.read_text(encoding="utf-8")
    content = re.sub(
        r"(?:v1 \(Windows\) is in development[^\n]*|Latest release:[^\n]*)",
        f"Latest release: [v{version}]({release_url}) — built on LibreWolf {lw_info['version']}.",
        content,
    )
    readme.write_text(content, encoding="utf-8")

    build_md = REPO_ROOT / "docs" / "BUILD.md"
    content = build_md.read_text(encoding="utf-8")
    content = re.sub(
        r"This repo is currently built and verified against \*\*LibreWolf `[^`]+`\*\* \(BuildID `[^`]+`\)\.",
        f"This repo is currently built and verified against **LibreWolf `{lw_info['version']}`** (BuildID `{lw_info['build_id']}`).",
        content,
    )
    build_md.write_text(content, encoding="utf-8")


def commit_docs(version):
    """Commit README.md and docs/BUILD.md if they changed."""
    changed = subprocess.run(
        ["git", "diff", "--quiet", "README.md", "docs/BUILD.md"],
        cwd=REPO_ROOT,
    ).returncode != 0
    if not changed:
        return
    subprocess.run(
        ["git", "add", "README.md", "docs/BUILD.md"],
        cwd=REPO_ROOT, check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", f"Update docs for Wisp {version} release"],
        cwd=REPO_ROOT, check=True,
    )


def confirm_and_publish(version, exe, sha256_file, lw_version, notes):
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
            "--notes", notes,
        ]
    )
    if result.returncode != 0:
        sys.exit(f"error: gh release create failed (exit {result.returncode}).")
    print(f"\nDone. https://github.com/{REPO}/releases/tag/v{version}")


if __name__ == "__main__":
    args = parse_args()
    check_gh()
    check_no_existing_release(args.version)
    lw_info = get_librewolf_info(args.librewolf_dir)
    notes = edit_release_notes(args.version, lw_info["version"])
    exe, sha256_file = run_build(args)
    confirm_and_publish(args.version, exe, sha256_file, lw_info["version"], notes)
    update_docs(args.version, lw_info)
    commit_docs(args.version)
