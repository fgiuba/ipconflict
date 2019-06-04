# ipconflict

Check if two or more network subnets are overlapping.

## Install

`pip install ipconflict`

## Quick Start

* `ipconflict 10.0.0.0/22 10.0.1.0/24`
* `ipconflict 10.0.0.0/22 10.0.1.1-10.0.1.5`
* `ipconflict 172.16.0.0/22 172.16.1.0/24 172.16.3.0/27`

For printing the overlapping IPs add `-p` (or `--print-conflicts`) option:
* `ipconflict -p 10.0.0.0/24 10.0.0.100-10.0.0.105`

Subnets can be defined in a simple text file (one subnet per line):
* `ipconflict -f /path/to/my/subnets`

Other subnets can still be appended:
* `ipconflict -f /path/to/my/subnets 192.168.5.0/27 10.0.128.0/21`

## Subnet Definition

Subnet can be specified in several ways:

* CIDR notation `192.168.0.0/24`
* Single IP address `10.0.1.2`
* IP range `10.0.0.5-10.0.0.20`

The tools works both with IPv4 and IPv6.
