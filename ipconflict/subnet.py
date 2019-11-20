import os
import sys

import radix
from netaddr import IPRange, IPSet
from netaddr.core import AddrFormatError
from tqdm import tqdm


def get_ip_set(subnet):
    try:
        return IPSet([subnet])
    except AddrFormatError:
        try:
            start, end = subnet.split('-')
            return IPSet(IPRange(start, end))
        except (AddrFormatError, ValueError):
            print(u'error: invalid subnet format {}'.format(subnet))
            sys.exit(1)


def parse_subnet_data(data):
    subnets = []
    lines = data.splitlines()
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            subnets.append(line)
    return subnets


def parse_stdin_data():
    data = sys.stdin.read()
    return [subnet.strip() for subnet in data.split() if subnet]


def parse_subnet_file(path):
    if os.path.isfile(path):
        with open(path) as data:
            return parse_subnet_data(data.read())
    else:
        print(u'warning: invalid subnets file')
        return []


def check_conflicts(subnets, quiet=True):
    conflicts = []
    rtree = radix.Radix()
    for idx, subnet_a in tqdm(enumerate(subnets), unit='subnet', total=len(subnets), disable=quiet):
        set_a = get_ip_set(subnet_a)
        matched = False
        for cidr in set_a.iter_cidrs():
            cidr = str(cidr)
            if (rtree.search_covered(cidr) or rtree.search_covering(cidr)) and not matched:
                for subnet_b in subnets[:idx]:
                    overlapping_ips = set_a & get_ip_set(subnet_b)
                    if overlapping_ips:
                        conflicts.append((subnet_b, subnet_a, overlapping_ips))
                matched = True
            rtree.add(cidr)
    return conflicts
