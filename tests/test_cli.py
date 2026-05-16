# -*- coding: utf-8 -*-
"""Tests for CLI functionality."""

import pytest
import sys
from io import StringIO
from unittest.mock import patch, MagicMock
from dnx.cli import main
from dnx.exceptions import DNXError
from dnx.params import DNS_PRESETS, DNX_VERSION
from dnx.ping import PingResult


class TestCLIVersion:
    """Tests for global --version."""

    def test_version_flag(self):
        with patch.object(sys, "argv", ["dnx", "--version"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc:
                    main()
        assert exc.value.code == 0
        assert mock_stdout.getvalue().strip() == f"dnx {DNX_VERSION}"


class TestCLIList:
    """Tests for 'dnx list' command."""

    def test_list_shows_all_presets(self):
        with patch.object(sys, "argv", ["dnx", "list"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()

        for name in DNS_PRESETS:
            assert name in output

    def test_list_shows_ips(self):
        with patch.object(sys, "argv", ["dnx", "list"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()

        assert "8.8.8.8" in output
        assert "1.1.1.1" in output


class TestCLICurrent:
    """Tests for 'dnx current' command."""

    def test_current_shows_dns(self):
        mock_backend = MagicMock()
        mock_backend.get_dns.return_value = ["8.8.8.8", "8.8.4.4"]

        with patch.object(sys, "argv", ["dnx", "current"]):
            with patch("dnx.cli.get_backend", return_value=mock_backend):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    main()
                    output = mock_stdout.getvalue()

        assert "8.8.8.8" in output
        assert "8.8.4.4" in output

    def test_current_no_dns(self):
        mock_backend = MagicMock()
        mock_backend.get_dns.return_value = []

        with patch.object(sys, "argv", ["dnx", "current"]):
            with patch("dnx.cli.get_backend", return_value=mock_backend):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    main()
                    output = mock_stdout.getvalue()

        assert "No DNS servers configured" in output


class TestCLISet:
    """Tests for 'dnx set' command."""

    def test_set_requires_servers(self):
        with patch.object(sys, "argv", ["dnx", "set"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2

    def test_set_with_preset(self):
        mock_backend = MagicMock()
        mock_backend.get_dns.return_value = []

        with patch.object(sys, "argv", ["dnx", "set", "cloudflare", "--no-latency"]):
            with patch("dnx.cli.get_backend", return_value=mock_backend):
                with patch("dnx.cli.require_admin"):
                    with patch("sys.stdout", new_callable=StringIO):
                        main()

        mock_backend.set_dns.assert_called_once_with(["1.1.1.1", "1.0.0.1"])

    def test_set_with_custom_ips(self):
        mock_backend = MagicMock()
        mock_backend.get_dns.return_value = []

        with patch.object(sys, "argv", ["dnx", "set", "9.9.9.9", "1.1.1.1", "--no-latency"]):
            with patch("dnx.cli.get_backend", return_value=mock_backend):
                with patch("dnx.cli.require_admin"):
                    with patch("sys.stdout", new_callable=StringIO):
                        main()

        mock_backend.set_dns.assert_called_once_with(["9.9.9.9", "1.1.1.1"])

    def test_set_invalid_ip_fails(self):
        with patch.object(sys, "argv", ["dnx", "set", "invalid-ip"]):
            with patch("dnx.cli.require_admin"):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1


class TestCLIReset:
    """Tests for 'dnx reset' command."""

    def test_reset_calls_backend(self):
        mock_backend = MagicMock()

        with patch.object(sys, "argv", ["dnx", "reset"]):
            with patch("dnx.cli.get_backend", return_value=mock_backend):
                with patch("dnx.cli.require_admin"):
                    with patch("sys.stdout", new_callable=StringIO):
                        main()

        mock_backend.reset_dns.assert_called_once()


class TestCLIPing:
    """Tests for 'dnx ping' command."""

    def test_ping_with_preset(self):
        with patch.object(sys, "argv", ["dnx", "ping", "google"]):
            with patch("dnx.cli.ping_servers") as mock_ping:
                mock_ping.return_value = []
                with patch("sys.stdout", new_callable=StringIO):
                    main()

        mock_ping.assert_called_once()
        call_args = mock_ping.call_args[0][0]
        assert call_args == ["8.8.8.8", "8.8.4.4"]

    def test_ping_with_custom_ip(self):
        with patch.object(sys, "argv", ["dnx", "ping", "1.1.1.1"]):
            with patch("dnx.cli.ping_servers") as mock_ping:
                mock_ping.return_value = []
                with patch("sys.stdout", new_callable=StringIO):
                    main()

        mock_ping.assert_called_once()
        call_args = mock_ping.call_args[0][0]
        assert call_args == ["1.1.1.1"]

    def test_ping_with_count_option(self):
        with patch.object(sys, "argv", ["dnx", "ping", "-c", "5", "8.8.8.8"]):
            with patch("dnx.cli.ping_servers") as mock_ping:
                mock_ping.return_value = []
                with patch("sys.stdout", new_callable=StringIO):
                    main()

        mock_ping.assert_called_once_with(["8.8.8.8"], count=5)


class TestCLIInterface:
    """Tests for --iface option."""

    def test_iface_passed_to_backend(self):
        with patch.object(sys, "argv", ["dnx", "--iface", "eth0", "current"]):
            with patch("dnx.cli.get_backend") as mock_get_backend:
                mock_backend = MagicMock()
                mock_backend.get_dns.return_value = []
                mock_get_backend.return_value = mock_backend
                with patch("sys.stdout", new_callable=StringIO):
                    main()

        mock_get_backend.assert_called_once_with("eth0")


class TestCLIListLatency:
    """Tests for 'dnx list --latency' command."""

    def test_list_latency_shows_results(self):
        """Verify --latency pings every preset and prints results."""
        fake_result = PingResult(
            ip="8.8.8.8", reachable=True, avg_ms=10.0, loss_percent=0.0
        )
        with patch.object(sys, "argv", ["dnx", "list", "--latency"]):
            with patch("dnx.cli.ping_servers", return_value=[fake_result]):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    main()
                    output = mock_stdout.getvalue()

        assert "Checking latency" in output
        for name in DNS_PRESETS:
            assert name in output


class TestCLICurrentLatency:
    """Tests for 'dnx current --latency' command."""

    def test_current_latency_shows_results(self):
        """Verify --latency pings current servers and prints latency."""
        mock_backend = MagicMock()
        mock_backend.get_dns.return_value = ["8.8.8.8"]
        fake_result = PingResult(
            ip="8.8.8.8", reachable=True, avg_ms=12.0, loss_percent=0.0
        )

        with patch.object(sys, "argv", ["dnx", "current", "--latency"]):
            with patch("dnx.cli.get_backend", return_value=mock_backend):
                with patch("dnx.cli.ping_servers", return_value=[fake_result]):
                    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                        main()
                        output = mock_stdout.getvalue()

        assert "Latency" in output
        assert "8.8.8.8" in output


class TestCLIKeyboardInterrupt:
    """Tests for CLI KeyboardInterrupt handling."""

    def test_keyboard_interrupt_exits_130(self):
        """Verify KeyboardInterrupt during execution exits with code 130."""
        with patch.object(sys, "argv", ["dnx", "current"]):
            with patch("dnx.cli.get_backend", side_effect=KeyboardInterrupt):
                with patch("sys.stdout", new_callable=StringIO):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 130

    def test_dnx_error_exits_1(self):
        """Verify DNXError during execution exits with code 1."""
        with patch.object(sys, "argv", ["dnx", "current"]):
            with patch("dnx.cli.get_backend", side_effect=DNXError("boom")):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1


class TestCLICurrentEndToEnd:
    """End-to-end tests for 'dnx current' (no admin required)."""

    def test_current_end_to_end(self):
        """Run 'dnx current' with real backend -- reads DNS without admin."""
        with patch.object(sys, "argv", ["dnx", "current"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()

        assert "Current DNS servers" in output or "No DNS servers" in output


class TestCLIErrorHandling:
    """Tests for CLI error handling."""

    def test_no_command_shows_help(self):
        with patch.object(sys, "argv", ["dnx"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2

    def test_unknown_command_fails(self):
        with patch.object(sys, "argv", ["dnx", "unknown"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2
