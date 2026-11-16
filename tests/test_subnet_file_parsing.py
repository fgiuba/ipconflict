import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from ipconflict.subnet import parse_stdin_data, parse_subnet_data, parse_subnet_file


class SubnetFileTest(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))

    def test_space_in_comment(self):
        subnet_file = os.path.join(self.test_dir, "data", "subnets_file_with_spaces_in_comments")
        subnets = parse_subnet_file(subnet_file)
        self.assertEqual(subnets, ["10.168.0.0/20", "10.146.0.0/20"])

    def test_empty_line_in_file(self):
        subnet_file = os.path.join(self.test_dir, "data", "subnets_file_with_empty_lines")
        subnets = parse_subnet_file(subnet_file)
        self.assertEqual(subnets, ["10.168.0.0/20", "10.146.0.0/20"])

    def test_not_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in (os.path.join(directory, "missing"), directory):
                with self.subTest(path=path):
                    with contextlib.redirect_stdout(io.StringIO()) as output:
                        subnets = parse_subnet_file(path)
                    self.assertEqual(subnets, [])
                    self.assertEqual(output.getvalue(), "warning: invalid subnets file\n")


class SubnetDataTest(unittest.TestCase):
    def test_comments_blank_lines_and_whitespace(self):
        data = "# office\r\n10.0.0.0/24\r\n\r\n   # lab\n\t10.0.1.0/24  \n \t\n2001:db8::/32"
        self.assertEqual(parse_subnet_data(data), ["10.0.0.0/24", "10.0.1.0/24", "2001:db8::/32"])


class StdinDataTest(unittest.TestCase):
    def test_whitespace_separated(self):
        data = " 10.0.0.0/24\n10.0.0.1\t10.0.0.2  10.0.0.3-10.0.0.4\r\n\n"
        with mock.patch("sys.stdin", io.StringIO(data)):
            subnets = parse_stdin_data()
        self.assertEqual(subnets, ["10.0.0.0/24", "10.0.0.1", "10.0.0.2", "10.0.0.3-10.0.0.4"])


if __name__ == "__main__":
    unittest.main()
