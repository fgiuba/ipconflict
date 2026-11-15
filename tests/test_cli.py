import pytest

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


def test_too_few_subnets(capsys):
    assert run(capsys, "10.0.0.0/24") == (2, "must specify at least 2 subnets\n")


@pytest.mark.parametrize("subnet", ["foo", "10.0.0.0/8/8", "10.0.0.5-10.0.0.1"])
def test_invalid_subnet(capsys, subnet):
    assert run(capsys, "-q", "10.0.0.0/24", subnet) == (
        2,
        f"error: invalid subnet format {subnet}\n",
    )
