// Wisp unlocked defaults — user-editable, unlike the lockPref() additions in librewolf.cfg.append.
//
// Mirrors the DNSOverHTTPS policy's ProviderURL (distribution/policies.json) as the default-branch
// value, so the Settings UI shows the right provider selected even before policy enforcement applies,
// while staying changeable (pi-hole/dns0 users can swap it in Settings).
pref("network.trr.uri", "https://base.dns.mullvad.net/dns-query");
