import os
import sys
from collections.abc import Sequence

import radix
from netaddr import IPRange, IPSet
from netaddr.core import AddrFormatError
from tqdm import tqdm

Conflict = tuple[str, str, IPSet]
"""A conflict: (earlier subnet, later subnet, overlapping addresses)."""


class InvalidSubnetError(ValueError):
    """A subnet definition is neither a CIDR, a single address nor a ``start-end`` range."""

    def __init__(self, subnet: str) -> None:
        super().__init__(f"invalid subnet format {subnet}")
        self.subnet = subnet


def get_ip_set(subnet: str) -> IPSet:
    try:
        return IPSet([subnet])
    except (AddrFormatError, ValueError):
        try:
            start, end = subnet.split("-")
            return IPSet(IPRange(start, end))
        except (AddrFormatError, ValueError):
            raise InvalidSubnetError(subnet) from None


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
    conflicts: list[Conflict] = []
    rtree = radix.Radix()
    for idx, subnet_a in tqdm(enumerate(subnets), unit="subnet", total=len(subnets), disable=quiet):
        set_a = get_ip_set(subnet_a)
        matched = False
        for cidr in set_a.iter_cidrs():
            cidr = str(cidr)
            if not matched and (rtree.search_covered(cidr) or rtree.search_covering(cidr)):
                for subnet_b in subnets[:idx]:
                    overlapping_ips = set_a & get_ip_set(subnet_b)
                    if overlapping_ips:
                        conflicts.append((subnet_b, subnet_a, overlapping_ips))
                matched = True
            rtree.add(cidr)
    return conflicts
