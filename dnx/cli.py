# -*- coding: utf-8 -*-
"""
Command-line interface for dnx.

This module provides the main CLI entry point for the dnx DNS changer tool.
It supports listing presets, showing current DNS, setting DNS servers,
resetting to defaults, and pinging DNS servers for latency testing.
"""
import sys
import argparse
from .dns import get_backend, require_admin, validate_ips
from .params import DNX_VERSION, DNS_PRESETS
from .exceptions import DNXError
from .ping import ping_servers, verify_servers, format_ping_results, format_ping_result


def main():
    """
    Execute the dnx command-line interface.

    Parse command-line arguments and execute the appropriate DNS operation.
    Handle errors gracefully and provide user-friendly output.

    Commands:
        list: List predefined DNS presets.
        current: Show current DNS servers.
        set: Set DNS servers (requires admin).
        reset: Reset DNS to system default (requires admin).
        ping: Ping DNS servers to check latency.
    """
    parser = argparse.ArgumentParser(
        prog="dnx",
        description="dnx - Minimal cross-platform DNS changer",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {DNX_VERSION}",
    )

    parser.add_argument(
        "--iface",
        help="Network interface override (skip auto-detection)",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    list_p = sub.add_parser("list", help="List predefined DNS servers")
    list_p.add_argument(
        "--latency",
        action="store_true",
        help="Show latency for all presets",
    )

    current_p = sub.add_parser("current", help="Show current DNS servers")
    current_p.add_argument(
        "--latency",
        action="store_true",
        help="Show latency for current DNS servers",
    )

    sub.add_parser("reset", help="Reset DNS to system default")

    set_p = sub.add_parser("set", help="Set DNS servers")
    set_p.add_argument(
        "servers",
        nargs="+",
        help="Preset name or IP addresses",
    )
    set_p.add_argument(
        "--verify",
        action="store_true",
        help="Verify servers are reachable before setting",
    )
    set_p.add_argument(
        "--no-latency",
        action="store_true",
        help="Skip latency check after setting DNS",
    )

    ping_p = sub.add_parser("ping", help="Ping DNS servers to check latency")
    ping_p.add_argument(
        "servers",
        nargs="+",
        help="Preset name or IP addresses to ping",
    )
    ping_p.add_argument(
        "-c", "--count",
        type=int,
        default=3,
        help="Number of ping packets (default: 3)",
    )

    args = parser.parse_args()

    try:
        if args.cmd == "list":
            _handle_list(args)
            return

        if args.cmd == "ping":
            _handle_ping(args)
            return

        backend = get_backend(args.iface)

        if args.cmd == "current":
            _handle_current(backend, args)

        elif args.cmd == "set":
            _handle_set(backend, args)

        elif args.cmd == "reset":
            _handle_reset(backend)

    except DNXError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)


def _handle_list(args):
    """
    Handle the 'list' command.

    Args:
        args: Parsed command-line arguments.
    """
    if args.latency:
        print("Checking latency for all presets...\n")
        for name, servers in DNS_PRESETS.items():
            print(f"{name}:")
            results = ping_servers(servers, count=2)
            for r in results:
                print(f"  {format_ping_result(r)}")
            print()
    else:
        for name, servers in DNS_PRESETS.items():
            print(f"{name}: {', '.join(servers)}")


def _handle_ping(args):
    """
    Handle the 'ping' command.

    Args:
        args: Parsed command-line arguments.
    """
    if len(args.servers) == 1 and args.servers[0] in DNS_PRESETS:
        servers = DNS_PRESETS[args.servers[0]]
    else:
        servers = args.servers

    validate_ips(servers)
    print(f"Pinging {len(servers)} server(s)...\n")
    results = ping_servers(servers, count=args.count)
    print(format_ping_results(results))


def _handle_current(backend, args):
    """
    Handle the 'current' command.

    Args:
        backend: DNS backend instance.
        args: Parsed command-line arguments.
    """
    servers = backend.get_dns()
    if not servers:
        print("No DNS servers configured")
    else:
        print("Current DNS servers:")
        for s in servers:
            print(f"  {s}")

        if args.latency:
            print("\nLatency:")
            results = ping_servers(servers, count=2)
            for r in results:
                print(f"  {format_ping_result(r)}")


def _handle_set(backend, args):
    """
    Handle the 'set' command.

    Args:
        backend: DNS backend instance.
        args: Parsed command-line arguments.
    """
    require_admin()

    if len(args.servers) == 1 and args.servers[0] in DNS_PRESETS:
        preset_name = args.servers[0]
        servers = DNS_PRESETS[preset_name]
        print(f"Using preset '{preset_name}': {', '.join(servers)}")
    else:
        servers = args.servers

    validate_ips(servers)

    if args.verify:
        print(f"\nVerifying {len(servers)} server(s)...")
        all_ok, results = verify_servers(servers)
        print(format_ping_results(results))

        if not all_ok:
            unreachable = [r.ip for r in results if not r.reachable]
            print(
                f"\nWarning: {len(unreachable)} server(s) unreachable: "
                f"{', '.join(unreachable)}",
                file=sys.stderr,
            )
            response = input("Continue anyway? [y/N] ").strip().lower()
            if response != "y":
                print("Aborted.")
                sys.exit(1)
        print()

    old_servers = backend.get_dns()
    backend.set_dns(servers)
    print("DNS updated successfully!")

    if not args.no_latency:
        print("\nLatency comparison:")
        if old_servers:
            print("  Before:")
            old_results = ping_servers(old_servers, count=2)
            for r in old_results:
                print(f"    {format_ping_result(r)}")

        print("  After:")
        new_results = ping_servers(servers, count=2)
        for r in new_results:
            print(f"    {format_ping_result(r)}")


def _handle_reset(backend):
    """
    Handle the 'reset' command.

    Args:
        backend: DNS backend instance.
    """
    require_admin()
    backend.reset_dns()
    print("DNS reset to system default")
