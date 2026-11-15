import heapq
import os
import sys
from collections.abc import Sequence

from netaddr import IPAddress, IPNetwork, IPRange, IPSet
from netaddr.core import AddrFormatError

Conflict = tuple[str, str, IPSet]
"""A conflict: (earlier subnet, later subnet, overlapping addresses)."""


class InvalidSubnetError(ValueError):
    """A subnet definition is neither a CIDR, a single address nor a ``start-end`` range."""

    def __init__(self, subnet: str) -> None:
        super().__init__(f"invalid subnet format {subnet}")
        self.subnet = subnet


def _parse_block(subnet: str) -> tuple[int, int, int]:
    """Return ``(ip_version, first, last)`` of the contiguous address block ``subnet`` covers."""
    try:
        network = IPNetwork(subnet)
        return network.version, network.first, network.last
    except (AddrFormatError, ValueError):
        pass
    try:
        start, end = subnet.split("-")
        address_range = IPRange(start, end)
    except (AddrFormatError, ValueError):
        raise InvalidSubnetError(subnet) from None
    return address_range.version, address_range.first, address_range.last


def _block_to_ip_set(version: int, first: int, last: int) -> IPSet:
    return IPSet(IPRange(IPAddress(first, version), IPAddress(last, version)))


def get_ip_set(subnet: str) -> IPSet:
    return _block_to_ip_set(*_parse_block(subnet))


def parse_subnet_data(data: str) -> list[str]:
    subnets = []
    for line in data.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            subnets.append(line)
    return subnets


def parse_stdin_data() -> list[str]:
    return sys.stdin.read().split()


def parse_subnet_file(path: str) -> list[str]:
    if os.path.isfile(path):
        with open(path) as data:
            return parse_subnet_data(data.read())
    print("warning: invalid subnets file")
    return []


def check_conflicts(subnets: Sequence[str], quiet: bool = True) -> list[Conflict]:
    """Find every pair of overlapping subnet definitions.

    Each definition (CIDR, single address or ``start-end`` range) covers one contiguous block of
    addresses. Blocks are sorted by first address and swept once, keeping the blocks that are
    still open in a min-heap keyed by last address: every block still open when a new one
    starts overlaps it. This takes O(n log n + k) time for n definitions and k conflicts.

    Conflicts are ordered by the input position of the later definition, then of the earlier
    one. ``quiet`` is ignored; it is only kept for backward compatibility.
    """
    blocks = sorted((*_parse_block(subnet), idx) for idx, subnet in enumerate(subnets))
    overlaps: list[tuple[int, int, int, int, int]] = []  # (later, earlier, version, first, last)
    open_blocks: list[tuple[int, int]] = []  # min-heap of (last, idx)
    current_version = None
    for version, first, last, idx in blocks:
        if version != current_version:  # IPv4 and IPv6 blocks never overlap
            open_blocks, current_version = [], version
        while open_blocks and open_blocks[0][0] < first:
            heapq.heappop(open_blocks)
        for open_last, open_idx in open_blocks:
            later, earlier = max(idx, open_idx), min(idx, open_idx)
            overlaps.append((later, earlier, version, first, min(last, open_last)))
        heapq.heappush(open_blocks, (last, idx))
    overlaps.sort()
    return [
        (subnets[earlier], subnets[later], _block_to_ip_set(version, first, last))
        for later, earlier, version, first, last in overlaps
    ]
