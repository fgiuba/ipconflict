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
  enables `python -m ipconflict`). It never builds netaddr objects: it calls `_find_conflicts`
  and `_write_report` formats the integer results directly. `__version__` and `-V` read the
  installed metadata lazily (`_version`): the only source of truth is `pyproject.toml`.
- `ipconflict/subnet.py` — parsing and conflict detection; the only runtime dependency is
  `netaddr`, which defines the accepted syntax.
  - `_parse_block` turns a definition into `(ip_version, first, last)`: every accepted format
    is one contiguous block. Common formats go through a fast path built on the same
    `_socket.inet_pton` netaddr uses; anything else (netmasks, odd prefixes, invalid input,
    Windows IPv4) falls back to `_parse_block_netaddr`, the reference. Invalid input raises
    `InvalidSubnetError` (a `ValueError`); the CLI turns it into exit status 2.
  - `_find_conflicts` sorts the blocks and sweeps them once with a min-heap of the still-open
    blocks, per IP version: O(n log n + k). Blocks, heap entries and pairs are single ints
    (`value << bits | index`), not tuples. Do not reintroduce pairwise comparisons:
    `tests/test_overlap.py::ScalingTest` guards the case that used to be quadratic.
  - `check_conflicts` (library API) turns pairs into `IPSet`s via `_ip_set_factory` (a single
    CIDR is built directly) with the garbage collector paused; `_address_lines` prints `-p`
    addresses exactly as `str(IPAddress)` would. `quiet` and `-q` are backward-compatible no-ops.
- Startup is most of a typical run, so `ipconflict` must not import `netaddr`,
  `importlib.metadata`, `typing` or `socket` at module level: import them where needed, and put
  type-only imports under the `TYPE_CHECKING = False` idiom (ty understands it).
  `tests/test_fast_paths.py` checks this and that every fast path matches netaddr.
- Performance work: measure first. On 3.11–3.15, plain loops beat clever variants here
  (`itertools`-vectorized sweep, float sort keys, `zip` iteration in hot output loops).
- Build backend is `uv_build` with a flat layout (`[tool.uv.build-backend] module-root = ""`),
  not `src/`.

## Contracts to preserve

- `check_conflicts` returns `list[tuple[earlier, later, IPSet]]` ordered by the later subnet's
  input position, then the earlier one's (the sweep sorts its pairs back into this order); the
  original strings are returned verbatim. Tests assert exact lists, and
  `BruteForceComparisonTest` checks random IPv4/IPv6 inputs against a pairwise `IPSet` oracle
  (`SweepTest` compares the sweep alone with a pairwise check, on larger inputs).
- The CLI prints exactly what printing the results of `check_conflicts` would, although it never
  builds them: `tests/test_cli.py::test_output_matches_the_library` checks it on random inputs.
- The accepted syntax and the `-p` address format are netaddr's: a fast path may only take a
  shortcut to netaddr's result, never change what is accepted or printed. Invalid input must
  only ever raise `InvalidSubnetError`: anything else would crash the CLI with exit status 1.
- Exit codes are deliberately grep-like and documented in the README and `--help` epilog:
  `0` conflicts found, `1` no conflict, `2` aborted/invalid input.

## Repository conventions

- Never add `Co-Authored-By: Claude` trailers or "Generated with Claude Code" lines to commits
  or pull requests.
- Default branch is `master`.
