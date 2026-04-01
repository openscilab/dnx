# -*- coding: utf-8 -*-
"""
Ping functionality for dnx.

This module provides cross-platform ping capabilities to check DNS server
reachability and measure latency.
"""

import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from .dns import Platform, get_platform
from .exceptions import CommandFailedError


@dataclass
class PingResult:
    """
    Result of pinging a DNS server.

    Attributes:
        ip: IP address that was pinged.
        reachable: Whether the server responded to ping.
        packets_sent: Number of ping packets sent.
        packets_received: Number of ping responses received.
        loss_percent: Percentage of packets lost (0-100).
        min_ms: Minimum round-trip time in milliseconds.
        avg_ms: Average round-trip time in milliseconds.
        max_ms: Maximum round-trip time in milliseconds.
        error: Error message if ping failed.
    """

    ip: str
    reachable: bool
    packets_sent: int = 0
    packets_received: int = 0
    loss_percent: float = 100.0
    min_ms: Optional[float] = None
    avg_ms: Optional[float] = None
    max_ms: Optional[float] = None
    error: Optional[str] = None

    @property
    def latency(self) -> Optional[float]:
        """
        Return average latency in milliseconds.

        Returns:
            Average round-trip time, or None if not available.
        """
        return self.avg_ms


def _get_ping_command(ip: str, count: int) -> List[str]:
    """
    Get the platform-specific ping command.

    Args:
        ip: IP address to ping.
        count: Number of ping packets to send.

    Returns:
        Command as list of strings.
    """
    current_platform = get_platform()

    if current_platform == Platform.WINDOWS:
        return ["ping", "-n", str(count), "-w", "1000", ip]
    else:
        return ["ping", "-c", str(count), "-W", "1", ip]


def _parse_ping_output_unix(output: str) -> dict:
    """
    Parse ping output on Unix-like systems (Linux/macOS).

    Args:
        output: Raw ping command output.

    Returns:
        Dictionary with parsed statistics.
    """
    result = {
        "packets_sent": 0,
        "packets_received": 0,
        "loss_percent": 100.0,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
    }

    packet_match = re.search(
        r"(\d+)\s+packets?\s+transmitted,\s+(\d+)\s+(?:packets?\s+)?received",
        output,
        re.IGNORECASE,
    )
    if packet_match:
        result["packets_sent"] = int(packet_match.group(1))
        result["packets_received"] = int(packet_match.group(2))
        if result["packets_sent"] > 0:
            result["loss_percent"] = (
                100.0
                * (result["packets_sent"] - result["packets_received"])
                / result["packets_sent"]
            )

    rtt_match = re.search(
        r"(?:rtt|round-trip)\s+min/avg/max(?:/[a-z]+)?\s*=\s*"
        r"([\d.]+)/([\d.]+)/([\d.]+)",
        output,
        re.IGNORECASE,
    )
    if rtt_match:
        result["min_ms"] = float(rtt_match.group(1))
        result["avg_ms"] = float(rtt_match.group(2))
        result["max_ms"] = float(rtt_match.group(3))

    return result


def _parse_ping_output_windows(output: str) -> dict:
    """
    Parse ping output on Windows.

    Args:
        output: Raw ping command output.

    Returns:
        Dictionary with parsed statistics.
    """
    result = {
        "packets_sent": 0,
        "packets_received": 0,
        "loss_percent": 100.0,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
    }

    packet_match = re.search(
        r"Packets:\s*Sent\s*=\s*(\d+),\s*Received\s*=\s*(\d+)",
        output,
        re.IGNORECASE,
    )
    if packet_match:
        result["packets_sent"] = int(packet_match.group(1))
        result["packets_received"] = int(packet_match.group(2))
        if result["packets_sent"] > 0:
            result["loss_percent"] = (
                100.0
                * (result["packets_sent"] - result["packets_received"])
                / result["packets_sent"]
            )

    rtt_match = re.search(
        r"Minimum\s*=\s*(\d+)ms,\s*Maximum\s*=\s*(\d+)ms,\s*Average\s*=\s*(\d+)ms",
        output,
        re.IGNORECASE,
    )
    if rtt_match:
        result["min_ms"] = float(rtt_match.group(1))
        result["max_ms"] = float(rtt_match.group(2))
        result["avg_ms"] = float(rtt_match.group(3))

    return result


def ping_server(ip: str, count: int = 3, timeout: int = 5) -> PingResult:
    """
    Ping a DNS server and return latency statistics.

    Args:
        ip: IP address to ping.
        count: Number of ping packets to send.
        timeout: Overall timeout in seconds.

    Returns:
        PingResult with reachability and latency information.
    """
    cmd = _get_ping_command(ip, count)
    current_platform = get_platform()

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + count * 2,
        )
        output = proc.stdout + proc.stderr

        if current_platform == Platform.WINDOWS:
            parsed = _parse_ping_output_windows(output)
        else:
            parsed = _parse_ping_output_unix(output)

        reachable = parsed["packets_received"] > 0

        return PingResult(
            ip=ip,
            reachable=reachable,
            packets_sent=parsed["packets_sent"],
            packets_received=parsed["packets_received"],
            loss_percent=parsed["loss_percent"],
            min_ms=parsed["min_ms"],
            avg_ms=parsed["avg_ms"],
            max_ms=parsed["max_ms"],
        )

    except subprocess.TimeoutExpired:
        return PingResult(
            ip=ip,
            reachable=False,
            packets_sent=count,
            packets_received=0,
            loss_percent=100.0,
            error="Timeout",
        )
    except FileNotFoundError:
        return PingResult(
            ip=ip,
            reachable=False,
            error="ping command not found",
        )
    except Exception as e:
        return PingResult(
            ip=ip,
            reachable=False,
            error=str(e),
        )


def ping_servers(servers: List[str], count: int = 3) -> List[PingResult]:
    """
    Ping multiple DNS servers.

    Args:
        servers: List of IP addresses to ping.
        count: Number of ping packets to send to each server.

    Returns:
        List of PingResult objects.
    """
    return [ping_server(ip, count) for ip in servers]


def verify_servers(servers: List[str], count: int = 2) -> tuple:
    """
    Verify that DNS servers are reachable.

    Args:
        servers: List of IP addresses to verify.
        count: Number of ping packets to send.

    Returns:
        Tuple of (all_reachable: bool, results: List[PingResult]).
    """
    results = ping_servers(servers, count)
    all_reachable = all(r.reachable for r in results)
    return all_reachable, results


def format_ping_result(result: PingResult) -> str:
    """
    Format a single ping result for display.

    Args:
        result: PingResult to format.

    Returns:
        Formatted string representation.
    """
    if result.error:
        return f"{result.ip}: Error - {result.error}"

    if not result.reachable:
        return f"{result.ip}: Unreachable (100% packet loss)"

    latency_str = f"{result.avg_ms:.1f}ms" if result.avg_ms else "N/A"
    loss_str = f"{result.loss_percent:.0f}%"

    return f"{result.ip}: {latency_str} avg ({loss_str} loss)"


def format_ping_results(results: List[PingResult]) -> str:
    """
    Format multiple ping results for display.

    Args:
        results: List of PingResult objects.

    Returns:
        Multi-line formatted string.
    """
    lines = [format_ping_result(r) for r in results]
    return "\n".join(lines)
