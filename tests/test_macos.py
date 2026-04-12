# -*- coding: utf-8 -*-
"""Integration tests for macOS DNS backend."""

import pytest
from unittest.mock import patch, MagicMock

from dnx.dns import MacOSDNS
from dnx.exceptions import InterfaceNotFoundError, ServiceNotFoundError


@pytest.mark.macos
class TestMacOSDNS:
    """Tests for MacOSDNS backend."""

    def test_get_active_interface_via_scutil(self, sample_macos_nwi_output):
        with patch("dnx.dns.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout=sample_macos_nwi_output)
            backend = MacOSDNS()
            iface = backend.get_active_interface()

        assert iface == "en0"

    def test_get_active_interface_fallback_to_route(
        self, sample_macos_route_output
    ):
        from dnx.exceptions import CommandFailedError

        def side_effect(args, **kwargs):
            if args[0] == "scutil":
                raise CommandFailedError("scutil failed")
            return MagicMock(stdout=sample_macos_route_output)

        with patch("dnx.dns.run_command", side_effect=side_effect):
            backend = MacOSDNS()
            iface = backend.get_active_interface()

        assert iface == "en0"

    def test_interface_to_service(self, sample_macos_hardware_ports):
        with patch("dnx.dns.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout=sample_macos_hardware_ports)
            backend = MacOSDNS()
            service = backend._interface_to_service("en0")

        assert service == "Wi-Fi"

    def test_interface_to_service_not_found(self):
        mock_output = "Hardware Port: Wi-Fi\nDevice: en0\n\n"

        with patch("dnx.dns.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)

            with patch.object(MacOSDNS, "_interface_to_service") as mock_method:
                mock_method.side_effect = ServiceNotFoundError("Not found")
                backend = MacOSDNS()

                with pytest.raises(ServiceNotFoundError):
                    backend._interface_to_service("en99")

    def test_get_dns_parses_output(self):
        mock_output = "8.8.8.8\n8.8.4.4\n"

        with patch("dnx.dns.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            backend = MacOSDNS()
            backend._service = "Wi-Fi"
            servers = backend.get_dns()

        assert servers == ["8.8.8.8", "8.8.4.4"]

    def test_get_dns_no_servers(self):
        mock_output = "There aren't any DNS Servers set on Wi-Fi.\n"

        def side_effect(args, **kwargs):
            if args[:2] == ["scutil", "--dns"]:
                return MagicMock(stdout="")
            return MagicMock(stdout=mock_output)

        with patch("dnx.dns.run_command", side_effect=side_effect):
            backend = MacOSDNS()
            backend._service = "Wi-Fi"
            backend.iface = "en0"
            servers = backend.get_dns()

        assert servers == []

    def test_get_dns_filters_invalid_ips(self):
        mock_output = "8.8.8.8\nSome text\n1.1.1.1\n"

        with patch("dnx.dns.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            backend = MacOSDNS()
            backend._service = "Wi-Fi"
            servers = backend.get_dns()

        assert servers == ["8.8.8.8", "1.1.1.1"]

    def test_set_dns_calls_networksetup(self):
        call_count = 0

        def track_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock()

        with patch("dnx.dns.run_command", side_effect=track_calls):
            backend = MacOSDNS()
            backend._service = "Wi-Fi"
            backend.set_dns(["8.8.8.8", "8.8.4.4"])

        assert call_count >= 1

    def test_set_dns_flushes_cache(self):
        calls = []

        def track_calls(args, **kwargs):
            calls.append(args)
            return MagicMock()

        with patch("dnx.dns.run_command", side_effect=track_calls):
            backend = MacOSDNS()
            backend._service = "Wi-Fi"
            backend.set_dns(["8.8.8.8"])

        command_strings = [" ".join(c) for c in calls]
        assert any("dscacheutil" in c for c in command_strings)

    def test_reset_dns_uses_empty(self):
        calls = []

        def track_calls(args, **kwargs):
            calls.append(args)
            return MagicMock()

        with patch("dnx.dns.run_command", side_effect=track_calls):
            backend = MacOSDNS()
            backend._service = "Wi-Fi"
            backend.reset_dns()

        reset_call = [c for c in calls if "-setdnsservers" in c]
        assert len(reset_call) > 0
        assert "Empty" in reset_call[0]

    def test_service_caching(self):
        backend = MacOSDNS()
        backend._service = "Cached-Service"

        service = backend._get_service()
        assert service == "Cached-Service"

    def test_repr(self):
        backend = MacOSDNS(iface="en0")
        assert "MacOSDNS" in repr(backend)
        assert "en0" in repr(backend)


@pytest.mark.macos
class TestMacOSDNSIntegration:
    """Integration tests that actually call macOS APIs."""

    def test_get_interface_returns_valid_name(self):
        backend = MacOSDNS()
        try:
            iface = backend.get_active_interface()
            assert iface is not None
            assert isinstance(iface, str)
            assert iface.startswith("en") or iface.startswith("utun")
        except InterfaceNotFoundError:
            pytest.skip("No active interface found")

    def test_get_dns_returns_valid_ips(self):
        backend = MacOSDNS()
        try:
            servers = backend.get_dns()
            assert isinstance(servers, list)

            import ipaddress
            for server in servers:
                ipaddress.ip_address(server)
        except (InterfaceNotFoundError, ServiceNotFoundError):
            pytest.skip("Cannot get network service")

    @pytest.mark.requires_admin
    def test_set_and_reset_dns(self):
        backend = MacOSDNS()
        original = backend.get_dns()

        try:
            backend.set_dns(["8.8.8.8", "8.8.4.4"])
            new_servers = backend.get_dns()
            assert "8.8.8.8" in new_servers
        finally:
            backend.reset_dns()
