<h1>
  <img src="rebrand/icon/wisp.png" alt="Wisp logo" width="96" height="96" align="left">&nbsp;&nbsp;
  WISP
</h1>

Wisp is a privacy-hardened config overlay on [LibreWolf](https://librewolf.net/), packaged as a self-contained Windows installer.

No engine work, no recompile — Wisp takes the official LibreWolf binary, layers on additional policy/pref hardening and Wisp branding, and wraps it in an installer.

## Status

v1 (Windows) is in development. See [`wisp-v1-build-plan.md`](wisp-v1-build-plan.md) for the build plan.

## Privacy posture

- **DNS-level content blocking**, on by default via DNS-over-HTTPS to [Mullvad's base resolver](https://mullvad.net/en/help/dns-over-https-and-dns-over-tls) (ad, tracker, and malware blocking). No in-browser ad blocker.
  - **Tradeoff:** this means Mullvad sees Wisp's DNS queries by default. Change it in `Settings → Privacy & Security → DNS over HTTPS` — point it at your own pi-hole/dns0 instance, or pick a different provider from the dropdown.
- Fingerprinting resistance (LibreWolf's `resistFingerprinting`) and HTTPS-only mode are locked on, not just defaulted.
- Telemetry, Firefox Studies, and Pocket are disabled.
- All extension/theme/dictionary installs are blocked (DNS-level blocking only — no in-browser blocker, no exceptions).

## Security updates

Wisp does not auto-update in v1. We commit to a manual rebuild-and-release **within 72 hours** of each upstream LibreWolf security release.

## Known limits (v1)

- No per-site exceptions UI.
- Some sites may break due to the blanket extension-install block.
- The installer is **unsigned** — Windows SmartScreen will warn on first run ("Windows protected your PC"). Click **More info → Run anyway** to proceed. Code signing is being evaluated for a future release (no committed date).
  - To verify the download instead of trusting the warning: each release publishes a `.sha256` checksum file alongside the installer. Verify with `Get-FileHash Wisp-Setup-<version>.exe -Algorithm SHA256` and compare against the first field of the matching `.sha256` file.

## Building from source

See [`docs/BUILD.md`](docs/BUILD.md).

## License

MPL-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
