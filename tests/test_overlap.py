import unittest

from netaddr import IPSet

from ipconflict.subnet import check_conflicts


class NoOverlapTest(unittest.TestCase):

    def test_two_ips(self):
        subnets = ['10.0.0.1', '10.0.0.2']
        self.assertEqual(check_conflicts(subnets), [])

    def test_multiple_ips(self):
        subnets = ['10.0.0.1', '10.0.0.2', '10.0.0.3']
        self.assertEqual(check_conflicts(subnets), [])

    def test_two_subnets(self):
        subnets = ['10.0.0.0/24', '10.0.1.0/24']
        self.assertEqual(check_conflicts(subnets), [])

    def test_multiple_subnets(self):
        subnets = ['10.0.0.0/24', '10.0.1.0/24', '10.0.2.0/24']
        self.assertEqual(check_conflicts(subnets), [])

    def test_two_ranges(self):
        subnets = ['10.0.0.10-10.0.0.20', '10.0.0.30-10.0.0.40']
        self.assertEqual(check_conflicts(subnets), [])

    def test_multiple_ranges(self):
        subnets = ['10.0.0.10-10.0.0.20', '10.0.0.30-10.0.0.40', '10.0.0.50-10.0.0.60']
        self.assertEqual(check_conflicts(subnets), [])

    def test_multiple_types(self):
        subnets = ['10.0.0.1', '172.16.0.1/24', '192.168.0.1-192.168.0.254']
        self.assertEqual(check_conflicts(subnets), [])


class OverlapTest(unittest.TestCase):

    def test_two_ips(self):
        subnets = ['10.0.0.1', '10.0.0.1']
        result = [('10.0.0.1', '10.0.0.1', IPSet(['10.0.0.1/32']))]
        self.assertEqual(check_conflicts(subnets), result)

    def test_two_subnets(self):
        subnets = ['10.0.1.0/24', '10.0.0.0/22']
        result = [('10.0.1.0/24', '10.0.0.0/22', IPSet(['10.0.1.0/24']))]
        self.assertEqual(check_conflicts(subnets), result)

    def test_ips_and_subnet(self):
        subnets = ['10.0.0.1', '10.0.0.2', '10.0.0.0/24']
        result = [
            ('10.0.0.1', '10.0.0.0/24', IPSet(['10.0.0.1/32'])),
            ('10.0.0.2', '10.0.0.0/24', IPSet(['10.0.0.2/32'])),
        ]
        self.assertEqual(check_conflicts(subnets), result)

    def test_ip_and_range(self):
        subnets = ['10.0.0.3', '10.0.0.1-10.0.0.254']
        result = [('10.0.0.3', '10.0.0.1-10.0.0.254', IPSet(['10.0.0.3/32']))]
        self.assertEqual(check_conflicts(subnets), result)

    def test_subnet_and_range(self):
        subnets = ['10.0.0.0/24', '10.0.0.5-10.0.0.6']
        result = [
            ('10.0.0.0/24', '10.0.0.5-10.0.0.6',
             IPSet(['10.0.0.5/32', '10.0.0.6/32']))
        ]
        self.assertEqual(check_conflicts(subnets), result)

    def test_two_ranges(self):
        subnets = ['10.0.0.1-10.0.0.5', '10.0.0.3-10.0.0.10']
        result = [
            ('10.0.0.1-10.0.0.5', '10.0.0.3-10.0.0.10',
             IPSet(['10.0.0.3/32', '10.0.0.4/32', '10.0.0.5/32'])),
        ]
        self.assertEqual(check_conflicts(subnets), result)

    def test_ip_and_subnet_and_range(self):
        subnets = ['10.0.0.10', '10.0.0.0/24', '10.0.0.252-10.0.0.253']
        result = [
            ('10.0.0.10', '10.0.0.0/24', IPSet(['10.0.0.10/32'])),
            ('10.0.0.0/24', '10.0.0.252-10.0.0.253', IPSet(['10.0.0.252/31'])),
        ]
        self.assertEqual(check_conflicts(subnets), result)


if __name__ == '__main__':
    unittest.main()
