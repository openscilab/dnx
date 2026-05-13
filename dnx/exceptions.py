# -*- coding: utf-8 -*-
"""
Custom exceptions for dnx.

This module defines the exception hierarchy used throughout dnx for
error handling and providing meaningful error messages to users.
"""


class DNXError(Exception):
    """Base exception for all dnx errors."""

    pass


class AdminRequiredError(DNXError):
    """Raised when admin/root privileges are required but not available."""

    pass


class InterfaceNotFoundError(DNXError):
    """Raised when the network interface cannot be detected or does not exist."""

    pass


class InvalidIPError(DNXError):
    """Raised when an invalid IP address is provided."""

    pass


class UnsupportedPlatformError(DNXError):
    """Raised when the operating system is not supported."""

    pass


class CommandFailedError(DNXError):
    """Raised when a system command fails to execute."""

    pass


class DNSOperationError(DNXError):
    """Raised when a DNS operation (get/set/reset) fails."""

    pass


class ServiceNotFoundError(DNXError):
    """Raised when a network service cannot be found (macOS)."""

    pass


class BackendNotAvailableError(DNXError):
    """Raised when no suitable DNS backend is available."""

    pass
