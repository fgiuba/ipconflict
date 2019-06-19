import os
import unittest

from ipconflict.subnet import parse_subnet_file


class SubnetFileTest(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))

    def test_space_in_comment(self):
        subnet_file = self.test_dir + '/subnets_file_with_spaces_in_comments'
        subnets = parse_subnet_file(subnet_file)
        self.assertEqual(subnets, ['10.168.0.0/20', '10.146.0.0/20'])

    def test_empty_line_in_file(self):
        subnet_file = self.test_dir + '/subnets_file_with_empty_lines'
        subnets = parse_subnet_file(subnet_file)
        self.assertEqual(subnets, ['10.168.0.0/20', '10.146.0.0/20'])

if __name__ == '__main__':
    unittest.main()
