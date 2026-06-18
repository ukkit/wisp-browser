# Wisp — v1 build plan (Windows)

Wisp v1 is a privacy-hardened **config overlay on LibreWolf**, packaged as a self-contained Windows installer. No engine work, no recompile: you take the official LibreWolf binary, layer on Wisp's policy + prefs + branding, and wrap it in an Inno Setup installer.

Each task below is scoped to roughly one working day for someone new to this tooling, and includes a "Done when" so you know it's finished. Tasks are mostly sequential; the phase order matters.

---

## Decisions locked for v1

- **Base:** LibreWolf (Gecko), latest stable Windows release. Config overlay only.
- **Threat model:** ad-tech, mass profiling, cross-site trackers. (State-level deferred.)
- **Fingerprinting:** LibreWolf's built-in resistFingerprinting (uniformity). Randomization deferred.
- **Content blocking:** DNS-level only, via DoH. Default = **Mullvad adblock** (`https://adblock.dns.mullvad.net/dns-query`), left **user-changeable** so pi-hole/dns0 users can swap it. No in-browser blocker.
- **Locked prefs:** resistFingerprinting, telemetry off, extension installs blocked (blanket block covers all install types — extensions, dictionaries, themes, sitepermissions, not just "extension"), HTTPS-only on. Note: `resistFingerprinting` and HTTPS-only mode are **not** actually locked by upstream LibreWolf (it only `defaultPref`s them) — Wisp locks them itself via `lockPref()` appended to `librewolf.cfg`.
- **Unlocked (user-editable):** DoH provider only. Crash reporting is **not** a Wisp setting — LibreWolf removes the crash-reporter component at the build level (no `crashreporter.exe` ships) and already `lockPref()`s the related prefs off itself; there's nothing to expose.
- **Default homepage / new-tab:** stays `about:blank`, matching LibreWolf's existing minimalist default. No custom Wisp welcome/onboarding page in v1.
- **Help/support URLs:** `app.support.baseURL`, `app.feedback.baseURL`, `app.releaseNotesURL`, and the `SupportMenu` policy entry are repointed to the `wisp-browser` GitHub repo's issues page, not left pointing at LibreWolf's own site/tracker — avoids Wisp-specific bug reports landing in the wrong upstream project.
- **Branding:** name "Wisp"; mono icon (indigo circle + white wisp); palette indigo `#29286A` / `#4F46E5` + cyan `#A5F3FC`. The in-app string rebrand (Task 7) applies to **all ~100 locales** LibreWolf ships (scripted pattern-replace across every `chrome/<locale>/branding` and `localization/<locale>/branding` file in `omni.ja`), not just en-US — several are Indian-language locales (hi-IN, gu-IN, pa-IN, bn, mr, ta, te, kn, ur, sat) that should see "Wisp," not "LibreWolf," after a language switch.
- **Packaging:** self-contained Inno Setup installer, manual build, **unsigned** for v1 (SmartScreen warning documented in README + a published SHA-256 checksum per release so users can verify integrity without Authenticode; signing deferred — release notes say "evaluating for a future release," no committed date). **Install scope is per-user** (e.g. `%LocalAppData%\Wisp`), not per-machine Program Files — avoids stacking a UAC elevation prompt on top of the unsigned-binary SmartScreen warning.
- **Repo contents:** only Wisp's overlay (policies.json, cfg/pref additions, locale-rebrand script, icon assets, Inno script) is tracked in git. The downloaded LibreWolf binary/install tree is gitignored; `BUILD.md` pins the exact version and download URL instead.
- **Platforms:** Windows v1 → macOS v2 → Linux v3.
- **License:** MPL-2.0, open source. NOTICE must disclaim affiliation with both Mozilla *and* LibreWolf (confirmed: MPL-2.0 imposes no extra rebrand restriction beyond this).
- **Security update commitment:** no auto-update in v1, but Wisp commits to a manual rebuild-and-release **within 72 hours** of each upstream LibreWolf security release. State this explicitly in README as the support contract, rather than leaving update cadence implicit.
- **DoH default reverses LibreWolf's own default** (LibreWolf ships DoH off, `network.trr.mode=5`). This is intentional — DNS-level blocking via Mullvad is Wisp's core mechanism — but disclose clearly in README that this means Mullvad sees DNS queries, as an explicit tradeoff.

### Build automation & versioning (added after plan review)

- **Single pipeline script:** the whole overlay → rebrand → icon → package flow is driven by one Python script (`build.py`), not a manual checklist. Python chosen (over PowerShell) specifically because it's the language v2 (macOS) and v3 (Linux) builds will reuse for their own orchestration.
- **LibreWolf fetch stays manual in v1** — a human downloads/extracts the LibreWolf build and passes its folder path into `build.py`; the script does not fetch it. Scripted auto-fetch is deferred to v2, once the manual flow has proven reliable (avoids silently trusting a bad download/redirect during a 72-hour security-rebuild crunch).
- **Repo layout:**
  ```
  wisp-browser/
  ├── build.py                      # pipeline orchestrator
  ├── overlay/
  │   ├── policies.json             # full replace of distribution/policies.json
  │   ├── librewolf.cfg.append      # lockPref() lines appended to LibreWolf's cfg
  │   └── wisp.js                   # defaults/pref/wisp.js (unlocked defaults)
  ├── rebrand/
  │   ├── rebrand_strings.py        # omni.ja LibreWolf→Wisp pattern-replace (104 locales)
  │   └── icon/
  │       ├── wisp.svg              # source mark
  │       └── wisp.ico              # exported multi-res
  ├── installer/
  │   └── wisp.iss                  # Inno Setup template (version passed as ISCC define)
  ├── docs/
  │   ├── BUILD.md
  │   └── verification-checklist.md # Task 5 checklist, kept current
  ├── README.md
  ├── NOTICE
  ├── LICENSE
  └── .gitignore                    # librewolf-*/, dist/
  ```
  `build.py` takes the local LibreWolf folder path as a CLI arg and emits `dist/Wisp-Setup-<version>.exe` + `dist/Wisp-Setup-<version>.exe.sha256` (both gitignored, plain-overwrite on re-run — no same-day build counter).
- **Versioning is independent of LibreWolf's version**: `YYYY.mmdd` (build date, e.g. `2026.0618`), not LibreWolf-mirrored semver. Chosen over a month+sequence-counter scheme (`YYYY.mm.N`) because the date is always unique and needs no manually-tracked counter state across releases.
- **"Built on LibreWolf `<version>`" is surfaced via `about:support`'s existing non-localized version-display field** (app name/version sourced from `application.ini`/buildconfig), not a new "About Wisp" dialog. This avoids adding any new string to the already-risky 104-locale Task 7 rebrand pattern-replace — it's a one-time config value change, not translated UI.
- **Checksum format:** standard `sha256sum`-style (`<hash>  <filename>` in a `.sha256` file), matching cross-platform convention even though v1's README instructions are Windows-specific (`Get-FileHash -Algorithm SHA256`, compare against the file's first field).
- **Packaging tool stays Inno Setup** — confirmed after review; no Windows-alternative (NSIS, WiX, pynsist, SFX) actually buys cross-platform reuse for v2/v3, which need fundamentally different ecosystems (`.pkg`/notarization, AppImage/deb/rpm) regardless.
- **Publishing the GitHub release stays a manual, human-judgment step in v1** (tag, release notes, upload) even though the build itself is fully scripted — release notes need a human glance (routine CVE patch vs. something else) before going public. Scripted `gh release create` end-to-end is deferred to v2.
- **Icon artwork:** drafted directly as hand-written SVG (circle + wisp glyph), iterated visually, then exported to the `.ico` layer set by a small Python script (cairosvg/Pillow) — no external design tool/handoff.

---

## Phase 0 — Setup & learning

**Task 1 — Project scaffold + dev environment**
- GitHub repo `wisp-browser` already exists at `github.com/ukkit/wisp-browser` (currently just `LICENSE`, MPL-2.0). Add `README.md` skeleton, `NOTICE` crediting LibreWolf and Mozilla, `.gitignore` (pattern `librewolf-*/` — excludes the downloaded LibreWolf binary/install tree; only Wisp's overlay files are tracked in git; see Decisions).
- Install: VS Code, Inno Setup, 7-Zip, **Python** (for the Task 7 rebrand script), **`rcedit`** (CLI exe-icon swap, used in Task 7/8 instead of Resource Hacker), **VirtualBox** (Task 10 clean-VM test — this dev machine is Windows Home, no Hyper-V support). Download the latest LibreWolf stable Windows build from the official download page (`librewolf.net/installation/windows/`, currently linking to portable/zip builds) — the portable/zip is easiest to work with. **Record the exact version/build number downloaded** — this is what `BUILD.md` will pin against later (Task 11), since "latest stable" drifts and isn't reproducible on its own.
- **Source of truth for new releases:** LibreWolf's actual release history lives on Codeberg (a Forgejo/Gitea instance, *not* GitHub/GitLab) at `codeberg.org/librewolf/bsys6/releases`, releasing roughly weekly. Track new releases via its RSS feed — `codeberg.org/librewolf/bsys6/releases.rss` — or by "Watch"-ing the repo on Codeberg; this is what should trigger the 72-hour security-rebuild clock when a release looks security-relevant. The same repo also exposes a JSON releases API (`codeberg.org/api/v1/repos/librewolf/bsys6/releases`), which is the natural data source to reuse for v2's scripted auto-fetch (polling and downloading off the same endpoint, not two separate mechanisms).
- Note: the downloaded artifact is LibreWolf's *portable* distribution. Only the `LibreWolf\` subfolder is the actual application that gets overlaid and packaged — the top-level portable-mode files (`LibreWolf-Portable.exe`, `LibreWolf-WinUpdater.exe`, `ScheduledTask-Create.ps1`, `ScheduledTask-Remove.ps1`) are not part of the shipped Wisp build (see Task 9).
- Measure stock LibreWolf's cold-start time on this machine now, before any overlay changes — this is the baseline the Task 10 perf target gets compared against. Methodology: reboot the machine/VM, launch to interactive window, repeat 3x, average — use the **same protocol** in Task 10 so the comparison is apples-to-apples.
- *Done when:* repo is up, all tools installed, LibreWolf launches locally, version number and baseline cold-start time (reboot + 3-run average) are noted.

**Task 2 — Map the config surfaces (research day)**
- Learn the three levers: `distribution/policies.json` (enterprise policy — what's lockable), the autoconfig `.cfg` mechanism (`lockPref` vs `defaultPref`), and `defaults/pref/*.js` (user-overridable defaults).
- Note: LibreWolf already ships its own `librewolf.cfg` autoconfig and locks most hardening. **Don't replace it — extend it.** Wisp's locked additions append to that file; Wisp's unlocked defaults go in a separate `defaults/pref/wisp.js`.
- *Done when:* you can list exactly which Wisp setting goes via policy vs autoconfig vs default-pref, and you've located each file inside the install folder.

## Phase 1 — The hardening overlay

**Task 3 — Write `distribution/policies.json`**
- This is a **full replace** of LibreWolf's existing `distribution/policies.json`, not a merge. Confirmed against the actual LibreWolf 152.0-1 build: upstream's `SearchEngines` block (DuckDuckGo Lite default, Google/Bing/Amazon/eBay/Twitter/Perplexity removed, DuckDuckGo Lite/Searx/MetaGer/Startpage/Mojeek added) is exactly the privacy-respecting config Wisp wants — **carry it forward verbatim** into Wisp's policy file rather than dropping it or rewriting it from scratch.
- Block all installs of every type (`ExtensionSettings: {"*": {installation_mode: "blocked"}}`, no `allowed_types` carve-out for dictionaries/themes) — block everything rather than allowlisting LibreWolf's own system extension IDs, **including dropping upstream's `uBlock0@raymondhill.net` install allowance** (Wisp's content-blocking model is DNS-level only; no in-browser blocker, no exceptions). If Task 5 testing finds this breaks a built-in feature, the fallback is a narrow allowlist for that specific extension ID (documented inline), not a relaxation of the blanket policy. Verify no built-in feature breaks in Task 5 rather than pre-emptively scoping the policy. **Decision authority: any breakage found always triggers a stop-and-ask, never a pre-authorized auto-allowlist** — loosening the "block everything" stance is a security-policy tradeoff, not a routine engineering call, so it needs explicit sign-off every time it comes up, even during a 72-hour rebuild crunch. Also set `DisableTelemetry`, `DisableFirefoxStudies`, disable Pocket, set HTTPS-only (note: HTTPS-only has no dedicated policy field — see Task 4 for how it's actually locked).
- **Explicitly include `DisableAppUpdate: true` and `AppUpdateURL: "https://localhost"`** — easy to lose in a full replace, but critical: without it the bundled `LibreWolf-WinUpdater.exe`-style auto-update mechanism could silently overwrite Wisp's branding/hardening, contradicting the "no auto-update in v1" commitment.
- Set `DNSOverHTTPS`: `Enabled: true`, `ProviderURL` = Mullvad adblock, `Locked: false`, **`Fallback: true`** (this policy field, available since Firefox 124, falls back to system DNS if the DoH provider fails — this is what fixes captive-portal/hotel-WiFi login pages, not a manual `network.trr.mode` tweak). This policy is the **sole** mechanism for default-DoH-on; don't also touch `librewolf.cfg`'s `network.trr.mode`/`network.trr.uri` defaults (leave them as upstream shipped them) to avoid two competing sources of truth.
- Set `SupportMenu` to point at the `wisp-browser` GitHub issues page, not LibreWolf's tracker.
- *Done when:* a manually-modified LibreWolf shows the Wisp policies at `about:policies`, refuses to install an extension/dictionary/theme, and the Help menu points at Wisp's own issue tracker.

**Task 4 — Write the pref overlay**
- Append Wisp's **locked** prefs to the existing `librewolf.cfg` using `lockPref()`. This is **not** just belt-and-suspenders: confirmed by reading the shipped cfg that `privacy.resistFingerprinting` and `dom.security.https_only_mode` are only `defaultPref`'d by LibreWolf, not actually locked — Wisp's `lockPref()` calls are the only thing that locks them.
- Add a "Mullvad (Adblock)" entry to `doh-rollout.provider-list` in the cfg (it currently only lists "Mullvad (No Filtering)") so the Settings UI dropdown correctly names the endpoint the `DNSOverHTTPS` policy actually sets as default.
- Override `app.support.baseURL`, `app.feedback.baseURL`, `app.releaseNotesURL`, `app.update.url.details`, `app.update.url.manual` (currently pointing at `librewolf.net`/`codeberg.org`) to point at the `wisp-browser` GitHub repo, matching the Help-menu repoint in Task 3.
- Add a `defaults/pref/wisp.js` with `pref()` for **unlocked defaults**: DoH default mirror. (Default homepage stays `about:blank`, no override needed — see Decisions.)
- Crash reporting is dropped from scope entirely (confirmed: no `crashreporter.exe` ships, and the relevant prefs are already `lockPref()`'d off by LibreWolf — see Decisions). No work needed here.
- Update `application.ini`/buildconfig app identity to "Wisp" so `about:support` shows the right name/version (carries the "Built on LibreWolf `<version>`" info — see Build automation & versioning in Decisions) — **and confirm this gives Wisp its own separate profile directory** (e.g. `%LocalAppData%\Wisp\Profiles\...`), distinct from any stock LibreWolf install on the same machine. This is a real risk, not just cosmetic: Firefox-derived browsers key their profile path off app/vendor identity, so getting this wrong could mean Wisp and a separately-installed LibreWolf silently collide on the same profile (bookmarks/history/logins). Verify in Task 5/10, not just inferred from the About page string.
- *Done when:* `about:config` shows `resistFingerprinting` and `https_only_mode` as locked, the DoH provider dropdown shows "Mullvad (Adblock)," Help/About URLs resolve to the Wisp repo, `about:support` shows "Wisp"/"Built on LibreWolf `<version>`", and a fresh launch creates a profile under a Wisp-specific directory.

**Task 5 — Verify the config end-to-end (test day)**
- Fresh-profile checklist: launches; `about:policies` active; extensions blocked (and no built-in LibreWolf feature broken by the blanket block — any breakage found is a stop-and-ask, see Task 3); DoH live (check `about:networking#dns`); RFP active (amiunique/coveryourtracks); HTTPS-only prompts on http **and** the per-page "Continue to HTTP Site" click-through still works on a plain-HTTP local address (e.g. router admin panel) despite the global setting being locked; a known ad domain is blocked by Mullvad; DoH is changeable in Settings; DoH fallback works; profile directory is Wisp-specific, not shared with LibreWolf (see Task 4); crash reporting off but toggleable (if applicable per Task 4 finding).
- **DoH fallback test method:** temporarily add a Windows Firewall rule blocking outbound HTTPS to the Mullvad DoH endpoint (`netsh advfirewall firewall add rule ...`), confirm pages still load via system-DNS fallback, then remove the rule. Preferred over a hosts-file block since it simulates the real failure mode (endpoint unreachable) without risking DNS-cache interference from Firefox's own resolver.
- **Locale rebrand verification (Task 7) is spot-checked, not exhaustive**: manually language-switch through a deliberately diverse subset (en-US, hi-IN, ur, plus one of de/fr) rather than all 104 locales, combined with the rebrand script's own automated per-file diff/match-count report (e.g. "312/312 files patched, N substitutions, 0 unexpected matches") as the primary sanity check.
- **Verification cadence for 72-hour security rebuilds (post-v1.0.0):** this full checklist runs in full once, at v1.0.0. For routine rebuilds afterward, skim the upstream LibreWolf changelog first — if it touches fingerprinting, network/DoH, or extension/policy handling, re-run the specific affected checklist item(s); otherwise a routine CVE-only patch only needs a cheap smoke check (`about:policies` shows Wisp's policy, app launches, loads a page). This keeps the 72-hour window realistic without re-testing things that didn't change.
- *Done when:* every item passes and the checklist is saved in the repo (`docs/verification-checklist.md`).

## Phase 2 — Branding

**Task 6 — Export the icon asset set**
- No existing logo/reference to start from — design the mono mark (indigo `#4F46E5` circle, white wisp) from scratch as SVG, drafted by hand (circle + stylized wisp glyph) and iterated visually rather than sourced from external design tooling. Make a **thickened** variant for the 16px layer so it stays legible.
- Export a multi-resolution `wisp.ico` (16/32/48/64/128/256) plus a PNG for the README, via a small Python script (cairosvg/Pillow) — this becomes part of `rebrand/icon/` in the `build.py` pipeline, not a one-off manual export.
- *Done when:* `wisp.ico` exists, looks right at both 16px and 256px.

**Task 7 — Rebrand the binary** *(highest-fiddliness task — give it the full day)*
- Swap the `.exe` icon with **`rcedit`** (CLI tool, not Resource Hacker — keeps the icon swap scriptable/reproducible from `BUILD.md` rather than a manual GUI step; add `rcedit` as a documented build dependency). Edit brand strings (LibreWolf → Wisp) inside `browser/omni.ja` (it's a zip). Confirmed against the actual build: 104 locales each ship `chrome/<locale>/locale/branding/brand.dtd` + `brand.properties` (208 files) and `localization/<locale>/branding/brand.ftl` (104 files) — all uniform, tiny, simple "LibreWolf"→"Wisp" string swaps. Write a **Python** script (`rebrand/rebrand_strings.py`, zipfile + re) that pattern-replaces across all 312 files in one pass, not just en-US, called from `build.py`. See Decisions for why all locales matter.
- **Concrete go/no-go gate, checked immediately after the repack (not discovered later in Task 9/10):** rebuild `omni.ja` with only the string substitution (no structural changes), relaunch, confirm clean startup with no crash and no integrity/tamper warning. Pass → keep the string rebrand. Fail → fall back to icon-only rebrand for v1 and defer the in-app string rebrand to v1.1, decided same day rather than as a late surprise. **This gate is a manual, human-confirmed step on the first build only** — `build.py` pauses and prompts to relaunch and confirm before continuing. Once validated, record a marker (e.g. a `validated-against: <libreWolf-version-or-schema>` note) so subsequent 72-hour rebuilds skip the pause automatically, re-triggering only if LibreWolf's internal `omni.ja`/locale structure actually changes.
- **Verification scope:** spot-check a diverse subset of locales (en-US, hi-IN, ur, plus de or fr) visually, plus the script's own automated per-file diff/match-count report — not an exhaustive manual sweep of all 104 (see Task 5).
- *Done when:* the patched build shows "Wisp" in the title/menus across the spot-checked locales and the Wisp icon in the taskbar, confirmed via the go/no-go relaunch test — or, if that test fails, at minimum the icon is rebranded and the fallback is noted in release notes.

## Phase 3 — Packaging

**Task 8 — Learn Inno Setup + draft installer**
- Follow Inno's "first script" tutorial. Draft a script (`installer/wisp.iss`) that installs LibreWolf files **per-user to `%LocalAppData%\Wisp`** (not Program Files — no admin/UAC elevation required, avoids stacking a UAC prompt on top of the unsigned-binary SmartScreen warning), creates "Wisp" Start Menu + desktop shortcuts with the Wisp icon, and an uninstaller. Set `AppPublisher = "Wisp Project"` (no personal name/handle tied to the binary, matching how LibreWolf itself labels its publisher). Version/output-name are passed in as `ISCC.exe` preprocessor defines from `build.py`, not hand-edited per release. Confirmed: Inno Setup stays the packaging tool (no Windows alternative buys cross-platform reuse for v2/v3 anyway — see Decisions).
- *Done when:* you can build a `Setup.exe` that installs without requiring admin rights, launches, and cleanly uninstalls.

**Task 9 — Assemble the real Wisp installer**
- `build.py` invokes `ISCC.exe` against `wisp.iss`, pointed at the **branded + overlay-applied** build dir (binary + `distribution/policies.json` + cfg/pref overlay + swapped icon + patched `omni.ja`). Package **only the contents of the `LibreWolf\` subfolder** — explicitly exclude `LibreWolf-Portable.exe`, `LibreWolf-WinUpdater.exe`, `ScheduledTask-Create.ps1`, and `ScheduledTask-Remove.ps1` from the source download, since these are portable-mode tooling and shipping the updater would undermine the "no auto-update" commitment. Set product name/publisher = Wisp; version = independent `YYYY.mmdd` build date (see Decisions), not LibreWolf's version. Output `dist/Wisp-Setup-<YYYY.mmdd>.exe` + `.sha256` (gitignored, overwritten on re-run).
- *Done when:* a from-scratch install yields a working, hardened, Wisp-branded browser, with no portable-mode wrapper files present in the installed directory.

**Task 10 — Clean-machine acceptance test**
- Install on a genuinely fresh Windows VM. **Use VirtualBox** — the dev machine is Windows Home, which does not support Hyper-V (Home edition lacks the Hyper-V optional feature entirely). Not just a secondary local account, which shares OS/registry/AV state with the dev machine and would miss issues like missing redistributables or first-run SmartScreen/Defender behavior. Re-run the Phase-1 checklist post-install (packaging can move file paths — confirm `policies.json` and the cfg land correctly, and confirm the profile directory is Wisp-specific — see Task 4). Measure cold-start against the stock-LibreWolf baseline recorded in Task 1, using the **same protocol** (reboot the VM, launch to interactive window, repeat 3x, average), treating <2s / 4GB-RAM as an aspirational stretch goal, not a gate. Verify uninstall removes everything, including the per-user `%LocalAppData%\Wisp` install directory.
- **Cadence for 72-hour security rebuilds (post-v1.0.0):** for now, this full VM test re-runs on **every** rebuild, not just packaging-affecting changes — automating/scoping this down is deferred to v3 rather than decided now.
- *Done when:* all pass on a clean VM; startup is compared against the Task 1 baseline using the identical reboot+3-run-average protocol and meets target or the gap is documented.

## Phase 4 — Ship

**Task 11 — Docs + repo finalize**
- `README.md`: what Wisp is, the privacy posture (including the explicit DoH-on-by-default tradeoff — Mullvad sees DNS queries), how to change DoH / use a pi-hole, the 72-hour security-rebuild commitment, and known limits (no per-site exceptions, some sites may break, unsigned → SmartScreen warning + how to proceed + published SHA-256 checksum for verification, in standard `sha256sum`-style format — see Decisions — verified on Windows via `Get-FileHash -Algorithm SHA256`).
- `BUILD.md`: exact steps to run `build.py` against a manually-downloaded LibreWolf build, **pinned to the specific LibreWolf version/build number** recorded in Task 1 (not just "latest stable" — note that later LibreWolf releases may require adapting the overlay steps). Confirm MPL-2.0 compliance (source offer, license notices, attribution, no LibreWolf/Mozilla marks, NOTICE disclaims affiliation with both).
- *Done when:* a stranger could rebuild Wisp's first release from your docs alone (running `build.py`), against the pinned LibreWolf version.

**Task 12 — Cut the v1 release**
- Tag the release using Wisp's own `YYYY.mmdd` version (e.g. `v2026.0618`, not `v1.0.0` — see Decisions), upload `Wisp-Setup-<YYYY.mmdd>.exe` to a GitHub Release along with its **`.sha256` checksum file**, with notes (including the unsigned/SmartScreen note, the checksum, the LibreWolf base version this build was made against, and "code signing is being evaluated for a future release" — no committed date). **This step is manual in v1** — `build.py` stops at local `dist/` artifacts; tagging, release notes, and upload are a deliberate human action, not scripted, since release notes need a judgment call (routine CVE rebuild vs. something else) before going public.
- *Done when:* the release is public and downloadable.

---

## Explicitly deferred (not v1)

Auto-update pipeline · code signing · macOS & Linux builds · fingerprint randomization · Tor / state-level adversary resistance · per-site exceptions UI · custom settings page · full rebrand of crash-reporter internals · scripted LibreWolf auto-fetch (v2) · scripted GitHub release publishing (v2) · scoping/automating the full VM acceptance test to packaging-affecting changes only (v3).

## Rough timeline

~12 working days of focused effort — call it **2.5–3 weeks part-time**, with Tasks 7 and 9 the most likely to spill.
