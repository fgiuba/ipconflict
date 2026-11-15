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
uv run ipconflict -q -p 10.0.0.0/24 10.0.0.5-10.0.0.6   # or: uv run python -m ipconflict ...
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
- `ipconflict/subnet.py` — input parsing and `check_conflicts(subnets, quiet)`, the core.
  - `get_ip_set` parses one definition into a `netaddr.IPSet` (CIDR/IP first, then `a-b` range).
    On invalid input it prints an error and calls `sys.exit(2)` itself, i.e. library code exits.
  - `check_conflicts` inserts each subnet's CIDR blocks into a `py-radix` tree; when a subnet
    hits an existing prefix (covered or covering), it intersects it with **every** earlier
    subnet, re-parsing each one. A `tqdm` progress bar is shown unless `quiet`.
- Build backend is `uv_build` with a flat layout (`[tool.uv.build-backend] module-root = ""`),
  not `src/`.

## Contracts to preserve

- `check_conflicts` returns `list[tuple[earlier, later, IPSet]]` ordered by the later subnet's
  input position, then the earlier one's; the original strings are returned verbatim. Tests
  assert exact lists, so ordering and `IPSet` contents are part of the API.
- Exit codes are deliberately grep-like and documented in the README and `--help` epilog:
  `0` conflicts found, `1` no conflict, `2` aborted/invalid input.

## Repository conventions

- Never add `Co-Authored-By: Claude` trailers or "Generated with Claude Code" lines to commits
  or pull requests.
- Default branch is `master`.
