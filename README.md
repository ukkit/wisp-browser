<h1>
  <img src="rebrand/icon/wisp.png" alt="Wisp logo" width="96" height="96" align="left">&nbsp;&nbsp;
  WISP
</h1>

Wisp is a privacy-hardened browser built for personal use — a config overlay on [LibreWolf](https://librewolf.net/), packaged as a self-contained Windows installer.

No engine work, no recompile. Wisp takes the official LibreWolf binary, layers on additional hardening and Wisp branding, and wraps it in an installer.

Latest release: [v2026.0627](https://github.com/ukkit/wisp-browser/releases/tag/v2026.0627) — built on LibreWolf 152.0-1.

## What it does

- **DNS-level content blocking** via DNS-over-HTTPS to [Mullvad's base resolver](https://mullvad.net/en/help/dns-over-https-and-dns-over-tls) (ads, trackers, malware). Change it in `Settings → Privacy & Security → DNS over HTTPS`.
- Fingerprinting resistance and HTTPS-only mode are locked on.
- Telemetry, Firefox Studies, and Pocket are disabled.
- **4 extensions pre-installed:** [uBlock Origin](https://ublockorigin.com/), [SponsorBlock](https://sponsor.ajay.app/), [Bitwarden](https://bitwarden.com/), [Clear Cache](https://addons.mozilla.org/en-US/firefox/addon/clearcache/). No other extension installation is permitted.

## Known limits

- No per-site exceptions UI.
- Some sites may break due to the extension-install block.
- Installer is **unsigned** — SmartScreen will warn on first run. Click **More info → Run anyway**. Each release includes a `.sha256` checksum for manual verification.
- No auto-updates. Security releases are rebuilt within 72 hours of upstream.

## Building from source

See [`docs/BUILD.md`](docs/BUILD.md).

## License

MPL-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
