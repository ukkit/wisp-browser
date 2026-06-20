# Wisp v2 — macOS port design

Companion to `wisp-v1-build-plan.md`. v2 ports Wisp's privacy-hardened LibreWolf overlay to macOS (Apple Silicon), reusing v1's tooling and decisions wherever the platform doesn't force a divergence.

## Decisions locked for v2

- **Target:** Apple Silicon (arm64) only — covers all Macs sold since late 2020. No Intel (x86_64) build; no universal binary.
- **Base:** LibreWolf's macOS arm64 build, same threat model as v1 (ad-tech, mass profiling, cross-site trackers).
- **Distribution / Gatekeeper:** Unsigned, no Apple Developer ID, no notarization — same trust trade-off v1 made for Windows/SmartScreen. This is a *worse* default experience than SmartScreen: an unsigned, unnotarized `.app` is blocked outright by Gatekeeper, not just warned. README must clearly document the override (right-click → Open on older macOS, or the Privacy & Security settings override on current macOS).
- **Packaging:** `.dmg` with drag-to-Applications. No `.pkg` installer — `.dmg` is the idiomatic, lowest-tooling macOS distribution format and doesn't need installer scripting the way Windows did.
- **Policy/branding parity:** v1's full hardening and branding set (resistFingerprinting, DoH→Mullvad base, telemetry off, blanket extension-install block, HTTPS-only locked, always-on private browsing, 104-locale rebrand) is the v2 baseline, ported as-is to macOS's config surfaces. Open to macOS-specific additions (e.g. Apple's own diagnostics/telemetry hooks, Gatekeeper/quarantine handling beyond the basic override doc) discovered during Phase 0 research — not a requirement to find something, just not foreclosed.
  - **Extension policy stays blocked, unchanged from v1, with no partial-allow option even if reconsidered later:** Firefox/Gecko's `ExtensionSettings` policy supports allow/block by extension ID or update-URL pattern, but has no field for "allow up to N extensions of any ID." A numeric cap isn't expressible via policy; only an enumerated allowlist or a custom bundled component could do it, both out of scope for a config-overlay project.
- **Build pipeline:** Extend the existing `build.py` with a macOS path, branching only at the points that actually diverge by platform (`hdiutil`/dmg creation vs `ISCC.exe`, Info.plist/bundle editing vs PE resource editing via `rcedit`) while sharing version computation, checksum writing, and the omni.ja rebrand logic unchanged — `rebrand_strings.py` operates on omni.ja's OS-agnostic zip/string format and needs no platform branch.
- **Dev/test environment:** A physical Mac is available, so v2 keeps the same local iterate-build-test loop v1 used on Windows — no CI/cloud-Mac dependency for development.
- **Default-browser registration:** Scoped in from the start (Launch Services registration with the correct launch arguments), rather than discovered late the way v1's Task 9/10 found the missing Windows registry keys. This is a proactive carry-forward of that lesson, not a new open question.
- **dmg background:** A new, dmg-sized background image (~660×400) will be generated reusing Wisp's existing brand constants (the `#29286A`/`#4F46E5`/`#A5F3FC` palette, the wisp icon mark, Segoe-UI-equivalent wordmark treatment from `export_social_preview.py`), with blank space left for Finder's app-icon and Applications-folder-arrow placement. Not a reuse of the existing `social-preview.png` as-is — that asset is the wrong aspect ratio (1280×640 widescreen) and has its wordmark/icon composited exactly where Finder needs to place its own icons.
- **Versioning/release:** Same independent `YYYY.mmdd` versioning as v1. Separate artifact naming per platform (e.g. `Wisp-<version>-macOS-arm64.dmg` + matching `.sha256`). Same manual tag/release process. The 72-hour security-rebuild commitment extends to cover macOS LibreWolf releases too, not just Windows.

## Phase structure

- **Phase 0 — Setup & research:** Download LibreWolf's macOS arm64 build. Map its config surfaces — confirm `distribution/policies.json`, the autoconfig `.cfg`, and `defaults/pref/*.js` exist in the same form inside the `.app` bundle (expected, since these are Gecko-level mechanisms, but unverified for this specific build). Research macOS-specific hardening surfaces (the "open to additions" item above). Locate the bundle's equivalent of `application.ini`/profile-identity for the Wisp-specific-profile requirement. Baseline cold-start timing on the physical Mac, same reboot+3-run-average protocol as v1's Task 1.
- **Phase 1 — Hardening overlay:** Port `policies.json` / `librewolf.cfg.append` / `wisp.js` to the `.app` bundle's actual paths. Add macOS Launch Services default-browser registration up front (see Decisions). Verify end-to-end with a v1-Task-5-style checklist, plus a Gatekeeper-override smoke check and a Launch-Services default-browser launch-argument check (mirrors v1 Task 10's profile-split check).
- **Phase 2 — Branding:** Reuse existing icon assets, re-exported as `.icns` instead of `.ico`. Rebrand `omni.ja` — expect `rebrand_strings.py` to need no changes, since omni.ja's internal format is OS-agnostic. Reconfirm the same locale spot-check approach (en-US, hi-IN, ur, plus one of de/fr) used in v1.
- **Phase 3 — Packaging:** Extend `build.py` with the dmg path (`hdiutil`). Generate the dmg background (see Decisions). Document the Gatekeeper override in place of v1's SmartScreen note.
- **Phase 4 — Ship:** Same `YYYY.mmdd` versioning, platform-specific artifact naming, same manual tag/release process, same 72-hour security-rebuild commitment extended to macOS LibreWolf releases.

## Repo layout additions

```
wisp-browser/
├── build.py                      # extended with a macOS path
├── overlay/                      # existing Windows overlay, untouched
├── overlay-macos/                # mirrors the .app bundle's own relative paths
│   ├── librewolf.cfg.append      # same append-only pattern, mac-specific path
│   ├── Contents/Resources/distribution/
│   │   └── policies.json
│   └── Contents/Resources/defaults/pref/
│       └── wisp.js
├── rebrand/
│   ├── rebrand_strings.py        # reused as-is (omni.ja is OS-agnostic)
│   └── icon/
│       ├── wisp.svg               # existing source, reused
│       └── wisp.icns              # new export target alongside wisp.ico
├── installer-macos/
│   └── dmg_background.png        # generated, reusing brand constants (see Decisions)
├── docs/
│   ├── BUILD.md                  # gets a macOS section appended
│   └── verification-checklist.md # gets macOS-specific checks appended
└── .gitignore                    # add macOS LibreWolf download pattern
```

## Verification & open research items

- **Verification:** Phase 1 gets a v1-Task-5-equivalent checklist (policy active, RFP/HTTPS-only locked, DoH live + fallback, locale spot-check, Wisp-specific profile dir), plus macOS-only additions: confirm the Gatekeeper override path works as documented on a clean account, and confirm Launch Services default-browser registration carries the right launch arguments.
- **Open research items, deliberately deferred to Phase 0 (not decided in this design):**
  - macOS-specific telemetry/diagnostics surfaces worth locking
  - exact `.app` bundle paths for policies/cfg/prefs
  - whether an `application.ini`-equivalent profile-identity mechanism exists the same way on macOS Gecko builds

## Explicitly out of scope for v2

Intel/x86_64 support, universal binary, code signing/notarization, a numeric extension-count cap (not expressible via policy — see Decisions), any policy change beyond what v1 already locked.
