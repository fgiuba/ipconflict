"""Parsing of subnet definitions and detection of the overlapping ones.

The CLI usually checks a handful of subnets, so its run time is mostly interpreter startup: this
module imports nothing heavy. netaddr, which defines the accepted syntax and provides the ``IPSet``
objects of the public API, is imported only when one of them is actually needed.
"""

from __future__ import annotations

import gc
import os
import sys
from _socket import AF_INET, AF_INET6, has_ipv6, inet_ntop, inet_pton
from heapq import heappop, heappush
from itertools import repeat

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

    from netaddr import IPSet

Conflict = tuple[str, str, "IPSet"]
"""A conflict: (earlier subnet, later subnet, overlapping addresses)."""


class InvalidSubnetError(ValueError):
    """A subnet definition is neither a CIDR, a single address nor a ``start-end`` range."""

    def __init__(self, subnet: str) -> None:
        super().__init__(f"invalid subnet format {subnet}")
        self.subnet = subnet


# Parsing
#
# netaddr defines which definitions are valid. It reads addresses with the C library's inet_pton
# (the very function imported above), reads prefix lengths with int() and rejects IPv4 octets with
# leading zeros. The fast path below handles the common formats with the same functions and hands
# everything else, valid or not, to netaddr. It is turned off where netaddr does not rely on
# inet_pton (IPv4 on Windows and Cygwin, IPv6 on Python builds without IPv6 support) and for IPv4
# when the C library accepts leading zeros.


def _inet_pton_rejects_leading_zeros() -> bool:
    for address in ("01.2.3.4", "1.2.3.04"):
        try:
            inet_pton(AF_INET, address)
        except OSError:
            continue
        return False
    return True


_FAST_IPV4 = sys.platform not in ("win32", "cygwin") and _inet_pton_rejects_leading_zeros()
_FAST_IPV6 = has_ipv6
_PREFIXLEN4 = {str(prefixlen): prefixlen for prefixlen in range(33)}
_PREFIXLEN6 = {str(prefixlen): prefixlen for prefixlen in range(129)}
_HOSTMASK4 = [(1 << (32 - prefixlen)) - 1 for prefixlen in range(33)]
_HOSTMASK6 = [(1 << (128 - prefixlen)) - 1 for prefixlen in range(129)]
_from_bytes = int.from_bytes


def _parse_block(subnet: str) -> tuple[int, int, int]:
    """Return ``(ip_version, first, last)`` of the contiguous address block ``subnet`` covers."""
    try:
        if "-" in subnet:
            start, _, end = subnet.partition("-")
            if ":" in start:
                if _FAST_IPV6:
                    first = _from_bytes(inet_pton(AF_INET6, start))
                    last = _from_bytes(inet_pton(AF_INET6, end))
                    if first <= last:
                        return 6, first, last
            elif _FAST_IPV4:
                first = _from_bytes(inet_pton(AF_INET, start))
                last = _from_bytes(inet_pton(AF_INET, end))
                if first <= last:
                    return 4, first, last
        else:
            address, slash, prefixlen = subnet.partition("/")
            if ":" in address:
                if _FAST_IPV6:
                    value = _from_bytes(inet_pton(AF_INET6, address))
                    hostmask = _HOSTMASK6[_PREFIXLEN6[prefixlen]] if slash else 0
                    return 6, value & ~hostmask, value | hostmask
            elif _FAST_IPV4:
                value = _from_bytes(inet_pton(AF_INET, address))
                hostmask = _HOSTMASK4[_PREFIXLEN4[prefixlen]] if slash else 0
                return 4, value & ~hostmask, value | hostmask
    except Exception:  # not one of the common formats: netaddr has the final word
        pass
    return _parse_block_netaddr(subnet)


def _parse_block_netaddr(subnet: str) -> tuple[int, int, int]:
    import netaddr  # deferred, see the module docstring

    try:
        network = netaddr.IPNetwork(subnet)
        return network.version, network.first, network.last
    except (netaddr.AddrFormatError, ValueError):
        pass
    try:
        start, end = subnet.split("-")
        address_range = netaddr.IPRange(start, end)
    except (netaddr.AddrFormatError, ValueError):
        raise InvalidSubnetError(subnet) from None
    return address_range.version, address_range.first, address_range.last


def parse_subnet_data(data: str) -> list[str]:
    return [line for raw in data.splitlines() if (line := raw.strip()) and line[0] != "#"]


def parse_stdin_data() -> list[str]:
    return sys.stdin.read().split()


def parse_subnet_file(path: str) -> list[str]:
    if os.path.isfile(path):
        with open(path) as data:
            return parse_subnet_data(data.read())
    print("warning: invalid subnets file")
    return []


# Conflict detection


class _Conflicts:
    """The overlapping pairs among some subnet definitions, as plain integers.

    Iterating yields ``(earlier, later)`` input positions, ordered by the later position and then
    by the earlier one. Hot loops can decode ``pairs`` themselves: each one is
    ``later << bits | earlier``, which avoids building a tuple per pair.
    """

    __slots__ = ("_firsts", "_lasts", "_versions", "bits", "pairs")

    def __init__(
        self, bits: int, versions: bytearray, firsts: list[int], lasts: list[int], pairs: list[int]
    ) -> None:
        self.bits = bits
        self.pairs = pairs
        self._versions = versions
        self._firsts = firsts
        self._lasts = lasts

    def __len__(self) -> int:
        return len(self.pairs)

    def __iter__(self) -> Iterator[tuple[int, int]]:
        pairs, bits = self.pairs, self.bits
        return zip(map(((1 << bits) - 1).__and__, pairs), map(bits.__rrshift__, pairs), strict=True)

    def overlap(self, earlier: int, later: int) -> tuple[int, int, int]:
        """Return ``(ip_version, first, last)`` of the addresses two conflicting subnets share."""
        firsts, lasts = self._firsts, self._lasts
        return (
            self._versions[later],
            max(firsts[earlier], firsts[later]),
            min(lasts[earlier], lasts[later]),
        )


def _find_conflicts(subnets: Sequence[str]) -> _Conflicts:
    """Find every pair of overlapping definitions in O(n log n + k) time.

    Each definition covers one contiguous block of addresses. The blocks of each IP version are
    sorted by first address and swept once, keeping the blocks that are still open in a min-heap
    keyed by last address: every block still open when a new one starts overlaps it.

    Blocks are handled as single integers, much faster than tuples: ``first << bits | index`` to
    sort them, ``last << bits | index`` in the heap and ``later << bits | earlier`` for the pairs.
    """
    count = len(subnets)
    bits = max(count.bit_length(), 1)
    mask = (1 << bits) - 1
    versions = bytearray(count)
    firsts = [0] * count
    lasts = [0] * count
    keys: dict[int, list[int]] = {4: [], 6: []}
    for index, subnet in enumerate(subnets):  # in input order, to report the first invalid one
        version, first, last = _parse_block(subnet)
        versions[index] = version
        firsts[index] = first
        lasts[index] = last
        keys[version].append(first << bits | index)

    pairs: list[int] = []
    add_pair = pairs.append
    for family in keys.values():  # IPv4 and IPv6 blocks never overlap
        family.sort()
        heap: list[int] = []
        max_last = -1
        for key in family:
            first = key >> bits
            index = key & mask
            last = lasts[index]
            if first > max_last:  # every block seen so far ended before this one: start afresh
                heap = [last << bits | index]
                max_last = last
                continue
            bound = first << bits
            while heap[0] < bound:  # drop the blocks that ended before this one starts
                heappop(heap)
            for entry in heap:
                other = entry & mask
                add_pair(index << bits | other if index > other else other << bits | index)
            heappush(heap, last << bits | index)
            if last > max_last:
                max_last = last
    pairs.sort()
    return _Conflicts(bits, versions, firsts, lasts, pairs)


# Results


def _ip_set_factory() -> Callable[[int, int, int], IPSet]:
    from netaddr import IPAddress, IPNetwork, IPRange, IPSet  # deferred, see the module docstring

    def to_ip_set(version: int, first: int, last: int) -> IPSet:
        size = last - first + 1
        if not size & (size - 1) and not first & (size - 1):  # a single CIDR: 4x faster
            prefixlen = (32 if version == 4 else 128) + 1 - size.bit_length()
            return IPSet(IPNetwork((first, prefixlen), version))
        return IPSet(IPRange(IPAddress(first, version), IPAddress(last, version)))

    return to_ip_set


_OCTETS = [str(octet) for octet in range(256)]


def _address_lines(version: int, first: int, last: int) -> Iterator[str]:
    """Yield the addresses ``first``..``last`` one per line, as netaddr writes them, in chunks."""
    if version == 4:
        while first <= last:  # a /24 at a time: only the last octet changes
            end = min(last, first | 255)
            prefix = f"{first >> 24}.{first >> 16 & 255}.{first >> 8 & 255}."
            yield prefix + f"\n{prefix}".join(_OCTETS[first & 255 : (end & 255) + 1]) + "\n"
            first = end + 1
    elif _FAST_IPV6:
        while first <= last:
            end = min(last, first + 4095)
            packed = map(int.to_bytes, range(first, end + 1), repeat(16))
            yield "\n".join(map(inet_ntop, repeat(AF_INET6), packed)) + "\n"
            first = end + 1
    else:
        import netaddr  # deferred, see the module docstring

        for value in range(first, last + 1):
            yield f"{netaddr.IPAddress(value, 6)}\n"


# Public API


def get_ip_set(subnet: str) -> IPSet:
    return _ip_set_factory()(*_parse_block(subnet))


def check_conflicts(subnets: Sequence[str], quiet: bool = True) -> list[Conflict]:
    """Find every pair of overlapping subnet definitions.

    Each definition is a CIDR (host bits allowed), a single address or a ``start-end`` range,
    IPv4 or IPv6. Conflicts are ordered by the input position of the later definition, then of
    the earlier one. ``quiet`` is ignored; it is only kept for backward compatibility.

    Raises InvalidSubnetError for the first definition that cannot be parsed.
    """
    conflicts = _find_conflicts(subnets)
    if not conflicts:
        return []
    to_ip_set = _ip_set_factory()
    overlap = conflicts.overlap
    # With many conflicts, all the new IPSet objects make the cyclic garbage collector run full
    # collections over and over, up to half of the time spent here. They hold no reference
    # cycles, so it can safely be paused meanwhile.
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        return [
            (subnets[earlier], subnets[later], to_ip_set(*overlap(earlier, later)))
            for earlier, later in conflicts
        ]
    finally:
        if gc_was_enabled:
            gc.enable()
