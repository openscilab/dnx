# -*- coding: utf-8 -*-
"""Tests for dnx exceptions."""

import pytest
from dnx.exceptions import (
    DNXError,
    AdminRequiredError,
    InterfaceNotFoundError,
    InvalidIPError,
    UnsupportedPlatformError,
    CommandFailedError,
    DNSOperationError,
    ServiceNotFoundError,
    BackendNotAvailableError,
)


class TestExceptionHierarchy:
    """Test that all exceptions inherit from DNXError."""

    def test_dnx_error_is_exception(self):
        assert issubclass(DNXError, Exception)

    def test_admin_required_error(self):
        assert issubclass(AdminRequiredError, DNXError)
        err = AdminRequiredError("test")
        assert str(err) == "test"

    def test_interface_not_found_error(self):
        assert issubclass(InterfaceNotFoundError, DNXError)
        err = InterfaceNotFoundError("eth0 not found")
        assert "eth0" in str(err)

    def test_invalid_ip_error(self):
        assert issubclass(InvalidIPError, DNXError)
        err = InvalidIPError("999.999.999.999")
        assert "999" in str(err)

    def test_unsupported_platform_error(self):
        assert issubclass(UnsupportedPlatformError, DNXError)

    def test_command_failed_error(self):
        assert issubclass(CommandFailedError, DNXError)

    def test_dns_operation_error(self):
        assert issubclass(DNSOperationError, DNXError)

    def test_service_not_found_error(self):
        assert issubclass(ServiceNotFoundError, DNXError)

    def test_backend_not_available_error(self):
        assert issubclass(BackendNotAvailableError, DNXError)


class TestExceptionCatching:
    """Test that exceptions can be caught properly."""

    def test_catch_dnx_error_catches_all(self):
        exceptions = [
            AdminRequiredError("test"),
            InterfaceNotFoundError("test"),
            InvalidIPError("test"),
            UnsupportedPlatformError("test"),
            CommandFailedError("test"),
            DNSOperationError("test"),
            ServiceNotFoundError("test"),
            BackendNotAvailableError("test"),
        ]

        for exc in exceptions:
            with pytest.raises(DNXError):
                raise exc

    def test_catch_specific_exception(self):
        with pytest.raises(AdminRequiredError):
            raise AdminRequiredError("Need admin")

        with pytest.raises(InvalidIPError):
            raise InvalidIPError("Bad IP")
