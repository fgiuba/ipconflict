# ipconflict

[![CI](https://github.com/fgiuba/ipconflict/actions/workflows/ci.yml/badge.svg)](https://github.com/fgiuba/ipconflict/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/ipconflict.svg)](https://pypi.org/project/ipconflict/)
[![Python versions](https://img.shields.io/pypi/pyversions/ipconflict.svg)](https://pypi.org/project/ipconflict/)
[![Downloads](https://pepy.tech/badge/ipconflict)](https://pepy.tech/project/ipconflict)

Check if two or more network subnets are overlapping.

## Install

Requires Python 3.11 or newer.

* `uv tool install ipconflict` (or run it once with `uvx ipconflict ...`)
* `pip install ipconflict`

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

## Exit Status

* `0`, one or more conflicts found
* `1`, no conflict found
* `2`, aborted or invalid input

## Development

The project is managed with [uv](https://docs.astral.sh/uv/), linted and formatted with
[Ruff](https://docs.astral.sh/ruff/) and type checked with [ty](https://docs.astral.sh/ty/).

```sh
uv sync                    # create .venv with runtime and dev dependencies
uv run pytest              # run the test suite
uv run ruff check          # lint
uv run ruff format         # format
uv run ty check            # type check
uv run ipconflict --help   # run the CLI from the source tree
```
