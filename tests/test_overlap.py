import gc
import random
import time
import unittest

from netaddr import IPAddress, IPNetwork, IPRange, IPSet

from ipconflict.subnet import InvalidSubnetError, check_conflicts


class NoOverlapTest(unittest.TestCase):
    def test_two_ips(self):
        subnets = ["10.0.0.1", "10.0.0.2"]
        self.assertEqual(check_conflicts(subnets), [])

    def test_multiple_ips(self):
        subnets = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
        self.assertEqual(check_conflicts(subnets), [])

    def test_two_subnets(self):
        subnets = ["10.0.0.0/24", "10.0.1.0/24"]
        self.assertEqual(check_conflicts(subnets), [])

    def test_multiple_subnets(self):
        subnets = ["10.0.0.0/24", "10.0.1.0/24", "10.0.2.0/24"]
        self.assertEqual(check_conflicts(subnets), [])

    def test_two_ranges(self):
        subnets = ["10.0.0.10-10.0.0.20", "10.0.0.30-10.0.0.40"]
        self.assertEqual(check_conflicts(subnets), [])

    def test_multiple_ranges(self):
        subnets = ["10.0.0.10-10.0.0.20", "10.0.0.30-10.0.0.40", "10.0.0.50-10.0.0.60"]
        self.assertEqual(check_conflicts(subnets), [])

    def test_multiple_types(self):
        subnets = ["10.0.0.1", "172.16.0.1/24", "192.168.0.1-192.168.0.254"]
        self.assertEqual(check_conflicts(subnets), [])


class OverlapTest(unittest.TestCase):
    def test_two_ips(self):
        subnets = ["10.0.0.1", "10.0.0.1"]
        result = [("10.0.0.1", "10.0.0.1", IPSet(["10.0.0.1/32"]))]
        self.assertEqual(check_conflicts(subnets), result)

    def test_two_subnets(self):
        subnets = ["10.0.1.0/24", "10.0.0.0/22"]
        result = [("10.0.1.0/24", "10.0.0.0/22", IPSet(["10.0.1.0/24"]))]
        self.assertEqual(check_conflicts(subnets), result)

    def test_ips_and_subnet(self):
        subnets = ["10.0.0.1", "10.0.0.2", "10.0.0.0/24"]
        result = [
            ("10.0.0.1", "10.0.0.0/24", IPSet(["10.0.0.1/32"])),
            ("10.0.0.2", "10.0.0.0/24", IPSet(["10.0.0.2/32"])),
        ]
        self.assertEqual(check_conflicts(subnets), result)

    def test_ip_and_range(self):
        subnets = ["10.0.0.3", "10.0.0.1-10.0.0.254"]
        result = [("10.0.0.3", "10.0.0.1-10.0.0.254", IPSet(["10.0.0.3/32"]))]
        self.assertEqual(check_conflicts(subnets), result)

    def test_subnet_and_range(self):
        subnets = ["10.0.0.0/24", "10.0.0.5-10.0.0.6"]
        result = [("10.0.0.0/24", "10.0.0.5-10.0.0.6", IPSet(["10.0.0.5/32", "10.0.0.6/32"]))]
        self.assertEqual(check_conflicts(subnets), result)

    def test_two_ranges(self):
        subnets = ["10.0.0.1-10.0.0.5", "10.0.0.3-10.0.0.10"]
        result = [
            (
                "10.0.0.1-10.0.0.5",
                "10.0.0.3-10.0.0.10",
                IPSet(["10.0.0.3/32", "10.0.0.4/32", "10.0.0.5/32"]),
            ),
        ]
        self.assertEqual(check_conflicts(subnets), result)

    def test_ip_and_subnet_and_range(self):
        subnets = ["10.0.0.10", "10.0.0.0/24", "10.0.0.252-10.0.0.253"]
        result = [
            ("10.0.0.10", "10.0.0.0/24", IPSet(["10.0.0.10/32"])),
            ("10.0.0.0/24", "10.0.0.252-10.0.0.253", IPSet(["10.0.0.252/31"])),
        ]
        self.assertEqual(check_conflicts(subnets), result)


class IPv6Test(unittest.TestCase):
    def test_no_overlap(self):
        subnets = ["2001:db8::/64", "2001:db8:0:1::/64", "2001:db8:1::1-2001:db8:1::ff"]
        self.assertEqual(check_conflicts(subnets), [])

    def test_overlap(self):
        subnets = ["2001:db8::/32", "2001:db8::10-2001:db8::11", "::1"]
        result = [("2001:db8::/32", "2001:db8::10-2001:db8::11", IPSet(["2001:db8::10/127"]))]
        self.assertEqual(check_conflicts(subnets), result)

    def test_ipv4_never_conflicts_with_ipv6(self):
        subnets = ["0.0.0.0/0", "::/0", "10.0.0.1", "::ffff:10.0.0.1", "::a00:1"]
        result = [
            ("0.0.0.0/0", "10.0.0.1", IPSet(["10.0.0.1/32"])),
            ("::/0", "::ffff:10.0.0.1", IPSet(["::ffff:10.0.0.1/128"])),
            ("::/0", "::a00:1", IPSet(["::a00:1/128"])),
        ]
        self.assertEqual(check_conflicts(subnets), result)


class ConflictOrderTest(unittest.TestCase):
    def test_follows_input_order_not_address_order(self):
        subnets = ["10.0.2.0/24", "10.0.0.0/16", "10.0.1.0/24", "10.0.1.128/25"]
        result = [
            ("10.0.2.0/24", "10.0.0.0/16", IPSet(["10.0.2.0/24"])),
            ("10.0.0.0/16", "10.0.1.0/24", IPSet(["10.0.1.0/24"])),
            ("10.0.0.0/16", "10.0.1.128/25", IPSet(["10.0.1.128/25"])),
            ("10.0.1.0/24", "10.0.1.128/25", IPSet(["10.0.1.128/25"])),
        ]
        self.assertEqual(check_conflicts(subnets), result)

    def test_duplicates_and_host_bits(self):
        subnets = ["10.0.0.1/16", "10.0.0.0/16", "10.0.255.255"]
        result = [
            ("10.0.0.1/16", "10.0.0.0/16", IPSet(["10.0.0.0/16"])),
            ("10.0.0.1/16", "10.0.255.255", IPSet(["10.0.255.255/32"])),
            ("10.0.0.0/16", "10.0.255.255", IPSet(["10.0.255.255/32"])),
        ]
        self.assertEqual(check_conflicts(subnets), result)


def random_definition(rnd: random.Random) -> str:
    """A CIDR, address or range in a small IPv4 or IPv6 space, so that overlaps are frequent."""
    base = IPNetwork("2001:db8::/118" if rnd.random() < 0.3 else "10.0.0.0/22")
    max_prefixlen = 32 if base.version == 4 else 128

    def address(value: int) -> IPAddress:
        return IPAddress(value, base.version)

    kind = rnd.random()
    start = base.first + rnd.randrange(base.size)
    if kind < 0.4:  # host bits are usually set
        return f"{address(start)}/{rnd.randint(base.prefixlen - 2, max_prefixlen)}"
    if kind < 0.7:
        return str(address(start))
    return f"{address(start)}-{address(rnd.randint(start, min(base.last, start + 300)))}"


class BruteForceComparisonTest(unittest.TestCase):
    @staticmethod
    def brute_force(subnets):
        def ip_set(subnet):
            if "-" in subnet:
                return IPSet(IPRange(*subnet.split("-")))
            return IPSet([subnet])

        sets = [ip_set(subnet) for subnet in subnets]
        return [
            (subnets[earlier], subnets[later], sets[earlier] & sets[later])
            for later in range(len(subnets))
            for earlier in range(later)
            if sets[earlier] & sets[later]
        ]

    def test_random_inputs(self):
        rnd = random.Random(20261115)
        for _ in range(500):
            subnets = [random_definition(rnd) for _ in range(rnd.randint(2, 20))]
            with self.subTest(subnets=subnets):
                self.assertEqual(check_conflicts(subnets), self.brute_force(subnets))


class ScalingTest(unittest.TestCase):
    def test_supernet_followed_by_its_subnets(self):
        # With the old algorithm every /24 here was compared with every earlier definition:
        # 20k definitions would take about 17 minutes. The sweep needs well under a second.
        subnets = ["10.0.0.0/8", *(f"10.{i >> 8}.{i & 255}.0/24" for i in range(20_000))]
        start = time.perf_counter()
        conflicts = check_conflicts(subnets)
        elapsed = time.perf_counter() - start
        self.assertEqual(len(conflicts), 20_000)
        self.assertTrue(all(earlier == "10.0.0.0/8" for earlier, _, _ in conflicts))
        self.assertLess(elapsed, 10)


class InvalidSubnetTest(unittest.TestCase):
    def test_invalid_definitions_raise(self):
        invalid = [
            "foo",
            "",
            "10.0.0.0/33",
            "10.0.0.0/8/8",
            "10.0.0.5-10.0.0.1",
            "10.0.0.1-::1",
            "10.0.0.1-10.0.0.2-10.0.0.3",
        ]
        for subnet in invalid:
            with self.subTest(subnet=subnet), self.assertRaises(InvalidSubnetError) as ctx:
                check_conflicts(["10.0.0.0/24", subnet])
            self.assertEqual(ctx.exception.subnet, subnet)


class GarbageCollectorTest(unittest.TestCase):
    def test_state_is_restored(self):
        subnets = ["10.0.0.0/24", "10.0.0.1"]
        was_enabled = gc.isenabled()
        try:
            for enabled in (True, False):
                (gc.enable if enabled else gc.disable)()
                self.assertEqual(len(check_conflicts(subnets)), 1)
                self.assertEqual(gc.isenabled(), enabled)
        finally:
            (gc.enable if was_enabled else gc.disable)()


if __name__ == "__main__":
    unittest.main()
