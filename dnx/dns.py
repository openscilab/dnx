# -*- coding: utf-8 -*-
"""
DNS backend implementations for dnx.

This module provides cross-platform DNS management through abstract backend
classes and platform-specific implementations for Linux, macOS, and Windows.
"""

import ipaddress
import os
import platform
import subprocess
from enum import Enum
from typing import List, Optional


class Platform(Enum):
    """
    Supported operating system platforms.

    Attributes:
        LINUX: Linux operating system.
        MACOS: macOS (Darwin) operating system.
        WINDOWS: Windows operating system.
    """

    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"

from .params import LINUX_RESOLV_CONF
from .exceptions import (
    AdminRequiredError,
    InterfaceNotFoundError,
    InvalidIPError,
    UnsupportedPlatformError,
    CommandFailedError,
    DNSOperationError,
    ServiceNotFoundError,
    BackendNotAvailableError,
)


def require_admin():
    """
    Check if running with admin/root privileges.

    Raises:
        AdminRequiredError: If not running with sufficient privileges.
    """
    if os.name != "nt":
        if os.geteuid() != 0:
            raise AdminRequiredError("Please run as root (sudo)")
    else:
        try:
            subprocess.check_call(
                ["net", "session"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            raise AdminRequiredError("Please run as Administrator")


def validate_ips(servers: List[str]):
    """
    Validate that all servers are valid IP addresses.

    Args:
        servers: List of IP address strings to validate.

    Raises:
        InvalidIPError: If any server is not a valid IP address.
    """
    for s in servers:
        try:
            ipaddress.ip_address(s)
        except ValueError:
            raise InvalidIPError(f"Invalid IP address: {s}")


def get_platform() -> Platform:
    """
    Detect the current operating system.

    Returns:
        Platform enum value for the current OS.

    Raises:
        UnsupportedPlatformError: If the OS is not supported.
    """
    system = platform.system().lower()
    if system == "linux":
        return Platform.LINUX
    if system == "darwin":
        return Platform.MACOS
    if system == "windows":
        return Platform.WINDOWS
    raise UnsupportedPlatformError(f"Unsupported operating system: {system}")


def run_command(
    args: List[str],
    check: bool = True,
    capture_output: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run a system command and return the result.

    Args:
        args: Command and arguments as a list of strings.
        check: If True, raise exception on non-zero exit code.
        capture_output: If True, capture stdout and stderr.
        text: If True, decode output as text.

    Returns:
        CompletedProcess instance with command results.

    Raises:
        CommandFailedError: If the command fails or is not found.
    """
    try:
        return subprocess.run(
            args,
            check=check,
            capture_output=capture_output,
            text=text,
        )
    except subprocess.CalledProcessError as e:
        raise CommandFailedError(f"Command failed: {' '.join(args)}\n{e.stderr or e}")
    except FileNotFoundError:
        raise CommandFailedError(f"Command not found: {args[0]}")


class DNSBackend:
    """
    Abstract base class for DNS backends.

    Provides the interface for platform-specific DNS management implementations.
    Subclasses must implement get_active_interface(), get_dns(), set_dns(),
    and reset_dns() methods.

    Attributes:
        iface: Optional network interface override.
    """

    def __init__(self, iface: Optional[str] = None):
        """
        Initialize the DNS backend.

        Args:
            iface: Optional network interface name to use instead of auto-detection.
        """
        self.iface = iface

    def get_active_interface(self) -> str:
        """
        Get the active network interface.

        Returns:
            Name of the active network interface.

        Raises:
            InterfaceNotFoundError: If no active interface can be detected.
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError

    def get_interface(self) -> str:
        """
        Get the interface to use (user-specified or auto-detected).

        Returns:
            Network interface name.
        """
        if self.iface:
            return self.iface
        return self.get_active_interface()

    def get_dns(self) -> List[str]:
        """
        Get current DNS servers.

        Returns:
            List of DNS server IP addresses.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError

    def set_dns(self, servers: List[str]) -> None:
        """
        Set DNS servers.

        Args:
            servers: List of DNS server IP addresses to set.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError

    def reset_dns(self) -> None:
        """
        Reset DNS to system default (DHCP).

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"{self.__class__.__name__}(iface={self.iface!r})"

    def __str__(self) -> str:
        """Return human-readable string representation."""
        return f"{self.__class__.__name__} on {self.get_interface()}"


class ResolvConfDNS(DNSBackend):
    """
    DNS backend using /etc/resolv.conf directly.

    This backend directly modifies the resolv.conf file. It's used as a
    fallback when neither systemd-resolved nor NetworkManager is available.
    """

    def get_active_interface(self) -> str:
        """
        Get the active network interface using ip route.

        Returns:
            Name of the default route interface.

        Raises:
            InterfaceNotFoundError: If no default route is found.
        """
        result = run_command(["ip", "route", "show", "default"])
        out = result.stdout.strip()

        parts = out.split()
        if "dev" in parts:
            return parts[parts.index("dev") + 1]

        raise InterfaceNotFoundError("Cannot detect active network interface")

    def get_dns(self) -> List[str]:
        """
        Get DNS servers from /etc/resolv.conf.

        Returns:
            List of nameserver IP addresses.

        Raises:
            DNSOperationError: If permission is denied.
        """
        servers = []
        try:
            with open(LINUX_RESOLV_CONF) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("nameserver"):
                        parts = line.split()
                        if len(parts) >= 2:
                            servers.append(parts[1])
        except FileNotFoundError:
            pass
        except PermissionError:
            raise DNSOperationError(f"Permission denied reading {LINUX_RESOLV_CONF}")
        return servers

    def set_dns(self, servers: List[str]) -> None:
        """
        Set DNS servers in /etc/resolv.conf.

        Preserves existing non-nameserver lines (search, options, etc.).

        Args:
            servers: List of DNS server IP addresses.

        Raises:
            DNSOperationError: If permission is denied.
        """
        try:
            existing_lines = []
            try:
                with open(LINUX_RESOLV_CONF) as f:
                    for line in f:
                        if not line.strip().startswith("nameserver"):
                            existing_lines.append(line.rstrip("\n"))
            except FileNotFoundError:
                pass

            with open(LINUX_RESOLV_CONF, "w") as f:
                for line in existing_lines:
                    f.write(line + "\n")
                for s in servers:
                    f.write(f"nameserver {s}\n")
        except PermissionError:
            raise DNSOperationError(
                f"Permission denied writing to {LINUX_RESOLV_CONF}. Run as root."
            )

    def reset_dns(self) -> None:
        """
        Reset DNS - not supported for unmanaged resolv.conf.

        Raises:
            DNSOperationError: Always, as reset is not supported.
        """
        raise DNSOperationError(
            "Reset not supported on unmanaged Linux systems. "
            "Please restore your original /etc/resolv.conf manually."
        )


class SystemdResolvedDNS(DNSBackend):
    """
    DNS backend using systemd-resolved (resolvectl).

    This backend uses resolvectl commands to manage DNS through
    systemd-resolved service.
    """

    def get_active_interface(self) -> str:
        """
        Get the active network interface using ip route.

        Returns:
            Name of the default route interface.

        Raises:
            InterfaceNotFoundError: If no default route is found.
        """
        result = run_command(["ip", "route", "show", "default"])
        out = result.stdout.strip()

        parts = out.split()
        if "dev" in parts:
            return parts[parts.index("dev") + 1]

        raise InterfaceNotFoundError("Cannot detect active network interface")

    def get_dns(self) -> List[str]:
        """
        Get DNS servers using resolvectl.

        Returns:
            List of DNS server IP addresses for the interface.
        """
        iface = self.get_interface()
        try:
            result = run_command(["resolvectl", "dns", iface])
            out = result.stdout.strip()

            servers = []
            for line in out.splitlines():
                parts = line.split(":")
                if len(parts) >= 2:
                    dns_part = parts[-1].strip()
                    for addr in dns_part.split():
                        addr = addr.strip()
                        if addr:
                            try:
                                ipaddress.ip_address(addr)
                                servers.append(addr)
                            except ValueError:
                                pass
            return servers
        except CommandFailedError:
            return []

    def set_dns(self, servers: List[str]) -> None:
        """
        Set DNS servers using resolvectl.

        Args:
            servers: List of DNS server IP addresses.
        """
        iface = self.get_interface()
        run_command(["resolvectl", "dns", iface] + servers)

    def reset_dns(self) -> None:
        """Reset DNS to default using resolvectl revert."""
        iface = self.get_interface()
        run_command(["resolvectl", "revert", iface])


class NetworkManagerDNS(DNSBackend):
    """
    DNS backend using NetworkManager (nmcli).

    This backend uses nmcli commands to manage DNS through NetworkManager.
    """

    def get_active_interface(self) -> str:
        """
        Get the active network interface using ip route.

        Returns:
            Name of the default route interface.

        Raises:
            InterfaceNotFoundError: If no default route is found.
        """
        result = run_command(["ip", "route", "show", "default"])
        out = result.stdout.strip()

        parts = out.split()
        if "dev" in parts:
            return parts[parts.index("dev") + 1]

        raise InterfaceNotFoundError("Cannot detect active network interface")

    def _get_connection_name(self) -> str:
        """
        Get the active NetworkManager connection name for the interface.

        Returns:
            Connection name string.

        Raises:
            InterfaceNotFoundError: If no active connection is found.
        """
        iface = self.get_interface()
        result = run_command(
            ["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"]
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[1] == iface:
                return parts[0]
        raise InterfaceNotFoundError(
            f"No active NetworkManager connection for interface {iface}"
        )

    def get_dns(self) -> List[str]:
        """
        Get DNS servers using nmcli.

        Returns:
            List of DNS server IP addresses.
        """
        iface = self.get_interface()
        result = run_command(["nmcli", "-t", "-f", "IP4.DNS", "device", "show", iface])
        servers = []
        for line in result.stdout.strip().splitlines():
            if line.startswith("IP4.DNS"):
                parts = line.split(":")
                if len(parts) >= 2:
                    addr = parts[1].strip()
                    if addr:
                        servers.append(addr)
        return servers

    def set_dns(self, servers: List[str]) -> None:
        """
        Set DNS servers using nmcli.

        Also sets ignore-auto-dns to prevent DHCP from overwriting.

        Args:
            servers: List of DNS server IP addresses.
        """
        conn_name = self._get_connection_name()
        dns_string = " ".join(servers)
        run_command(
            ["nmcli", "connection", "modify", conn_name, "ipv4.dns", dns_string]
        )
        run_command(
            ["nmcli", "connection", "modify", conn_name, "ipv4.ignore-auto-dns", "yes"]
        )
        run_command(["nmcli", "connection", "up", conn_name])

    def reset_dns(self) -> None:
        """Reset DNS to DHCP defaults using nmcli."""
        conn_name = self._get_connection_name()
        run_command(["nmcli", "connection", "modify", conn_name, "ipv4.dns", ""])
        run_command(
            ["nmcli", "connection", "modify", conn_name, "ipv4.ignore-auto-dns", "no"]
        )
        run_command(["nmcli", "connection", "up", conn_name])


def _is_systemd_resolved_active() -> bool:
    """
    Check if systemd-resolved is active.

    Returns:
        True if systemd-resolved is running, False otherwise.
    """
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "systemd-resolved"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 and result.stdout.strip() == "active"
    except FileNotFoundError:
        return False


def _is_networkmanager_active() -> bool:
    """
    Check if NetworkManager is available and running.

    Returns:
        True if NetworkManager is available, False otherwise.
    """
    try:
        result = subprocess.run(
            ["nmcli", "general", "status"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_linux_backend(iface: Optional[str] = None) -> DNSBackend:
    """
    Get the appropriate Linux DNS backend based on system configuration.

    Detection order:
    1. systemd-resolved (if active)
    2. NetworkManager (if available)
    3. Direct /etc/resolv.conf manipulation (fallback)

    Args:
        iface: Optional network interface override.

    Returns:
        Appropriate DNSBackend instance for the system.
    """
    if _is_systemd_resolved_active():
        return SystemdResolvedDNS(iface)
    if _is_networkmanager_active():
        return NetworkManagerDNS(iface)
    return ResolvConfDNS(iface)


class MacOSDNS(DNSBackend):
    """
    DNS backend for macOS using networksetup.

    This backend uses networksetup commands to manage DNS settings
    and flushes the DNS cache after changes.
    """

    _service: Optional[str] = None

    def get_active_interface(self) -> str:
        """
        Get the active network interface.

        Tries scutil --nwi first, falls back to route get default.

        Returns:
            Name of the active network interface.

        Raises:
            InterfaceNotFoundError: If no active interface is found.
        """
        try:
            result = run_command(["scutil", "--nwi"])
            out = result.stdout

            for line in out.splitlines():
                line = line.strip()
                if line.startswith("Network interfaces:"):
                    parts = line.split(":")
                    if len(parts) >= 2:
                        ifaces = parts[1].strip().split()
                        if ifaces:
                            return ifaces[0]
        except CommandFailedError:
            pass

        try:
            result = run_command(["route", "-n", "get", "default"])
            out = result.stdout

            for line in out.splitlines():
                if "interface:" in line:
                    return line.split(":")[1].strip()
        except CommandFailedError:
            pass

        raise InterfaceNotFoundError("Cannot detect active network interface")

    def _interface_to_service(self, iface: str) -> str:
        """
        Map a network interface to its network service name.

        Args:
            iface: Network interface name (e.g., 'en0').

        Returns:
            Network service name (e.g., 'Wi-Fi').

        Raises:
            ServiceNotFoundError: If the interface cannot be mapped.
        """
        result = run_command(["networksetup", "-listallhardwareports"])
        out = result.stdout

        blocks = out.split("\n\n")
        for block in blocks:
            if f"Device: {iface}" in block:
                for line in block.splitlines():
                    if line.startswith("Hardware Port:"):
                        return line.split(":", 1)[1].strip()

        services_result = run_command(["networksetup", "-listallnetworkservices"])
        services = [
            s.strip()
            for s in services_result.stdout.splitlines()
            if s.strip() and not s.startswith("*")
        ]

        for service in services:
            try:
                info_result = run_command(
                    ["networksetup", "-getinfo", service], check=False
                )
                if iface in info_result.stdout:
                    return service
            except CommandFailedError:
                continue

        raise ServiceNotFoundError(f"Cannot map interface '{iface}' to network service")

    def _get_service(self) -> str:
        """
        Get the network service name, caching the result.

        Returns:
            Network service name.
        """
        if self._service is None:
            iface = self.get_interface()
            self._service = self._interface_to_service(iface)
        return self._service

    def get_dns(self) -> List[str]:
        """
        Get DNS servers using networksetup.

        Returns:
            List of DNS server IP addresses.
        """
        result = run_command(
            ["networksetup", "-getdnsservers", self._get_service()], check=False
        )
        out = result.stdout.strip()

        if "There aren't any DNS Servers" in out:
            return []

        servers = []
        for line in out.splitlines():
            line = line.strip()
            if line:
                try:
                    ipaddress.ip_address(line)
                    servers.append(line)
                except ValueError:
                    pass
        return servers

    def set_dns(self, servers: List[str]) -> None:
        """
        Set DNS servers using networksetup.

        Also flushes the DNS cache after setting.

        Args:
            servers: List of DNS server IP addresses.
        """
        run_command(
            ["networksetup", "-setdnsservers", self._get_service()] + servers
        )
        try:
            run_command(["dscacheutil", "-flushcache"])
        except CommandFailedError:
            pass
        try:
            run_command(["killall", "-HUP", "mDNSResponder"], check=False)
        except CommandFailedError:
            pass

    def reset_dns(self) -> None:
        """Reset DNS to DHCP defaults and flush cache."""
        run_command(["networksetup", "-setdnsservers", self._get_service(), "Empty"])
        try:
            run_command(["dscacheutil", "-flushcache"])
        except CommandFailedError:
            pass


class WindowsDNS(DNSBackend):
    """
    DNS backend for Windows using PowerShell.

    This backend uses PowerShell cmdlets for DNS management,
    providing locale-independent output parsing.
    """

    _cached_iface: Optional[str] = None

    def get_active_interface(self) -> str:
        """
        Get the active network interface using PowerShell.

        Returns:
            Interface alias of the default route interface.

        Raises:
            InterfaceNotFoundError: If no default route is found.
        """
        if self._cached_iface:
            return self._cached_iface

        ps_command = (
            "Get-NetRoute -DestinationPrefix '0.0.0.0/0' | "
            "Sort-Object RouteMetric | "
            "Select-Object -First 1 -ExpandProperty InterfaceAlias"
        )

        result = run_command(
            ["powershell", "-NoProfile", "-Command", ps_command]
        )
        out = result.stdout.strip()

        if not out:
            raise InterfaceNotFoundError("Cannot detect active network interface")

        self._cached_iface = out
        return out

    def get_dns(self) -> List[str]:
        """
        Get DNS servers using PowerShell.

        Returns:
            List of IPv4 DNS server addresses.
        """
        iface = self.get_interface()

        ps_command = (
            f"Get-DnsClientServerAddress -InterfaceAlias '{iface}' | "
            "Where-Object { $_.AddressFamily -eq 2 } | "
            "Select-Object -ExpandProperty ServerAddresses"
        )

        result = run_command(
            ["powershell", "-NoProfile", "-Command", ps_command], check=False
        )
        out = result.stdout.strip()

        if not out:
            return []

        servers = []
        for line in out.splitlines():
            line = line.strip()
            if line:
                try:
                    ipaddress.ip_address(line)
                    servers.append(line)
                except ValueError:
                    pass
        return servers

    def set_dns(self, servers: List[str]) -> None:
        """
        Set DNS servers using PowerShell.

        Args:
            servers: List of DNS server IP addresses.
        """
        iface = self.get_interface()

        servers_array = ",".join(f"'{s}'" for s in servers)
        ps_command = (
            f"Set-DnsClientServerAddress -InterfaceAlias '{iface}' "
            f"-ServerAddresses @({servers_array})"
        )

        run_command(["powershell", "-NoProfile", "-Command", ps_command])

    def reset_dns(self) -> None:
        """Reset DNS to DHCP defaults using PowerShell."""
        iface = self.get_interface()

        ps_command = (
            f"Set-DnsClientServerAddress -InterfaceAlias '{iface}' -ResetServerAddresses"
        )

        run_command(["powershell", "-NoProfile", "-Command", ps_command])


def get_backend(iface: Optional[str] = None) -> DNSBackend:
    """
    Get the appropriate DNS backend for the current platform.

    Args:
        iface: Optional network interface override.

    Returns:
        Platform-appropriate DNSBackend instance.

    Raises:
        BackendNotAvailableError: If no backend is available.
    """
    p = get_platform()
    if p == Platform.LINUX:
        return get_linux_backend(iface)
    if p == Platform.MACOS:
        return MacOSDNS(iface)
    if p == Platform.WINDOWS:
        return WindowsDNS(iface)
    raise BackendNotAvailableError("No DNS backend available")
