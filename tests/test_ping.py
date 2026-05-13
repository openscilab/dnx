# -*- coding: utf-8 -*-
"""Tests for ping functionality."""

import pytest
from dnx.ping import (
    PingResult,
    ping_server,
    ping_servers,
    verify_servers,
    format_ping_result,
    format_ping_summary,
    _parse_ping_output_unix,
    _parse_ping_output_windows,
)


class TestPingResult:
    """Tests for PingResult dataclass."""

    def test_ping_result_creation(self):
        result = PingResult(ip="8.8.8.8", reachable=True, avg_ms=12.5)
        assert result.ip == "8.8.8.8"
        assert result.reachable is True
        assert result.avg_ms == 12.5

    def test_ping_result_defaults(self):
        result = PingResult(ip="1.1.1.1", reachable=False)
        assert result.packets_sent == 0
        assert result.packets_received == 0
        assert result.loss_percent == 100.0
        assert result.min_ms is None
        assert result.avg_ms is None
        assert result.max_ms is None
        assert result.error is None

    def test_latency_property(self):
        result = PingResult(ip="8.8.8.8", reachable=True, avg_ms=15.0)
        assert result.latency == 15.0

    def test_latency_property_none(self):
        result = PingResult(ip="8.8.8.8", reachable=False)
        assert result.latency is None


class TestParsePingOutput:
    """Tests for ping output parsing."""

    def test_parse_linux_output_success(self, sample_ping_output_linux):
        result = _parse_ping_output_unix(sample_ping_output_linux)
        assert result["packets_sent"] == 3
        assert result["packets_received"] == 3
        assert result["loss_percent"] == 0.0
        assert result["min_ms"] == 11.8
        assert result["avg_ms"] == 12.067
        assert result["max_ms"] == 12.3

    def test_parse_macos_output_success(self, sample_ping_output_macos):
        result = _parse_ping_output_unix(sample_ping_output_macos)
        assert result["packets_sent"] == 3
        assert result["packets_received"] == 3
        assert result["loss_percent"] == 0.0
        assert result["min_ms"] == 14.8
        assert result["avg_ms"] == 15.0
        assert result["max_ms"] == 15.2

    def test_parse_windows_output_success(self, sample_ping_output_windows):
        result = _parse_ping_output_windows(sample_ping_output_windows)
        assert result["packets_sent"] == 3
        assert result["packets_received"] == 3
        assert result["loss_percent"] == 0.0
        assert result["min_ms"] == 11.0
        assert result["max_ms"] == 13.0
        assert result["avg_ms"] == 12.0

    def test_parse_unreachable_output(self, sample_ping_output_unreachable):
        result = _parse_ping_output_unix(sample_ping_output_unreachable)
        assert result["packets_sent"] == 3
        assert result["packets_received"] == 0
        assert result["loss_percent"] == 100.0
        assert result["avg_ms"] is None

    def test_parse_empty_output(self):
        result = _parse_ping_output_unix("")
        assert result["packets_sent"] == 0
        assert result["packets_received"] == 0


class TestPingServer:
    """Tests for ping_server function."""

    def test_ping_localhost(self):
        result = ping_server("127.0.0.1", count=1)
        assert result.ip == "127.0.0.1"
        assert result.reachable is True
        assert result.packets_received >= 1

    def test_ping_unreachable_host(self):
        result = ping_server("10.255.255.1", count=1, timeout=2)
        assert result.reachable is False

    def test_ping_invalid_ip(self):
        result = ping_server("999.999.999.999", count=1, timeout=2)
        assert result.reachable is False


class TestPingServers:
    """Tests for ping_servers function."""

    def test_ping_multiple_servers(self):
        results = ping_servers(["127.0.0.1"], count=1)
        assert len(results) == 1
        assert results[0].ip == "127.0.0.1"

    def test_ping_empty_list(self):
        results = ping_servers([], count=1)
        assert results == []


class TestVerifyServers:
    """Tests for verify_servers function."""

    def test_verify_reachable(self):
        all_ok, results = verify_servers(["127.0.0.1"], count=1)
        assert all_ok is True
        assert len(results) == 1

    def test_verify_unreachable(self):
        all_ok, results = verify_servers(["10.255.255.1"], count=1)
        assert all_ok is False


class TestFormatPingResult:
    """Tests for formatting ping results."""

    def test_format_successful_ping(self):
        result = PingResult(
            ip="8.8.8.8",
            reachable=True,
            packets_sent=3,
            packets_received=3,
            loss_percent=0.0,
            avg_ms=12.5,
        )
        output = format_ping_result(result)
        assert "8.8.8.8" in output
        assert "12.5ms" in output
        assert "0%" in output

    def test_format_unreachable(self):
        result = PingResult(ip="10.0.0.1", reachable=False)
        output = format_ping_result(result)
        assert "10.0.0.1" in output
        assert "Unreachable" in output

    def test_format_with_error(self):
        result = PingResult(ip="bad", reachable=False, error="Invalid address")
        output = format_ping_result(result)
        assert "Error" in output
        assert "Invalid address" in output


class TestFormatPingResults:
    """Tests for formatting multiple ping results."""

    def test_format_multiple(self):
        results = [
            PingResult(ip="8.8.8.8", reachable=True, avg_ms=10.0, loss_percent=0.0),
            PingResult(ip="1.1.1.1", reachable=True, avg_ms=15.0, loss_percent=0.0),
        ]
        output = format_ping_summary(results)
        assert "8.8.8.8" in output
        assert "1.1.1.1" in output
        lines = output.strip().split("\n")
        assert len(lines) == 2

    def test_format_empty_list(self):
        output = format_ping_summary([])
        assert output == ""
