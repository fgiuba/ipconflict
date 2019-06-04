#!/usr/bin/env python

import argparse
import sys

from ipconflict.subnet import check_conflicts, parse_subnet_file


version = u'0.2.0'


epilog = u"""examples:
\tipconflict 10.0.0.0/24 10.0.0.1/16
\tipconflict 10.0.0.0/24 10.0.0.20-10.0.0.25
\tipconflict -f my-subnets.txt
\tipconflict -f my-subnets.txt 192.168.0.0/24
"""


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
                        help=u'list of subnets to be checked')
    parser.add_argument('-f', '--from-file', default='',
                        help=u'load subnet definitions from file (one per line)')
    parser.add_argument('-p', '--print-conflicts', action='store_true',
                        help=u'print overlapping IPs')
    parser.add_argument('-V', '--version', action='store_true',
                        help=u'print ipconflict version')

    args = parser.parse_args(sys.argv[1:])
    if not args:
        parser.print_usage()
        sys.exit(0)

    if args.version:
        print(u'ipconflict {}'.format(version))
        sys.exit(0)

    subnets = args.subnets
    subnet_file = args.from_file
    if subnet_file:
        subnets += parse_subnet_file(subnet_file)
    conflicts = check_conflicts(subnets)
    print_results(conflicts, args.print_conflicts)


if __name__ == '__main__':
    main()
