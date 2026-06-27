# Release Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single `release.py` script at the repo root that builds the Wisp installer then, after two manual confirmations, publishes it as a GitHub release.

**Architecture:** `release.py` derives the output paths from the same version logic as `build.py`, runs `build.py` as a subprocess (streaming output live), then handles the confirmation + publish step itself. No capture/parsing of build output — paths are constructed directly.

**Tech Stack:** Python 3.11+ stdlib only (`argparse`, `subprocess`, `configparser`, `hashlib`, `shutil`, `datetime`, `pathlib`). GitHub CLI (`gh`) for release creation.

## Global Constraints

- No external Python dependencies — stdlib only
- `gh` CLI must already be authenticated; script errors out if not found
- Repo target: `ukkit/wisp-browser`
- Release tag format: `v{YYYY}.{MMDD}` (e.g. `v2026.0626`) — matches existing releases
- No attribution lines in commit messages; imperative mood
- Script lives at repo root: `release.py`

---

### Task 1: Write `release.py`

**Files:**
- Create: `release.py`

**Interfaces:**
- Consumes: `build.py` (invoked as subprocess), `gh` CLI
- Produces: a GitHub release at `ukkit/wisp-browser` with two assets: `Wisp-Setup-{version}.exe` and `Wisp-Setup-{version}.exe.sha256`

- [ ] **Step 1: Create `release.py` with arg parsing mirroring `build.py`**

  All args are passed through to `build.py`. `--version` defaults to today's date, same as `build.py`.

  ```python
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


  if __name__ == "__main__":
      args = parse_args()
  ```

- [ ] **Step 2: Add `gh` availability check**

  Before the build even starts, fail fast if `gh` is missing or unauthenticated.

  ```python
  def check_gh():
      if not shutil.which("gh"):
          sys.exit("error: 'gh' (GitHub CLI) not found — install from https://cli.github.com/")
      result = subprocess.run(["gh", "auth", "status"], capture_output=True)
      if result.returncode != 0:
          sys.exit("error: gh is not authenticated — run 'gh auth login' first")
  ```

  Call it at the top of `__main__`:
  ```python
  if __name__ == "__main__":
      args = parse_args()
      check_gh()
  ```

- [ ] **Step 3: Add pre-build duplicate-release guard**

  Check if the tag already exists on GitHub before running a 3-minute build.

  ```python
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
  ```

  Call after `check_gh()`:
  ```python
      check_no_existing_release(args.version)
  ```

- [ ] **Step 4: Add the build step**

  Derive expected output paths from args (same logic as `build.py`), run the build, verify outputs exist.

  ```python
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
  ```

  Call in `__main__`:
  ```python
      exe, sha256_file = run_build(args)
  ```

- [ ] **Step 5: Add LibreWolf version lookup for release notes**

  Read the LibreWolf version from the source `application.ini` to include it in the release notes. The app dir may be the portable parent or the nested `LibreWolf/` subfolder — handle both the same way `build.py` does.

  ```python
  def get_librewolf_version(librewolf_dir):
      app_dir = Path(librewolf_dir).resolve()
      if not (app_dir / "application.ini").exists():
          nested = app_dir / "LibreWolf" / "application.ini"
          if nested.exists():
              app_dir = app_dir / "LibreWolf"
      cfg = configparser.ConfigParser()
      cfg.read(app_dir / "application.ini")
      return cfg.get("App", "Version", fallback="unknown")
  ```

  Call before the confirmation prompt:
  ```python
      lw_version = get_librewolf_version(args.librewolf_dir)
  ```

- [ ] **Step 6: Add the confirmation prompt (two gates)**

  Show a summary, then ask twice before pushing.

  ```python
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
          sys.exit(0)

      confirm = input(f"Type the version to confirm ({version}): ").strip()
      if confirm != version:
          print(f"Confirmation failed — expected '{version}', got '{confirm}'. Aborted.")
          sys.exit(1)

      print(f"\nPublishing v{version} to {REPO}...")
      subprocess.run(
          [
              "gh", "release", "create", f"v{version}",
              str(exe), str(sha256_file),
              "--repo", REPO,
              "--title", f"Wisp {version}",
              "--notes", f"Built on LibreWolf {lw_version}.",
          ],
          check=True,
      )
      print(f"\nDone. https://github.com/{REPO}/releases/tag/v{version}")
  ```

  Call in `__main__`:
  ```python
      confirm_and_publish(args.version, exe, sha256_file, lw_version)
  ```

- [ ] **Step 7: Assemble the final file and verify it runs**

  The complete `release.py` should read (top to bottom): docstring, imports, constants, `parse_args()`, `check_gh()`, `check_no_existing_release()`, `run_build()`, `get_librewolf_version()`, `confirm_and_publish()`, `if __name__ == "__main__"` block.

  Smoke-test it without a LibreWolf dir to confirm arg parsing works:
  ```
  python release.py --help
  ```
  Expected output: shows `librewolf_dir`, `--version`, `--output-dir`, `--iscc`, `--rcedit` in the help text with no traceback.

- [ ] **Step 8: Commit**

  ```bash
  git add release.py
  git commit -m "Add release.py — build + double-confirmed GitHub publish"
  ```

---

## Verification

1. Run `python release.py --help` — confirm all args shown
2. Run `python release.py librewolf-152.0-1` — watch build complete, then see the confirmation summary with correct version/size/sha256
3. At first prompt type `n` — confirm it aborts cleanly
4. Re-run, type `y` at first prompt, type a wrong version at second — confirm it aborts with "Confirmation failed"
5. Re-run, type `y` then correct version — confirm the release appears at `github.com/ukkit/wisp-browser/releases`
