# -*- coding: utf-8 -*-
"""dnx CLI."""
import argparse
from .dns import get_backend, require_admin, validate_ips,
from .params import DNS_PRESETS


def main():
    parser = argparse.ArgumentParser(
        prog="dnx",
        description="dnx - Minimal DNS changer",
    )

    parser.add_argument(
        "--iface",
        help="Network interface override (skip auto-detection)",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List predefined DNS servers")
    sub.add_parser("current", help="Show current DNS servers")
    sub.add_parser("reset", help="Reset DNS to system default")

    set_p = sub.add_parser("set", help="Set DNS servers")
    set_p.add_argument(
        "servers",
        nargs="+",
        help="Preset name or IP addresses",
    )

    args = parser.parse_args()
    backend = get_backend(args.iface)

    if args.cmd == "list":
        for name, servers in DNS_PRESETS.items():
            print(f"{name}: {', '.join(servers)}")

    elif args.cmd == "current":
        servers = backend.get_dns()
        print("\n".join(servers) if servers else "No DNS servers configured")

    elif args.cmd == "set":
        require_admin()

        if len(args.servers) == 1 and args.servers[0] in DNS_PRESETS:
            servers = DNS_PRESETS[args.servers[0]]
        else:
            servers = args.servers

        validate_ips(servers)
        backend.set_dns(servers)
        print("DNS updated")

    elif args.cmd == "reset":
        require_admin()
        backend.reset_dns()
        print("DNS reset")


if __name__ == "__main__":
    main()

