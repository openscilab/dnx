# -*- coding: utf-8 -*-
"""Tests for validation functions."""

import os
import subprocess

import pytest
from unittest.mock import patch, MagicMock

from dnx.dns import (
    Platform,
    validate_ips,
    get_platform,
    run_command,
    require_admin,
    DNSBackend,
    ResolvConfDNS,
)
from dnx.exceptions import (
    InvalidIPError,
    UnsupportedPlatformError,
    CommandFailedError,
    AdminRequiredError,
    DNSOperationError,
)


class TestValidateIPs:
    """Tests for IP address validation."""

    def test_valid_ipv4_single(self):
        """Test single valid IPv4 address."""
        validate_ips(["8.8.8.8"])

    def test_valid_ipv4_multiple(self):
        """Test multiple valid IPv4 addresses."""
        validate_ips(["8.8.8.8", "1.1.1.1", "9.9.9.9"])

    def test_valid_ipv6(self):
        """Test valid IPv6 address."""
        validate_ips(["2001:4860:4860::8888"])

    def test_valid_ipv6_short(self):
        """Test valid short IPv6 address."""
        validate_ips(["::1"])

    def test_valid_mixed_ipv4_ipv6(self):
        """Test mixed IPv4 and IPv6 addresses."""
        validate_ips(["8.8.8.8", "2001:4860:4860::8888"])

    def test_invalid_ip_raises(self):
        """Test that invalid IP raises InvalidIPError."""
        with pytest.raises(InvalidIPError) as exc_info:
            validate_ips(["not-an-ip"])
        assert "not-an-ip" in str(exc_info.value)

    def test_invalid_ip_out_of_range(self):
        """Test that out-of-range IP raises InvalidIPError."""
        with pytest.raises(InvalidIPError):
            validate_ips(["999.999.999.999"])

    def test_invalid_ip_partial(self):
        """Test that partial IP raises InvalidIPError."""
        with pytest.raises(InvalidIPError):
            validate_ips(["192.168.1"])

    def test_invalid_ip_empty_string(self):
        """Test that empty string raises InvalidIPError."""
        with pytest.raises(InvalidIPError):
            validate_ips([""])

    def test_invalid_ip_mixed_valid_invalid(self):
        """Test that mixed valid/invalid list raises on first invalid."""
        with pytest.raises(InvalidIPError) as exc_info:
            validate_ips(["8.8.8.8", "bad-ip", "1.1.1.1"])
        assert "bad-ip" in str(exc_info.value)

    def test_empty_list_passes(self):
        """Test that empty list is valid."""
        validate_ips([])

    def test_localhost(self):
        """Test localhost IP."""
        validate_ips(["127.0.0.1"])

    def test_private_ranges(self):
        """Test private IP ranges."""
        validate_ips(["192.168.1.1", "10.0.0.1", "172.16.0.1"])


class TestGetPlatform:
    """Tests for platform detection."""

    def test_returns_valid_platform(self):
        """Test that get_platform returns a valid Platform enum."""
        result = get_platform()
        assert result in [Platform.LINUX, Platform.MACOS, Platform.WINDOWS]

    def test_returns_platform_enum(self):
        """Test that get_platform returns a Platform enum instance."""
        result = get_platform()
        assert isinstance(result, Platform)

    def test_platform_has_value(self):
        """Test that Platform enum has string value."""
        result = get_platform()
        assert result.value in ["linux", "macos", "windows"]

    def test_unsupported_platform_raises(self):
        """Test that unsupported OS raises UnsupportedPlatformError."""
        with patch("dnx.dns.platform.system", return_value="FreeBSD"):
            with pytest.raises(UnsupportedPlatformError) as exc_info:
                get_platform()
            assert "freebsd" in str(exc_info.value).lower()


class TestRunCommand:
    """Tests for run_command error handling."""

    def test_command_not_found_raises(self):
        """Test that a nonexistent command raises CommandFailedError."""
        with pytest.raises(CommandFailedError) as exc_info:
            run_command(["__nonexistent_command_dnx_test__"])
        assert "not found" in str(exc_info.value).lower()

    def test_command_failure_raises(self):
        """Test that a failing command raises CommandFailedError."""
        with pytest.raises(CommandFailedError):
            run_command(["python", "-c", "import sys; sys.exit(1)"])

    def test_successful_command(self):
        """Test that a successful command returns CompletedProcess."""
        result = run_command(["python", "-c", "print('hello')"])
        assert result.returncode == 0
        assert "hello" in result.stdout


class TestRequireAdmin:
    """Tests for require_admin function."""

    def test_non_admin_raises_on_unix(self):
        """Test that non-root on Unix raises AdminRequiredError."""
        with patch("dnx.dns.get_platform", return_value=Platform.LINUX):
            with patch("dnx.dns.os.geteuid", create=True, return_value=1000):
                with pytest.raises(AdminRequiredError):
                    require_admin()

    def test_admin_passes_on_unix(self):
        """Test that root on Unix passes without error."""
        with patch("dnx.dns.get_platform", return_value=Platform.LINUX):
            with patch("dnx.dns.os.geteuid", create=True, return_value=0):
                require_admin()

    def test_non_admin_raises_on_windows(self):
        """Test that non-admin on Windows raises AdminRequiredError."""
        with patch("dnx.dns.get_platform", return_value=Platform.WINDOWS):
            with patch(
                "dnx.dns.subprocess.check_call",
                side_effect=subprocess.CalledProcessError(1, "net"),
            ):
                with pytest.raises(AdminRequiredError):
                    require_admin()

    def test_admin_passes_on_windows(self):
        """Test that admin on Windows passes without error."""
        with patch("dnx.dns.get_platform", return_value=Platform.WINDOWS):
            with patch("dnx.dns.subprocess.check_call"):
                require_admin()


class TestDNSBackendAbstract:
    """Tests for DNSBackend base class abstract methods."""

    def test_get_active_interface_raises(self):
        """Test that base class raises NotImplementedError."""
        backend = DNSBackend()
        with pytest.raises(NotImplementedError):
            backend.get_active_interface()

    def test_get_dns_raises(self):
        """Test that base class raises NotImplementedError."""
        backend = DNSBackend()
        with pytest.raises(NotImplementedError):
            backend.get_dns()

    def test_set_dns_raises(self):
        """Test that base class raises NotImplementedError."""
        backend = DNSBackend()
        with pytest.raises(NotImplementedError):
            backend.set_dns(["8.8.8.8"])

    def test_reset_dns_raises(self):
        """Test that base class raises NotImplementedError."""
        backend = DNSBackend()
        with pytest.raises(NotImplementedError):
            backend.reset_dns()

    def test_get_interface_returns_iface_when_set(self):
        """Test that get_interface returns user-specified iface."""
        backend = DNSBackend(iface="eth0")
        assert backend.get_interface() == "eth0"

    def test_get_interface_falls_back_to_active(self):
        """Test that get_interface calls get_active_interface when iface is None."""
        backend = DNSBackend()
        with patch.object(backend, "get_active_interface", return_value="wlan0"):
            assert backend.get_interface() == "wlan0"


class TestResolvConfGetDNSPermission:
    """Tests for ResolvConfDNS.get_dns permission error handling."""

    @pytest.mark.linux
    def test_get_dns_permission_error(self, tmp_path):
        """Test that PermissionError on get_dns raises DNSOperationError."""
        resolv_file = tmp_path / "resolv.conf"
        resolv_file.write_text("nameserver 8.8.8.8\n")
        os.chmod(resolv_file, 0o000)

        try:
            with patch("dnx.dns.LINUX_RESOLV_CONF", str(resolv_file)):
                backend = ResolvConfDNS()
                with pytest.raises(DNSOperationError):
                    backend.get_dns()
        finally:
            os.chmod(resolv_file, 0o644)
