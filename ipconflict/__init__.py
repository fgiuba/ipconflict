#!/usr/bin/env python

import argparse
import os
import sys

from netaddr import IPRange, IPSet
from netaddr.core import AddrFormatError


epilog = """examples:
\tipconflict 10.0.0.0/24 10.0.0.1/16
\tipconflict 10.0.0.0/24 10.0.0.20-10.0.0.25
\tipconflict -f my-subnets.txt
\tipconflict -f my-subnets.txt 192.168.0.0/24
"""


def get_ip_set(subnet):
    try:
        return IPSet([subnet])
    except AddrFormatError:
        try:
            start, end = subnet.split('-')
            return IPSet(IPRange(start, end))
        except (AddrFormatError, ValueError):
            print(u'invalid subnet format: {}'.format(subnet))
            sys.exit(1)


def check_conflicts(subnets):
    conflicts = []
    for idx, subnet_a in enumerate(subnets):
        for subnet_b in subnets[idx+1:]:
            overlapping_ips = get_ip_set(subnet_a) & get_ip_set(subnet_b)
            if overlapping_ips:
                conflicts.append((subnet_a, subnet_b, overlapping_ips))
    return conflicts


def print_results(conflicts, print_conflicts):
    for subnet_a, subnet_b, overlapping_ips in conflicts:
        print(u'conflict found: {} <-> {}'.format(subnet_a, subnet_b))
        if print_conflicts:
            for ip in overlapping_ips:
                print(ip)
    if not conflicts:
        print(u'no conflict found')


def main():

    parser = argparse.ArgumentParser(
        description=u'Check for conflicts between subnets.',
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('subnets', nargs='*',
                        help='list of subnets to be checked')
    parser.add_argument('-f', '--from-file', default='',
                        help='load subnet definitions from file (one per line)')
    parser.add_argument('-p', '--print-conflicts', action='store_true',
                        help='print overlapping IPs')

    args = parser.parse_args(sys.argv[1:])
    if not args:
        parser.print_usage()
        sys.exit(0)

    subnets = args.subnets
    subnet_file = args.from_file
    if subnet_file:
        if os.path.isfile(subnet_file):
            subnets += open(subnet_file).read().splitlines()
        else:
            print(u'Error: invalid subnet file')
    conflicts = check_conflicts(subnets)
    print_results(conflicts, args.print_conflicts)


if __name__ == '__main__':
    main()
