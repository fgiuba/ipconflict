"""Check for conflicts between network subnets."""

from __future__ import annotations

import argparse
import sys

from ipconflict.subnet import (
    InvalidSubnetError,
    _address_lines,
    _Conflicts,
    _find_conflicts,
    parse_stdin_data,
    parse_subnet_file,
)

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any, TextIO


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


_CHUNK = 65536


def _write_report(
    out: TextIO,
    subnets: Sequence[str],
    conflicts: _Conflicts,
    print_addresses: bool,
    ip_only: bool,
) -> None:
    if not conflicts:
        out.write("no conflict found\n")
        return
    if not print_addresses:  # build the lines in bulk, a chunk at a time to bound memory
        pairs, bits = conflicts.pairs, conflicts.bits
        mask = (1 << bits) - 1
        for start in range(0, len(pairs), _CHUNK):
            lines = [
                f"conflict found: {subnets[pair & mask]} <-> {subnets[pair >> bits]}\n"
                for pair in pairs[start : start + _CHUNK]
            ]
            out.write("".join(lines))
        return
    for earlier, later in conflicts:
        if not ip_only:
            out.write(f"conflict found: {subnets[earlier]} <-> {subnets[later]}\n")
        for chunk in _address_lines(*conflicts.overlap(earlier, later)):
            out.write(chunk)


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
        conflicts = _find_conflicts(subnets)
        _write_report(
            sys.stdout, subnets, conflicts, args.print_conflicts or args.ip_only, args.ip_only
        )
    except InvalidSubnetError as exc:
        print(f"error: {exc}")
        sys.exit(2)
    except KeyboardInterrupt:
        print("aborted\n")
        sys.exit(2)
    sys.exit(0 if conflicts else 1)


if __name__ == "__main__":
    main()
