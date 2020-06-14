#!/usr/bin/env python

import argparse
import sys

from ipconflict.subnet import check_conflicts, parse_stdin_data, parse_subnet_file


version = u'0.5.0'


epilog = u"""examples:
  ipconflict 10.0.0.0/24 10.0.0.1/16
  ipconflict 10.0.0.0/24 10.0.0.20-10.0.0.25
  ipconflict -f my-subnets.txt
  ipconflict -f my-subnets.txt 192.168.0.0/24

exit status:
  0: one or more conflicts found
  1: no conflict found
  2: aborted or invalid input
"""


def print_results(conflicts, print_conflicts, ip_only):
    for subnet_a, subnet_b, overlapping_ips in conflicts:
        if not ip_only:
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
    parser.add_argument('-i', '--from-stdin', action='store_true',
                        help=u'load subnet definitions from stdin')
    parser.add_argument('-o', '--ip-only', action='store_true',
                        help=u'print only the overlapping IP addresses')
    parser.add_argument('-p', '--print-conflicts', action='store_true',
                        help=u'print overlapping IP addresses')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help=u'show progress status')
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
    if args.from_stdin:
        subnets += parse_stdin_data()
    subnet_file = args.from_file
    if subnet_file:
        subnets += parse_subnet_file(subnet_file)
    if len(subnets) < 2:
        print('must specify at least 2 subnets')
        sys.exit(2)
    try:
        conflicts = check_conflicts(subnets, args.quiet)
        print_results(conflicts, args.print_conflicts, args.ip_only)
    except KeyboardInterrupt:
        print('aborted\n')
        sys.exit(2)
    else:
        if conflicts:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()
