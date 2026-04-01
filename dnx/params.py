# -*- coding: utf-8 -*-
"""dnx parameters and constants."""

DNX_VERSION = "0.1"

DNS_PRESETS = {
    "google": ["8.8.8.8", "8.8.4.4"],
    "cloudflare": ["1.1.1.1", "1.0.0.1"],
    "quad9": ["9.9.9.9", "149.112.112.112"],
    "opendns": ["208.67.222.222", "208.67.220.220"],
    "adguard": ["94.140.14.14", "94.140.15.15"],
}

LINUX_RESOLV_CONF = "/etc/resolv.conf"

DEFAULT_PING_COUNT = 3
DEFAULT_PING_TIMEOUT = 5
