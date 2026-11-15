from importlib import metadata

import pytest

import ipconflict
from ipconflict import main


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    with pytest.raises(SystemExit) as exc:
        main(argv)
    code = exc.value.code
    assert isinstance(code, int)
    return code, capsys.readouterr().out


def test_conflict_found(capsys):
    assert run(capsys, "-q", "10.0.1.0/24", "10.0.0.0/22") == (
        0,
        "conflict found: 10.0.1.0/24 <-> 10.0.0.0/22\n",
    )


def test_no_conflict(capsys):
    assert run(capsys, "-q", "10.0.0.0/24", "10.0.1.0/24") == (1, "no conflict found\n")


def test_print_conflicts(capsys):
    assert run(capsys, "-q", "-p", "10.0.0.0/24", "10.0.0.5-10.0.0.6") == (
        0,
        "conflict found: 10.0.0.0/24 <-> 10.0.0.5-10.0.0.6\n10.0.0.5\n10.0.0.6\n",
    )


@pytest.mark.parametrize("flags", [["-o"], ["-o", "-p"]])
def test_ip_only(capsys, flags):
    assert run(capsys, *flags, "10.0.0.0/24", "10.0.0.5-10.0.0.6", "10.0.0.6") == (
        0,
        "10.0.0.5\n10.0.0.6\n10.0.0.6\n10.0.0.6\n",
    )


def test_ip_only_across_a_24_boundary(capsys):
    assert run(capsys, "-o", "10.0.0.254-10.0.1.1", "10.0.0.0/16") == (
        0,
        "10.0.0.254\n10.0.0.255\n10.0.1.0\n10.0.1.1\n",
    )


def test_ip_only_ipv6(capsys):
    assert run(capsys, "-o", "2001:db8::/126", "2001:db8::2-2001:db8::9", "::ffff:10.0.0.1") == (
        0,
        "2001:db8::2\n2001:db8::3\n",
    )


def test_version(capsys):
    assert run(capsys, "-V") == (0, f"ipconflict {metadata.version('ipconflict')}\n")
    assert ipconflict.__version__ == metadata.version("ipconflict")


def test_quiet_is_accepted(capsys):
    assert run(capsys, "-q", "10.0.0.0/24", "10.0.1.0/24") == (1, "no conflict found\n")


def test_too_few_subnets(capsys):
    assert run(capsys, "10.0.0.0/24") == (2, "must specify at least 2 subnets\n")


@pytest.mark.parametrize("subnet", ["foo", "10.0.0.0/8/8", "10.0.0.5-10.0.0.1"])
def test_invalid_subnet(capsys, subnet):
    assert run(capsys, "-q", "10.0.0.0/24", subnet) == (
        2,
        f"error: invalid subnet format {subnet}\n",
    )
