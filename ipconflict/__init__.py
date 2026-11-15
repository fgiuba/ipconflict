"""Check for conflicts between network subnets."""

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

from ipconflict.subnet import Conflict, check_conflicts, parse_stdin_data, parse_subnet_file

try:
    __version__ = _dist_version("ipconflict")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "unknown"


epilog = """examples:
  ipconflict 10.0.0.0/24 10.0.0.1/16
  ipconflict 10.0.0.0/24 10.0.0.20-10.0.0.25
  ipconflict -f my-subnets.txt
  ipconflict -f my-subnets.txt 192.168.0.0/24

exit status:
  0: one or more conflicts found
  1: no conflict found
  2: aborted or invalid input
"""


def print_results(conflicts: Sequence[Conflict], print_conflicts: bool, ip_only: bool) -> None:
    for subnet_a, subnet_b, overlapping_ips in conflicts:
        if not ip_only:
            print(f"conflict found: {subnet_a} <-> {subnet_b}")
        if print_conflicts:
            for ip in overlapping_ips:
                print(ip)
    if not conflicts:
        print("no conflict found")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Check for conflicts between subnets.",
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("subnets", nargs="*", help="list of subnets to be checked")
    parser.add_argument(
        "-f", "--from-file", default="", help="load subnet definitions from file (one per line)"
    )
    parser.add_argument(
        "-i", "--from-stdin", action="store_true", help="load subnet definitions from stdin"
    )
    parser.add_argument(
        "-o", "--ip-only", action="store_true", help="print only the overlapping IP addresses"
    )
    parser.add_argument(
        "-p", "--print-conflicts", action="store_true", help="print overlapping IP addresses"
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="hide progress status")
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"ipconflict {__version__}",
        help="print ipconflict version",
    )

    args = parser.parse_args(argv)

    subnets: list[str] = args.subnets
    if args.from_stdin:
        subnets += parse_stdin_data()
    if args.from_file:
        subnets += parse_subnet_file(args.from_file)
    if len(subnets) < 2:
        print("must specify at least 2 subnets")
        sys.exit(2)
    try:
        conflicts = check_conflicts(subnets, args.quiet)
        print_results(conflicts, args.print_conflicts, args.ip_only)
    except KeyboardInterrupt:
        print("aborted\n")
        sys.exit(2)
    sys.exit(0 if conflicts else 1)


if __name__ == "__main__":
    main()
