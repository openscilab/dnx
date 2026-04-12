# -*- coding: utf-8 -*-
"""Tests for macOS `scutil --dns` fallback parsing (runs on all platforms)."""

from unittest.mock import MagicMock, patch

from dnx.dns import MacOSDNS, _macos_scutil_dns_nameservers


def test_macos_scutil_parser_collects_nameservers():
    sample = (
        "resolver #1\n"
        "  nameserver[0] : 192.168.1.1\n"
        "  nameserver[1] : 2001:db8::1\n"
        "resolver #2\n"
        "  nameserver[0] : 8.8.8.8\n"
    )
    with patch("dnx.dns.run_command", return_value=MagicMock(stdout=sample)):
        assert _macos_scutil_dns_nameservers() == [
            "192.168.1.1",
            "2001:db8::1",
            "8.8.8.8",
        ]


def test_macos_scutil_parser_deduplicates():
    sample = (
        "resolver #1\n  nameserver[0] : 1.1.1.1\n"
        "resolver #2\n  nameserver[0] : 1.1.1.1\n"
    )
    with patch("dnx.dns.run_command", return_value=MagicMock(stdout=sample)):
        assert _macos_scutil_dns_nameservers() == ["1.1.1.1"]


def test_macos_scutil_skips_not_reachable_blocks():
    sample = (
        "resolver #1\n"
        "  nameserver[0] : 192.168.1.1\n"
        "  reach    : 0x00020002 (Reachable,Directly Reachable Address)\n"
        "resolver #2\n"
        "  domain   : local\n"
        "  reach    : 0x00000000 (Not Reachable)\n"
        "  nameserver[0] : 9.9.9.9\n"
    )
    with patch("dnx.dns.run_command", return_value=MagicMock(stdout=sample)):
        assert _macos_scutil_dns_nameservers() == ["192.168.1.1"]


def test_macos_scutil_strips_scoped_section():
    main = (
        "resolver #1\n  nameserver[0] : 1.1.1.1\n"
    )
    scoped = (
        "resolver #1\n  nameserver[0] : 1.1.1.1\n"
    )
    sample = main + "DNS configuration (for scoped queries)\n" + scoped
    with patch("dnx.dns.run_command", return_value=MagicMock(stdout=sample)):
        assert _macos_scutil_dns_nameservers() == ["1.1.1.1"]


def test_macos_scutil_prefers_if_index_block():
    sample = (
        "resolver #1\n"
        "  nameserver[0] : 8.8.8.8\n"
        "  if_index : 99 (en9)\n"
        "resolver #2\n"
        "  nameserver[0] : 192.168.1.1\n"
        "  if_index : 14 (en0)\n"
    )
    with patch("dnx.dns.run_command", return_value=MagicMock(stdout=sample)):
        assert _macos_scutil_dns_nameservers("en0") == ["192.168.1.1"]


def test_macos_scutil_ipv4_before_ipv6_per_block():
    sample = (
        "resolver #1\n"
        "  nameserver[0] : 2603:8000::1\n"
        "  nameserver[1] : 192.168.1.1\n"
    )
    with patch("dnx.dns.run_command", return_value=MagicMock(stdout=sample)):
        assert _macos_scutil_dns_nameservers() == ["192.168.1.1", "2603:8000::1"]


def test_get_dns_dhcp_uses_scutil_fallback():
    no_manual = "There aren't any DNS Servers set on Wi-Fi.\n"
    scutil_out = "resolver #1\n  nameserver[0] : 10.0.0.2\n"

    def side_effect(args, **kwargs):
        if args[:2] == ["scutil", "--dns"]:
            return MagicMock(stdout=scutil_out)
        return MagicMock(stdout=no_manual)

    with patch("dnx.dns.run_command", side_effect=side_effect):
        backend = MacOSDNS()
        backend._service = "Wi-Fi"
        backend.iface = "en0"
        assert backend.get_dns() == ["10.0.0.2"]
