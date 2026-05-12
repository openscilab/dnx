# -*- coding: utf-8 -*-
"""Integration tests for Linux DNS backends."""

import os
import pytest
from unittest.mock import patch, MagicMock

from dnx.dns import (
    ResolvConfDNS,
    SystemdResolvedDNS,
    NetworkManagerDNS,
    get_linux_backend,
    _is_systemd_resolved_active,
    _is_networkmanager_active,
)
from dnx.exceptions import InterfaceNotFoundError, DNSOperationError


@pytest.mark.linux
class TestResolvConfDNS:
    """Tests for ResolvConfDNS backend."""

    def test_get_active_interface(self):
        backend = ResolvConfDNS()
        iface = backend.get_active_interface()
        assert isinstance(iface, str)
        assert len(iface) > 0

    def test_get_dns_reads_resolv_conf(self, tmp_path):
        resolv_file = tmp_path / "resolv.conf"
        resolv_file.write_text("nameserver 8.8.8.8\nnameserver 1.1.1.1\n")

        with patch("dnx.dns.LINUX_RESOLV_CONF", str(resolv_file)):
            backend = ResolvConfDNS()
            servers = backend.get_dns()

        assert servers == ["8.8.8.8", "1.1.1.1"]

    def test_get_dns_handles_comments(self, tmp_path):
        resolv_file = tmp_path / "resolv.conf"
        resolv_file.write_text(
            "# comment\nnameserver 8.8.8.8\nsearch local\nnameserver 1.1.1.1\n"
        )

        with patch("dnx.dns.LINUX_RESOLV_CONF", str(resolv_file)):
            backend = ResolvConfDNS()
            servers = backend.get_dns()

        assert servers == ["8.8.8.8", "1.1.1.1"]

    def test_get_dns_missing_file(self, tmp_path):
        with patch("dnx.dns.LINUX_RESOLV_CONF", str(tmp_path / "nonexistent")):
            backend = ResolvConfDNS()
            servers = backend.get_dns()

        assert servers == []

    def test_set_dns_writes_resolv_conf(self, tmp_path):
        resolv_file = tmp_path / "resolv.conf"
        resolv_file.write_text("search local\noptions timeout:1\n")

        with patch("dnx.dns.LINUX_RESOLV_CONF", str(resolv_file)):
            backend = ResolvConfDNS()
            backend.set_dns(["9.9.9.9", "149.112.112.112"])

        content = resolv_file.read_text()
        assert "nameserver 9.9.9.9" in content
        assert "nameserver 149.112.112.112" in content
        assert "search local" in content

    def test_set_dns_permission_denied(self, tmp_path):
        resolv_file = tmp_path / "resolv.conf"
        resolv_file.write_text("")
        os.chmod(resolv_file, 0o000)

        try:
            with patch("dnx.dns.LINUX_RESOLV_CONF", str(resolv_file)):
                backend = ResolvConfDNS()
                with pytest.raises(DNSOperationError):
                    backend.set_dns(["8.8.8.8"])
        finally:
            os.chmod(resolv_file, 0o644)

    def test_reset_dns_raises(self):
        backend = ResolvConfDNS()
        with pytest.raises(DNSOperationError):
            backend.reset_dns()


@pytest.mark.linux
class TestSystemdResolvedDNS:
    """Tests for SystemdResolvedDNS backend."""

    def test_get_active_interface(self):
        backend = SystemdResolvedDNS()
        try:
            iface = backend.get_active_interface()
            assert isinstance(iface, str)
        except InterfaceNotFoundError:
            pytest.skip("No active interface found")

    def test_get_dns_parses_resolvectl_output(self):
        mock_output = "Link 2 (eth0): 8.8.8.8 8.8.4.4"

        with patch("dnx.dns.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            backend = SystemdResolvedDNS(iface="eth0")
            servers = backend.get_dns()

        assert "8.8.8.8" in servers
        assert "8.8.4.4" in servers


@pytest.mark.linux
class TestNetworkManagerDNS:
    """Tests for NetworkManagerDNS backend."""

    def test_get_active_interface(self):
        backend = NetworkManagerDNS()
        try:
            iface = backend.get_active_interface()
            assert isinstance(iface, str)
        except InterfaceNotFoundError:
            pytest.skip("No active interface found")

    def test_get_dns_parses_nmcli_output(self):
        mock_output = "IP4.DNS[1]:8.8.8.8\nIP4.DNS[2]:8.8.4.4"

        with patch("dnx.dns.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            backend = NetworkManagerDNS(iface="eth0")
            servers = backend.get_dns()

        assert servers == ["8.8.8.8", "8.8.4.4"]


@pytest.mark.linux
class TestLinuxBackendFactory:
    """Tests for get_linux_backend factory function."""

    def test_returns_backend(self):
        backend = get_linux_backend()
        assert backend is not None

    def test_systemd_resolved_detection(self):
        with patch("dnx.dns._is_systemd_resolved_active", return_value=True):
            backend = get_linux_backend()
            assert isinstance(backend, SystemdResolvedDNS)

    def test_networkmanager_detection(self):
        with patch("dnx.dns._is_systemd_resolved_active", return_value=False):
            with patch("dnx.dns._is_networkmanager_active", return_value=True):
                backend = get_linux_backend()
                assert isinstance(backend, NetworkManagerDNS)

    def test_fallback_to_resolvconf(self):
        with patch("dnx.dns._is_systemd_resolved_active", return_value=False):
            with patch("dnx.dns._is_networkmanager_active", return_value=False):
                backend = get_linux_backend()
                assert isinstance(backend, ResolvConfDNS)

    def test_passes_interface(self):
        with patch("dnx.dns._is_systemd_resolved_active", return_value=False):
            with patch("dnx.dns._is_networkmanager_active", return_value=False):
                backend = get_linux_backend(iface="eth1")
                assert backend.iface == "eth1"


@pytest.mark.linux
class TestSystemDetection:
    """Tests for system detection functions."""

    def test_is_systemd_resolved_active_returns_bool(self):
        result = _is_systemd_resolved_active()
        assert isinstance(result, bool)

    def test_is_networkmanager_active_returns_bool(self):
        result = _is_networkmanager_active()
        assert isinstance(result, bool)
