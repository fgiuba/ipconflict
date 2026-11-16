import io
import random
import subprocess
import sys
from importlib import metadata

import pytest
from netaddr import IPAddress, IPNetwork

import ipconflict
from ipconflict import main
from ipconflict.subnet import check_conflicts


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    with pytest.raises(SystemExit) as exc:
        main(argv)
    code = exc.value.code
    assert isinstance(code, int)
    return code, capsys.readouterr().out


# Report


def test_conflict_found(capsys):
    assert run(capsys, "-q", "10.0.1.0/24", "10.0.0.0/22") == (
        0,
        "conflict found: 10.0.1.0/24 <-> 10.0.0.0/22\n",
    )


def test_conflicts_follow_the_input_order(capsys):
    assert run(capsys, "10.0.2.0/24", "10.0.0.0/16", "10.0.1.0/24", "10.0.1.128/25") == (
        0,
        "conflict found: 10.0.2.0/24 <-> 10.0.0.0/16\n"
        "conflict found: 10.0.0.0/16 <-> 10.0.1.0/24\n"
        "conflict found: 10.0.0.0/16 <-> 10.0.1.128/25\n"
        "conflict found: 10.0.1.0/24 <-> 10.0.1.128/25\n",
    )


def test_no_conflict(capsys):
    assert run(capsys, "-q", "10.0.0.0/24", "10.0.1.0/24") == (1, "no conflict found\n")


@pytest.mark.parametrize("flag", ["-p", "-o"])
def test_no_conflict_when_printing_addresses(capsys, flag):
    assert run(capsys, flag, "10.0.0.0/24", "10.0.1.0/24") == (1, "no conflict found\n")


@pytest.mark.parametrize("flag", ["-p", "--print-conflicts"])
def test_print_conflicts(capsys, flag):
    assert run(capsys, "-q", flag, "10.0.0.0/24", "10.0.0.5-10.0.0.6") == (
        0,
        "conflict found: 10.0.0.0/24 <-> 10.0.0.5-10.0.0.6\n10.0.0.5\n10.0.0.6\n",
    )


@pytest.mark.parametrize("flags", [["-o"], ["--ip-only"], ["-o", "-p"]])
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


def test_report_is_written_in_chunks(capsys, monkeypatch):
    monkeypatch.setattr(ipconflict, "_CHUNK", 3)  # 7 conflicts: two full chunks and a partial one
    subnets = ["10.0.0.0/8", *(f"10.0.{i}.0/24" for i in range(7))]
    expected = "".join(f"conflict found: 10.0.0.0/8 <-> 10.0.{i}.0/24\n" for i in range(7))
    assert run(capsys, *subnets) == (0, expected)


def random_definition(rnd: random.Random) -> str:
    """A definition in any accepted format, from spaces small enough for frequent overlaps.

    No overlap exceeds 512 addresses, which keeps the output of -p short.
    """
    base = IPNetwork(rnd.choice(["10.0.0.0/22", "2001:db8::/118", "::ffff:10.0.0.0/118"]))
    max_prefixlen = 32 if base.version == 4 else 128
    start = IPAddress(base.first + rnd.randrange(base.size), base.version)
    prefixlen = rnd.randint(max_prefixlen - 9, max_prefixlen)
    kind = rnd.random()
    if kind < 0.3:  # host bits are usually set
        text = f"{start}/{prefixlen}"
    elif kind < 0.4:  # a netmask: parsed by netaddr, not by the fast path
        text = f"{start}/{IPNetwork(f'{start}/{prefixlen}').netmask}"
    elif kind < 0.7:
        text = str(start)
    else:
        end = IPAddress(min(base.last, int(start) + rnd.randrange(300)), base.version)
        text = f"{start}-{end}"
    return text.upper() if rnd.random() < 0.1 else text  # definitions are printed verbatim


def test_output_matches_the_library(capsys):
    # The CLI writes its report straight from the sweep, without the IPSets of check_conflicts:
    # it must print exactly what printing those would, as earlier versions did.
    rnd = random.Random(20261116)
    for _ in range(200):
        subnets = [random_definition(rnd) for _ in range(rnd.randint(2, 12))]
        conflicts = check_conflicts(subnets)
        headers = [f"conflict found: {earlier} <-> {later}\n" for earlier, later, _ in conflicts]
        addresses = ["".join(f"{address}\n" for address in ip_set) for _, _, ip_set in conflicts]
        reports = {
            (): "".join(headers),
            ("-p",): "".join(h + a for h, a in zip(headers, addresses, strict=True)),
            ("-o",): "".join(addresses),
        }
        for flags, report in reports.items():
            argv = [*flags, *subnets]
            expected = (0, report) if conflicts else (1, "no conflict found\n")
            assert run(capsys, *argv) == expected, argv


# Input


@pytest.mark.parametrize("flag", ["-f", "--from-file"])
def test_from_file(capsys, tmp_path, flag):
    path = tmp_path / "subnets.txt"
    path.write_bytes(b"# office\r\n10.0.0.0/24\r\n\r\n  # lab\n\t10.0.0.5-10.0.0.6  \n")
    assert run(capsys, flag, str(path)) == (
        0,
        "conflict found: 10.0.0.0/24 <-> 10.0.0.5-10.0.0.6\n",
    )


def test_from_missing_file(capsys, tmp_path):
    assert run(capsys, "-f", str(tmp_path / "missing.txt"), "10.0.0.0/24", "10.0.0.1") == (
        0,
        "warning: invalid subnets file\nconflict found: 10.0.0.0/24 <-> 10.0.0.1\n",
    )


@pytest.mark.parametrize("flag", ["-i", "--from-stdin"])
def test_from_stdin(capsys, monkeypatch, flag):
    monkeypatch.setattr("sys.stdin", io.StringIO("10.0.0.0/24\n10.0.0.5\t10.1.0.0/16  10.0.0.6\n"))
    assert run(capsys, flag) == (
        0,
        "conflict found: 10.0.0.0/24 <-> 10.0.0.5\nconflict found: 10.0.0.0/24 <-> 10.0.0.6\n",
    )


def test_sources_are_read_in_a_fixed_order(capsys, monkeypatch, tmp_path):
    # Arguments, then standard input, then the file, whatever the order of the options: the
    # conflicts follow it.
    path = tmp_path / "subnets.txt"
    path.write_text("10.0.0.0/8\n")
    monkeypatch.setattr("sys.stdin", io.StringIO("10.0.0.0/16\n"))
    assert run(capsys, "-f", str(path), "-i", "10.0.0.1") == (
        0,
        "conflict found: 10.0.0.1 <-> 10.0.0.0/16\n"
        "conflict found: 10.0.0.1 <-> 10.0.0.0/8\n"
        "conflict found: 10.0.0.0/16 <-> 10.0.0.0/8\n",
    )


def test_too_few_subnets(capsys):
    assert run(capsys, "10.0.0.0/24") == (2, "must specify at least 2 subnets\n")


def test_too_few_subnets_in_all_sources(capsys, monkeypatch, tmp_path):
    path = tmp_path / "subnets.txt"
    path.write_text("# nothing but comments\n\n")
    monkeypatch.setattr("sys.stdin", io.StringIO(" \n"))
    assert run(capsys, "-i", "-f", str(path), "10.0.0.0/24") == (
        2,
        "must specify at least 2 subnets\n",
    )


# Errors


@pytest.mark.parametrize("subnet", ["foo", "10.0.0.0/8/8", "10.0.0.5-10.0.0.1"])
def test_invalid_subnet(capsys, subnet):
    assert run(capsys, "-q", "10.0.0.0/24", subnet) == (
        2,
        f"error: invalid subnet format {subnet}\n",
    )


def test_first_invalid_subnet_is_reported_before_any_output(capsys):
    assert run(capsys, "10.0.0.0/24", "10.0.0.1", "2001:db8::g", "foo") == (
        2,
        "error: invalid subnet format 2001:db8::g\n",
    )


def test_unknown_option(capsys):
    assert run(capsys, "--bogus", "10.0.0.0/24", "10.0.0.1") == (2, "")


def test_keyboard_interrupt(capsys, monkeypatch):
    def interrupt(subnets):
        raise KeyboardInterrupt

    monkeypatch.setattr(ipconflict, "_find_conflicts", interrupt)
    try:
        result = run(capsys, "10.0.0.0/24", "10.0.0.1")
    except KeyboardInterrupt:  # left alone, it would stop the whole test session
        pytest.fail("KeyboardInterrupt was not handled")
    assert result == (2, "aborted\n\n")


# Options and entry points


@pytest.mark.parametrize("flag", ["-q", "--quiet"])
def test_quiet_is_accepted(capsys, flag):
    assert run(capsys, flag, "10.0.0.0/24", "10.0.1.0/24") == (1, "no conflict found\n")


@pytest.mark.parametrize("flag", ["-V", "--version"])
def test_version(capsys, flag):
    assert run(capsys, flag) == (0, f"ipconflict {metadata.version('ipconflict')}\n")


def test_version_attribute():
    assert ipconflict.__version__ == metadata.version("ipconflict")
    assert not hasattr(ipconflict, "nonexistent")


def test_version_when_not_installed(capsys, monkeypatch):
    def version(name):
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "version", version)
    assert run(capsys, "-V") == (0, "ipconflict unknown\n")
    assert ipconflict.__version__ == "unknown"


def test_help(capsys, monkeypatch):
    monkeypatch.setenv("PYTHON_COLORS", "0")  # argparse colors its help since Python 3.14
    code, output = run(capsys, "--help")
    assert code == 0
    assert output.endswith(
        "exit status:\n"
        "  0: one or more conflicts found\n"
        "  1: no conflict found\n"
        "  2: aborted or invalid input\n"
    )
    assert "--quiet" not in output  # accepted, but hidden


@pytest.mark.parametrize(
    ("argv", "status", "output"),
    [
        (["10.0.0.0/24", "10.0.0.1"], 0, "conflict found: 10.0.0.0/24 <-> 10.0.0.1\n"),
        (["10.0.0.0/24", "10.0.1.0/24"], 1, "no conflict found\n"),
        (["10.0.0.0/24", "foo"], 2, "error: invalid subnet format foo\n"),
    ],
)
def test_python_m(argv, status, output):
    command = [sys.executable, "-m", "ipconflict", *argv]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert (result.returncode, result.stdout) == (status, output)


def test_console_script():
    (script,) = metadata.entry_points(group="console_scripts", name="ipconflict")
    assert script.load() is main
