# -*- coding: utf-8 -*-
"""Integration tests for Windows DNS backend."""

import pytest
from unittest.mock import patch, MagicMock

from dnx.dns import WindowsDNS, DNSBackend, get_backend
from dnx.exceptions import InterfaceNotFoundError


@pytest.mark.windows
class TestWindowsDNS:
    """Tests for WindowsDNS backend."""

    def test_get_active_interface(self):
        backend = WindowsDNS()
        iface = backend.get_active_interface()
        assert isinstance(iface, str)
        assert len(iface) > 0

    def test_get_active_interface_cached(self):
        backend = WindowsDNS()
        backend._cached_iface = "Cached-Interface"
        assert backend.get_active_interface() == "Cached-Interface"

    def test_get_dns_returns_list(self):
        backend = WindowsDNS()
        servers = backend.get_dns()
        assert isinstance(servers, list)

    def test_get_dns_parses_powershell_output(self):
        mock_output = "8.8.8.8\n8.8.4.4\n"

        with patch("dnx.dns.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            backend = WindowsDNS(iface="Wi-Fi")
            servers = backend.get_dns()

        assert servers == ["8.8.8.8", "8.8.4.4"]

    def test_get_dns_handles_empty_output(self):
        with patch("dnx.dns.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            backend = WindowsDNS(iface="Wi-Fi")
            servers = backend.get_dns()

        assert servers == []

    def test_get_dns_filters_invalid_ips(self):
        mock_output = "8.8.8.8\nNot an IP\n1.1.1.1\n"

        with patch("dnx.dns.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            backend = WindowsDNS(iface="Wi-Fi")
            servers = backend.get_dns()

        assert servers == ["8.8.8.8", "1.1.1.1"]

    def test_set_dns_uses_powershell(self):
        with patch("dnx.dns.run_command") as mock_run:
            backend = WindowsDNS(iface="Wi-Fi")
            backend.set_dns(["8.8.8.8", "8.8.4.4"])

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "powershell" in call_args
        assert "Set-DnsClientServerAddress" in call_args[-1]
        assert "Wi-Fi" in call_args[-1]
        assert "8.8.8.8" in call_args[-1]
        assert "8.8.4.4" in call_args[-1]

    def test_reset_dns_uses_powershell(self):
        with patch("dnx.dns.run_command") as mock_run:
            backend = WindowsDNS(iface="Wi-Fi")
            backend.reset_dns()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "powershell" in call_args
        assert "ResetServerAddresses" in call_args[-1]

    def test_interface_with_spaces(self):
        mock_output = "8.8.8.8\n"

        with patch("dnx.dns.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            backend = WindowsDNS(iface="Ethernet 2")
            backend.get_dns()

        call_args = mock_run.call_args[0][0]
        assert "Ethernet 2" in call_args[-1]


@pytest.mark.windows
class TestWindowsGetBackend:
    """Tests for get_backend() on Windows."""

    def test_get_backend_returns_windows_dns(self):
        """Verify get_backend() returns a WindowsDNS instance on Windows."""
        backend = get_backend()
        assert isinstance(backend, WindowsDNS)
        assert isinstance(backend, DNSBackend)

    def test_get_backend_passes_iface(self):
        """Verify get_backend() forwards the iface argument."""
        backend = get_backend(iface="Wi-Fi")
        assert backend.iface == "Wi-Fi"


@pytest.mark.windows
class TestWindowsDNSIntegration:
    """Integration tests that actually call Windows APIs."""

    def test_get_interface_returns_valid_name(self):
        backend = WindowsDNS()
        iface = backend.get_active_interface()
        assert iface is not None
        assert isinstance(iface, str)
        assert len(iface.strip()) > 0

    def test_get_dns_returns_valid_ips(self):
        backend = WindowsDNS()
        servers = backend.get_dns()
        assert isinstance(servers, list)

        import ipaddress
        for server in servers:
            ipaddress.ip_address(server)

    @pytest.mark.requires_admin
    def test_set_and_reset_dns(self):
        backend = WindowsDNS()
        original = backend.get_dns()

        try:
            backend.set_dns(["8.8.8.8", "8.8.4.4"])
            new_servers = backend.get_dns()
            assert "8.8.8.8" in new_servers
        finally:
            backend.reset_dns()
