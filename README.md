# ipconflict

[![Downloads](https://pepy.tech/badge/ipconflict)](https://pepy.tech/project/ipconflict)
[![ipconflict](https://img.shields.io/badge/ipconflict-0.3.5-green.svg)](https://pypi.org/project/ipconflict/)
[![Python version](https://img.shields.io/badge/python-2.6%20%7C%202.7%20%7C%203.4%20%7C%203.5%20%7C%203.6%20%7C%203.7-blue.svg)](https://www.python.org/downloads/release/python-370/)

Check if two or more network subnets are overlapping.

## Install

`pip install ipconflict`

## Quick Start

* `ipconflict 10.0.0.0/22 10.0.1.0/24`
* `ipconflict 10.0.0.0/22 10.0.1.1-10.0.1.5`
* `ipconflict 172.16.0.0/22 172.16.1.0/24 172.16.3.0/27`

#### Print overlapping IP addresses

* `ipconflict -p 10.0.0.0/24 10.0.0.100-10.0.0.105`

#### Subnets from file

* `ipconflict -f /path/to/subnets`

#### Subnets from stdin

* `echo "10.0.1.0/24 10.0.0.0/22" | ipconflict -i`

#### Subnets from everywhere

* `echo "10.0.0.0/16" | ipconflict -i -f /path/to/subnets 192.168.0.0/24 172.25.1.17`

## Subnet Definition

A subnet can be specified in several ways:

* CIDR notation `192.168.0.0/24`
* Single IP address `10.0.1.2`
* IP range `10.0.0.5-10.0.0.20`

This tool works both with IPv4 and IPv6.
