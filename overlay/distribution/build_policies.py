"""One-off helper to derive Wisp's policies.json from the upstream LibreWolf
copy without hand-retyping the embedded base64 search-engine icons.
Not part of the build.py pipeline — run manually, then delete or keep as a
reference for future rebases against a new upstream policies.json.

Note: upstream LibreWolf moved its own SearchEngines defaults out of
policies.json and into a bundled remote-settings dump as of 153.0.4-1.
Wisp's curated SearchEngines block (own list of engines/removals) is no
longer derivable from upstream's file — it's pulled from the previous
policies.json instead (see --prev) and still works as a Firefox Enterprise
Policy override regardless of what LibreWolf's own remote-settings ship.
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default="../../librewolf-154.0.1-3/LibreWolf/distribution/policies.json",
                     help="upstream LibreWolf's policies.json for the new version")
    ap.add_argument("--prev", default="policies.json",
                     help="Wisp's previous policies.json, source of the SearchEngines block")
    ap.add_argument("dst", nargs="?", default="policies.json")
    args = ap.parse_args()

    with open(args.src, encoding="utf-8") as f:
        data = json.load(f)
    with open(args.prev, encoding="utf-8") as f:
        prev = json.load(f)["policies"]

    p = data["policies"]

    p["DisableSetDesktopBackground"] = True
    p["DisableProfileImport"] = True
    p["DisablePocket"] = True
    p["DisableDeveloperTools"] = False
    p["DefaultSerialGuardSetting"] = 3
    p["OverrideFirstRunPage"] = ""

    p["WebsiteFilter"] = {
        "Block": ["https://localhost/*"],
        "Exceptions": ["https://localhost/*"]
    }

    p["DNSOverHTTPS"] = {
        "Enabled": True,
        "ProviderURL": "https://base.dns.mullvad.net/dns-query",
        "Locked": False,
        "Fallback": True
    }

    p["SupportMenu"] = {
        "Title": "Wisp Issue Tracker",
        "URL": "https://github.com/ukkit/wisp-browser/issues"
    }

    p["ExtensionSettings"] = {
        "*": {
            "blocked_install_message": "Wisp ships with a curated set of extensions. Additional add-on installs are not permitted.",
            "installation_mode": "blocked"
        },
        "uBlock0@raymondhill.net": {
            "installation_mode": "force_installed",
            "install_url": "https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest.xpi",
            "default_area": "navbar",
            "private_browsing": True
        },
        "sponsorBlocker@ajay.app": {
            "installation_mode": "force_installed",
            "install_url": "https://addons.mozilla.org/firefox/downloads/latest/sponsorblock/latest.xpi",
            "default_area": "navbar",
            "private_browsing": True
        },
        "{446900e4-71c2-419f-a6a7-df9c091e268b}": {
            "installation_mode": "force_installed",
            "install_url": "https://addons.mozilla.org/firefox/downloads/latest/bitwarden-password-manager/latest.xpi",
            "default_area": "navbar",
            "private_browsing": True
        },
        "clearcache@michel.de.almeida": {
            "installation_mode": "force_installed",
            "install_url": "https://addons.mozilla.org/firefox/downloads/latest/clearcache/latest.xpi",
            "default_area": "navbar",
            "private_browsing": True
        }
    }

    # Not derivable from upstream anymore (see module docstring) — carried
    # forward from Wisp's own previous policies.json instead.
    p["SearchEngines"] = prev["SearchEngines"]

    with open(args.dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")

    print(f"wrote {args.dst}")


if __name__ == "__main__":
    main()
