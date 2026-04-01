# -*- coding: utf-8 -*-
"""
dnx - Minimal cross-platform DNS changer.

dnx is a command-line tool for changing DNS servers on Linux, macOS, and Windows.
It provides a simple interface for viewing, setting, and resetting DNS configuration
with support for popular DNS presets (Google, Cloudflare, Quad9, OpenDNS, AdGuard).

Example usage:
    >>> import dnx
    >>> backend = dnx.get_backend()
    >>> backend.get_dns()
    ['192.168.1.1']
    >>> backend.set_dns(['8.8.8.8', '8.8.4.4'])
"""

from .params import DNX_VERSION, DNS_PRESETS
from .exceptions import (
    DNXError,
    AdminRequiredError,
    InterfaceNotFoundError,
    InvalidIPError,
    UnsupportedPlatformError,
    CommandFailedError,
    DNSOperationError,
    ServiceNotFoundError,
    BackendNotAvailableError,
)
from .dns import (
    Platform,
    get_backend,
    get_platform,
    validate_ips,
    require_admin,
    DNSBackend,
    ResolvConfDNS,
    SystemdResolvedDNS,
    NetworkManagerDNS,
    MacOSDNS,
    WindowsDNS,
)
from .ping import (
    PingResult,
    ping_server,
    ping_servers,
    verify_servers,
    format_ping_result,
    format_ping_results,
)

__version__ = DNX_VERSION

__all__ = [
    "__version__",
    "DNX_VERSION",
    "DNS_PRESETS",
    "Platform",
    "DNXError",
    "AdminRequiredError",
    "InterfaceNotFoundError",
    "InvalidIPError",
    "UnsupportedPlatformError",
    "CommandFailedError",
    "DNSOperationError",
    "ServiceNotFoundError",
    "BackendNotAvailableError",
    "get_backend",
    "get_platform",
    "validate_ips",
    "require_admin",
    "DNSBackend",
    "ResolvConfDNS",
    "SystemdResolvedDNS",
    "NetworkManagerDNS",
    "MacOSDNS",
    "WindowsDNS",
    "PingResult",
    "ping_server",
    "ping_servers",
    "verify_servers",
    "format_ping_result",
    "format_ping_results",
]
