"""One-off helper to derive Wisp's policies.json from the upstream LibreWolf
copy without hand-retyping the embedded base64 search-engine icons.
Not part of the build.py pipeline — run manually, then delete or keep as a
reference for future rebases against a new upstream policies.json.
"""
import json
import sys

src = sys.argv[1] if len(sys.argv) > 1 else "../../librewolf-152.0-1/LibreWolf/distribution/policies.json"
dst = sys.argv[2] if len(sys.argv) > 2 else "policies.json"

with open(src, encoding="utf-8") as f:
    data = json.load(f)

p = data["policies"]

p["DisableProfileImport"] = True
p["DisableSetDesktopBackground"] = True

p["ExtensionSettings"] = {
    "*": {
        "blocked_install_message": "Wisp blocks all add-on installs by design — content blocking is handled at the DNS level, not in-browser.",
        "installation_mode": "blocked"
    }
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

with open(dst, "w", encoding="utf-8", newline="\n") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
    f.write("\n")

print(f"wrote {dst}")
