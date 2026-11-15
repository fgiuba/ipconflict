"""Check for conflicts between network subnets."""

from __future__ import annotations

import argparse
import sys

from ipconflict.subnet import (
    Conflict,
    InvalidSubnetError,
    check_conflicts,
    parse_stdin_data,
    parse_subnet_file,
)

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any


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


def _version() -> str:
    # importlib.metadata takes longer to import than a typical run of the tool: only on demand.
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("ipconflict")
    except PackageNotFoundError:  # running from a source tree that is not installed
        return "unknown"


def __getattr__(name: str) -> str:
    if name == "__version__":
        return _version()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class _VersionAction(argparse.Action):
    """argparse's "version" action, except that the version is read only when requested."""

    def __init__(self, option_strings: Sequence[str], dest: str, help: str | None = None) -> None:
        super().__init__(
            option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, nargs=0, help=help
        )

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        print(f"ipconflict {_version()}")
        parser.exit()


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
        "-o",
        "--ip-only",
        action="store_true",
        help="print only the overlapping IP addresses (implies -p)",
    )
    parser.add_argument(
        "-p", "--print-conflicts", action="store_true", help="print overlapping IP addresses"
    )
    # There is no progress bar any more: -q is accepted (and hidden) only so that existing
    # scripts keep working.
    parser.add_argument("-q", "--quiet", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("-V", "--version", action=_VersionAction, help="print ipconflict version")

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
        conflicts = check_conflicts(subnets)
        print_results(conflicts, args.print_conflicts or args.ip_only, args.ip_only)
    except InvalidSubnetError as exc:
        print(f"error: {exc}")
        sys.exit(2)
    except KeyboardInterrupt:
        print("aborted\n")
        sys.exit(2)
    sys.exit(0 if conflicts else 1)


if __name__ == "__main__":
    main()
