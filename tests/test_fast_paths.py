"""The fast paths must behave exactly like netaddr, which defines the accepted syntax."""

import importlib.util
import random
import subprocess
import sys
import unittest
from unittest import mock

from netaddr import IPAddress, IPRange, IPSet

from ipconflict import subnet
from ipconflict.subnet import _address_lines, _ip_set_factory, _parse_block, _parse_block_netaddr

FAST_PATHS = subnet._FAST_IPV4 and subnet._FAST_IPV6

EDGE_CASES = [
    "10.0.0.0/8", "10.0.0.1/16", "10.0.0.1", "0.0.0.0/0", "255.255.255.255/32", "1.2.3.4/33",
    "010.0.0.1", "10.0.0.01", "10.00.0.1", "1.2.3", "1.2.3.4.5", "0x0a.0.0.1", "10.0.0.256",
    " 10.0.0.1", "10.0.0.1 ", "10.0.0.0/08", "10.0.0.0/+8", "10.0.0.0/ 8", "10.0.0.0/8 ",
    "10.0.0.0/-0", "10.0.0.0/1_6", "10.0.0.0/\u0662\u0664", "10.0.0.0/", "/8", "10.0.0.0//8",
    "10.0.0.0/8/8", "10.0.0.1/255.255.0.0", "10.0.0.0/0.0.255.255", "10.0.0.0/255.0.255.0",
    "10.0.0.1-10.0.0.9", "10.0.0.9-10.0.0.1", "10.0.0.2-10.0.0.1", "::2-::1",
    "10.0.0.1-10.0.0.1", "10.0.0.1 - 10.0.0.9",
    "10.0.0.1-", "-10.0.0.1", "10.0.0.1--10.0.0.9", "10.0.0.1-10.0.0.2-10.0.0.3", "10.0.0.1-::1",
    "::1-10.0.0.1", "10.0.0.0/8-10.0.0.1", "010.0.0.1-10.0.0.2", "::", "::/0", "::1", "::1/128",
    "::1/129", "2001:db8::/32", "2001:DB8::1/64", "2001:db8::1/064", "2001:db8:0:0:0:0:0:1",
    "2001:db8::1::2", "2001:db8::g", "fe80::1%eth0", "::ffff:10.0.0.1", "::ffff:10.0.0.1/104",
    "::10.0.0.1", "2001:db8::/ffff:ffff::", "2001:db8::-2001:db8::ff", "2001:db8::ff-2001:db8::",
    "", " ", "#", "10.0.0.1\x00", "\uff11\uff10.0.0.1",
]  # fmt: skip


def outcome(parse, text):
    try:
        return parse(text)
    except Exception as exc:
        return type(exc).__name__


def random_definition(rnd: random.Random) -> str:
    version = rnd.choice((4, 6))
    bits = 32 if version == 4 else 128
    value = rnd.getrandbits(bits) if rnd.random() < 0.5 else rnd.randrange(1 << 12)
    address = str(IPAddress(value, version))
    kind = rnd.random()
    if kind < 0.4:
        return f"{address}/{rnd.randint(0, bits)}"
    if kind < 0.7:
        return address
    end = min(value + rnd.randrange(1000), (1 << bits) - 1)
    return f"{address}-{IPAddress(end, version)}"


def mutate(rnd: random.Random, text: str) -> str:
    alphabet = "0123456789abcdefABCDEF.:/-% +_x"
    chars = list(text)
    for _ in range(rnd.randint(1, 3)):
        position = rnd.randrange(len(chars) + 1)
        action = rnd.random()
        if action < 0.4 or not chars:
            chars.insert(position, rnd.choice(alphabet))
        elif action < 0.7:
            del chars[min(position, len(chars) - 1)]
        else:
            chars[min(position, len(chars) - 1)] = rnd.choice(alphabet)
    return "".join(chars)


def load_subnet_module():
    """Run a fresh copy of ipconflict.subnet, to see which fast paths it turns on."""
    spec = importlib.util.spec_from_file_location("ipconflict_subnet_copy", subnet.__file__)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ParseBlockTest(unittest.TestCase):
    def check(self, text):
        result = outcome(_parse_block, text)
        self.assertEqual(result, outcome(_parse_block_netaddr, text), text)
        if isinstance(result, str):  # any other error would crash the CLI with exit status 1
            self.assertEqual(result, "InvalidSubnetError", text)

    def test_edge_cases(self):
        for text in EDGE_CASES:
            with self.subTest(text=text):
                self.check(text)

    def test_random_and_mutated_definitions(self):
        rnd = random.Random(20261116)
        for _ in range(10_000):
            text = random_definition(rnd)
            self.check(text)
            self.check(mutate(rnd, text))

    def test_arbitrary_strings(self):
        rnd = random.Random(20261117)
        alphabet = "0123456789abcdefABCDEF.:/-% +_x\x00\t\n[]" + chr(0x0662) + chr(0xFF11)
        for _ in range(10_000):
            self.check("".join(rnd.choices(alphabet, k=rnd.randint(0, 24))))

    @unittest.skipUnless(sys.platform.startswith("linux"), "glibc and musl qualify, others may not")
    def test_fast_path_is_on(self):
        self.assertTrue(FAST_PATHS)

    @unittest.skipUnless(FAST_PATHS, "the fast path is turned off on this platform")
    def test_common_formats_do_not_need_netaddr(self):
        common = ["10.0.0.0/8", "10.0.0.1", "10.0.0.1-10.0.0.9", "2001:db8::/32", "::1", "::-::ff"]
        with mock.patch.object(subnet, "_parse_block_netaddr", side_effect=AssertionError):
            for text in common:
                _parse_block(text)


class FastPathSwitchTest(unittest.TestCase):
    """Each fast path must be off wherever it could disagree with netaddr."""

    def test_ipv4_is_off_on_windows_and_cygwin(self):
        for platform in ("win32", "cygwin"):  # netaddr does not use inet_pton for IPv4 there
            with self.subTest(platform=platform):
                with mock.patch.object(sys, "platform", platform):
                    module = load_subnet_module()
                self.assertFalse(module._FAST_IPV4)
                self.assertEqual(module._FAST_IPV6, subnet._FAST_IPV6)

    def test_ipv4_is_off_where_inet_pton_accepts_leading_zeros(self):
        for lenient in ("01.2.3.4", "1.2.3.04"):  # netaddr rejects both

            def inet_pton(family, text, lenient=lenient):
                return bytes(4) if text == lenient else subnet.inet_pton(family, text)

            with self.subTest(lenient=lenient):
                with mock.patch("_socket.inet_pton", inet_pton):
                    module = load_subnet_module()
                self.assertFalse(module._FAST_IPV4)

    def test_ipv6_is_off_without_ipv6_support(self):
        with mock.patch("_socket.has_ipv6", False):
            module = load_subnet_module()
        self.assertFalse(module._FAST_IPV6)
        self.assertEqual(module._FAST_IPV4, subnet._FAST_IPV4)

    @unittest.skipUnless(FAST_PATHS, "the fast path is turned off on this platform")
    def test_each_switch_covers_one_ip_version(self):
        ipv4 = ["10.0.0.0/8", "10.0.0.1", "10.0.0.1-10.0.0.9"]
        ipv6 = ["2001:db8::/32", "::1", "::-::ff"]
        for switch, off, on in (("_FAST_IPV4", ipv4, ipv6), ("_FAST_IPV6", ipv6, ipv4)):
            with (
                self.subTest(switch=switch),
                mock.patch.object(subnet, switch, False),
                mock.patch.object(subnet, "inet_pton", wraps=subnet.inet_pton) as inet_pton,
            ):
                for text in off:
                    self.assertEqual(_parse_block(text), _parse_block_netaddr(text))
                inet_pton.assert_not_called()
                for text in on:
                    _parse_block(text)
                inet_pton.assert_called()


class AddressLinesTest(unittest.TestCase):
    def check(self, version, first, last):
        addresses = IPSet(IPRange(IPAddress(first, version), IPAddress(last, version)))
        expected = "".join(f"{address}\n" for address in addresses)
        self.assertEqual("".join(_address_lines(version, first, last)), expected)

    def test_ipv4(self):
        top = (1 << 32) - 1
        for first, last in [
            (0, 0),
            (0, 300),
            (top - 300, top),
            (top, top),
            (0x0A00FFF0, 0x0A010110),
        ]:
            self.check(4, first, last)
        rnd = random.Random(4)
        for _ in range(200):
            first = rnd.getrandbits(32)
            self.check(4, first, min(first + rnd.randrange(700), top))

    def test_ipv6(self):
        top = (1 << 128) - 1
        mapped = int(IPAddress("::ffff:10.0.0.0"))
        documentation = int(IPAddress("2001:db8::"))
        for first, last in [
            (0, 20),
            (mapped - 5, mapped + 300),
            (int(IPAddress("::10.0.0.0")) - 3, int(IPAddress("::10.0.0.0")) + 3),
            (documentation + 0xFFF0, documentation + 0x10010),
            (documentation, documentation + 5000),  # more than one chunk
            (top - 10, top),
        ]:
            self.check(6, first, last)
        rnd = random.Random(6)
        for _ in range(100):
            first = rnd.getrandbits(128)
            self.check(6, first, min(first + rnd.randrange(300), top))

    def test_ipv6_without_ipv6_support(self):
        mapped = int(IPAddress("::ffff:10.0.0.0"))
        top = (1 << 128) - 1
        with mock.patch.object(subnet, "_FAST_IPV6", False):  # netaddr writes the addresses
            for first, last in [(0, 20), (mapped - 5, mapped + 5), (top - 3, top)]:
                self.check(6, first, last)


class IPSetFactoryTest(unittest.TestCase):
    def test_matches_netaddr_ranges(self):
        to_ip_set = _ip_set_factory()
        rnd = random.Random(7)
        cases = []
        for version, bits in ((4, 32), (6, 128)):
            for prefixlen in range(bits + 1):  # every CIDR size, aligned
                size = 1 << (bits - prefixlen)
                first = rnd.getrandbits(bits) & ~(size - 1)
                cases.append((version, first, first + size - 1))
            for _ in range(200):  # arbitrary ranges, mostly not a single CIDR
                first = rnd.getrandbits(bits)
                cases.append((version, first, min(first + rnd.randrange(5000), (1 << bits) - 1)))
        for version, first, last in cases:
            expected = IPSet(IPRange(IPAddress(first, version), IPAddress(last, version)))
            self.assertEqual(to_ip_set(version, first, last), expected)


class StartupTest(unittest.TestCase):
    @unittest.skipUnless(FAST_PATHS, "the fast path is turned off on this platform")
    def test_cli_does_not_import_heavy_modules(self):
        # Importing netaddr and importlib.metadata used to take 2/3 of a typical run; typing and
        # socket are not needed either. Whatever the interpreter itself imports does not count.
        code = (
            "import sys\n"
            "heavy = ('importlib.metadata', 'netaddr', 'socket', 'typing')\n"
            "preloaded = set(sys.modules)\n"
            "from ipconflict import main\n"
            "try:\n"
            "    main(sys.argv[1:])\n"
            "except SystemExit:\n"
            "    pass\n"
            "imported = [name for name in heavy if name in sys.modules and name not in preloaded]\n"
            "print(imported, file=sys.stderr)\n"
        )
        args = ["-p", "10.0.0.0/30", "10.0.0.1-10.0.0.2", "2001:db8::/127", "2001:db8::1"]
        command = [sys.executable, "-c", code, *args]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.stderr.strip(), "[]")
        self.assertEqual(
            result.stdout,
            "conflict found: 10.0.0.0/30 <-> 10.0.0.1-10.0.0.2\n10.0.0.1\n10.0.0.2\n"
            "conflict found: 2001:db8::/127 <-> 2001:db8::1\n2001:db8::1\n",
        )


if __name__ == "__main__":
    unittest.main()
