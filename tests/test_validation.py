# -*- coding: utf-8 -*-
"""Tests for validation functions."""

import pytest
from dnx.dns import validate_ips, get_platform, Platform
from dnx.exceptions import InvalidIPError, UnsupportedPlatformError


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
