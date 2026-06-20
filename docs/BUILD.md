# Building Wisp from source

## Prerequisites

- Windows 10/11
- Python 3.11+ (stdlib only — `build.py` and the rebrand script have no third-party dependencies)
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`ISCC.exe`, default install location is detected automatically)
- [`rcedit-x64.exe`](https://github.com/electron/rcedit/releases) — place it at the repo root (gitignored, not tracked)

## Get LibreWolf

LibreWolf fetch is manual in v1 — this repo does not download anything itself.

1. Download the **portable/zip** Windows build from [librewolf.net/installation/windows](https://librewolf.net/installation/windows/).
2. Extract it anywhere.

This repo is currently built and verified against **LibreWolf `152.0-1`** (BuildID `20260616193518`). A newer LibreWolf release may need overlay adjustments — check `wisp-v1-build-plan.md` before assuming a newer build works unmodified.

## Build

```
python build.py <path-to-LibreWolf-folder> [options]
```

`<path-to-LibreWolf-folder>` can be either the extracted portable distribution's top-level folder or its nested `LibreWolf/` app folder directly (containing `librewolf.exe`) — `build.py` detects which one it was given.

Options:

| Flag | Default | Purpose |
|---|---|---|
| `--version` | today as `YYYY.mmdd` | Wisp's own build version |
| `--output-dir` | `dist` | where the installer and checksum are written |
| `--iscc` | auto-detected | override path to `ISCC.exe` |
| `--rcedit` | `./rcedit-x64.exe` | override path to `rcedit-x64.exe` |
| `--keep-build-dir` | off | keep the intermediate build directory for debugging |

Output: `dist/Wisp-Setup-<version>.exe` and `dist/Wisp-Setup-<version>.exe.sha256` (both gitignored).

## What the pipeline does

1. Copies the LibreWolf app folder to a temp build directory, stripping portable-mode-only files (the bundled updater, scheduled-task scripts).
2. Applies Wisp's overlay: `distribution/policies.json` (full replace), `defaults/pref/wisp.js`, and appends `librewolf.cfg.append` to the existing `librewolf.cfg`.
3. Generates `browser/application.ini` (Wisp identity, real LibreWolf engine version) and `distribution/distribution.ini` (Wisp's own build version) — both per-build, not static files.
4. Rebrands `omni.ja` (strings across all locales, in-app icons).
5. Rebrands the `.exe` (icon and version-info identity strings) via `rcedit`.
6. Compiles the Inno Setup installer.
7. Writes the SHA-256 checksum.

## Verifying a release

```
Get-FileHash Wisp-Setup-<version>.exe -Algorithm SHA256
```

Compare the output against the first field of the matching `.sha256` file.

## License compliance

Wisp is MPL-2.0, built on LibreWolf/Firefox (also MPL-2.0). See [`LICENSE`](../LICENSE) and [`NOTICE`](../NOTICE) — Wisp is not affiliated with Mozilla or LibreWolf.
