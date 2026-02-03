# -*- coding: utf-8 -*-
"""dnx functions."""

import ipaddress
import os
import platform
import subprocess
import sys
from typing import List, Optional
from .params import LINUX_RESOLV_CONF


def die(msg: str):
    print(msg)
    sys.exit(1)


def require_admin():
    if os.name != "nt":
        if os.geteuid() != 0:
            die("Please run as root (sudo)")
    else:
        try:
            subprocess.check_call(
                ["net", "session"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            die("Please run as Administrator")


def validate_ips(servers: List[str]):
    for s in servers:
        try:
            ipaddress.ip_address(s)
        except ValueError:
            die(f"Invalid IP address: {s}")


def get_platform():
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    die("Unsupported operating system")


class DNSBackend:
    def __init__(self, iface: Optional[str] = None):
        self.iface = iface

    def get_active_interface(self) -> str:
        raise NotImplementedError

    def get_interface(self) -> str:
        if self.iface:
            return self.iface
        return self.get_active_interface()

    def get_dns(self) -> List[str]:
        raise NotImplementedError

    def set_dns(self, servers: List[str]) -> None:
        raise NotImplementedError

    def reset_dns(self) -> None:
        raise NotImplementedError


class LinuxDNS(DNSBackend):
    def get_active_interface(self) -> str:
        out = subprocess.check_output(
            ["ip", "route", "show", "default"],
            text=True,
        ).strip()

        parts = out.split()
        if "dev" in parts:
            return parts[parts.index("dev") + 1]

        die("Cannot detect active network interface")

    def get_dns(self):
        servers = []
        try:
            with open(LINUX_RESOLV_CONF) as f:
                for line in f:
                    if line.startswith("nameserver"):
                        servers.append(line.split()[1])
        except FileNotFoundError:
            pass
        return servers

    def set_dns(self, servers):
        content = "\n".join(f"nameserver {s}" for s in servers)
        with open(LINUX_RESOLV_CONF, "w") as f:
            f.write(content + "\n")

    def reset_dns(self):
        die("Reset not supported on unmanaged Linux systems")


class MacOSDNS(DNSBackend):
    _service = None

    def get_active_interface(self) -> str:
        out = subprocess.check_output(
            ["route", "get", "default"],
            text=True,
        )

        for line in out.splitlines():
            if "interface:" in line:
                return line.split(":")[1].strip()

        die("Cannot detect active network interface")

    def _interface_to_service(self, iface: str) -> str:
        out = subprocess.check_output(
            ["networksetup", "-listallhardwareports"],
            text=True,
        )

        blocks = out.split("\n\n")
        for block in blocks:
            if f"Device: {iface}" in block:
                for line in block.splitlines():
                    if line.startswith("Hardware Port"):
                        return line.split(":")[1].strip()

        die(f"Cannot map interface '{iface}' to network service")

    def _get_service(self) -> str:
        if self._service is None:
            iface = self.get_interface()
            self._service = self._interface_to_service(iface)
        return self._service

    def get_dns(self):
        out = subprocess.check_output(
            ["networksetup", "-getdnsservers", self._get_service()],
            text=True,
        ).strip()

        if "There aren't any DNS Servers" in out:
            return []

        return out.splitlines()

    def set_dns(self, servers):
        subprocess.check_call(
            ["networksetup", "-setdnsservers", self._get_service(), *servers]
        )

    def reset_dns(self):
        subprocess.check_call(
            ["networksetup", "-setdnsservers", self._get_service(), "Empty"]
        )


class WindowsDNS(DNSBackend):
    _cached_iface = None

    def get_active_interface(self) -> str:
        if self._cached_iface:
            return self._cached_iface

        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetRoute -DestinationPrefix 0.0.0.0/0 | "
                "Sort-Object RouteMetric | "
                "Select-Object -First 1 -ExpandProperty InterfaceAlias",
            ],
            text=True,
        ).strip()

        if not out:
            die("Cannot detect active network interface")

        self._cached_iface = out
        return out

    def get_dns(self):
        iface = self.get_interface()
        out = subprocess.check_output(
            ["netsh", "interface", "ip", "show", "dns", f"name={iface}"],
            text=True,
        )

        servers = []
        for line in out.splitlines():
            line = line.strip()
            if line and line[0].isdigit():
                servers.append(line)

        return servers

    def set_dns(self, servers):
        iface = self.get_interface()

        subprocess.check_call(
            [
                "netsh",
                "interface",
                "ip",
                "set",
                "dns",
                f"name={iface}",
                "static",
                servers[0],
            ]
        )

        for idx, s in enumerate(servers[1:], start=2):
            subprocess.check_call(
                [
                    "netsh",
                    "interface",
                    "ip",
                    "add",
                    "dns",
                    f"name={iface}",
                    s,
                    f"index={idx}",
                ]
            )

    def reset_dns(self):
        subprocess.check_call(
            [
                "netsh",
                "interface",
                "ip",
                "set",
                "dns",
                f"name={self.get_interface()}",
                "dhcp",
            ]
        )


def get_backend(iface: Optional[str] = None) -> DNSBackend:
    p = get_platform()
    if p == "linux":
        return LinuxDNS(iface)
    if p == "macos":
        return MacOSDNS(iface)
    if p == "windows":
        return WindowsDNS(iface)
    die("No DNS backend available")

