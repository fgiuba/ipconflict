# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`ipconflict` is a small CLI (published on PyPI) that reports overlaps between IPv4/IPv6 subnets
given as CIDR (host bits allowed, e.g. `10.0.0.1/16`), single addresses, or `start-end` ranges,
read from argv, a file (`-f`, one per line, `#` comments), and/or stdin (`-i`, whitespace-separated).

## Commands

Tooling is the Astral suite: uv (env, lock, build), Ruff (lint + format), ty (type check).

```sh
uv sync                                   # .venv with runtime + dev dependency group
uv run pytest                             # all tests
uv run pytest tests/test_overlap.py::OverlapTest::test_two_subnets   # single test
uv run --python 3.11 pytest               # test against a specific interpreter
uv run ruff check --fix && uv run ruff format
uv run ty check
uv run ipconflict -p 10.0.0.0/24 10.0.0.5-10.0.0.6      # or: uv run python -m ipconflict ...
uv build                                  # sdist + wheel (uv_build backend)
uv version --bump minor                   # bump the version in pyproject.toml
```

CI (`.github/workflows/ci.yml`) runs `uv sync --locked`, so run `uv lock` after touching
dependencies and commit `uv.lock`. The test matrix is CPython 3.11–3.15; keep the
`requires-python` floor, the classifiers and the matrix in sync.

## Architecture

- `ipconflict/__init__.py` — the CLI (`main`, entry point `ipconflict:main`; `__main__.py`
  enables `python -m ipconflict`). `__version__` is read from installed metadata: the only
  source of truth for the version is `pyproject.toml`.
- `ipconflict/subnet.py` — input parsing and `check_conflicts`, the core. The only runtime
  dependency is `netaddr`.
  - `_parse_block` turns a definition into `(ip_version, first, last)`: every accepted format
    (CIDR via `IPNetwork`, then `a-b` via `IPRange`) is one contiguous block of addresses.
    Invalid input raises `InvalidSubnetError` (a `ValueError`); the CLI catches it and exits 2.
    Library code never calls `sys.exit`.
  - `check_conflicts` sorts the blocks and sweeps them once with a min-heap of the blocks still
    open (keyed by last address), separately per IP version: O(n log n + k). The overlap of a
    pair is always a single range, turned into an `IPSet` only for the result. Do not
    reintroduce pairwise comparison of all subnets: `tests/test_overlap.py::ScalingTest`
    guards the 1-supernet-plus-20k-subnets case, which was quadratic before.
  - Its `quiet` parameter and the CLI's `-q` are no-ops kept for backward compatibility.
- Build backend is `uv_build` with a flat layout (`[tool.uv.build-backend] module-root = ""`),
  not `src/`.

## Contracts to preserve

- `check_conflicts` returns `list[tuple[earlier, later, IPSet]]` ordered by the later subnet's
  input position, then the earlier one's (the sweep sorts its pairs back into this order); the
  original strings are returned verbatim. Tests assert exact lists, and
  `BruteForceComparisonTest` checks random IPv4/IPv6 inputs against a pairwise `IPSet` oracle.
- Exit codes are deliberately grep-like and documented in the README and `--help` epilog:
  `0` conflicts found, `1` no conflict, `2` aborted/invalid input.

## Repository conventions

- Never add `Co-Authored-By: Claude` trailers or "Generated with Claude Code" lines to commits
  or pull requests.
- Default branch is `master`.
