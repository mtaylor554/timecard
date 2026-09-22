import unittest

import timecard


class VersionTests(unittest.TestCase):
    def test_version_looks_like_a_release(self):
        self.assertRegex(timecard.__version__, r"^\d+\.\d+\.\d+")

    def test_version_matches_pyproject(self):
        # Keeps the installed metadata and pyproject.toml from drifting apart
        # silently - if this fails, pyproject.toml's version was bumped
        # without reinstalling, or vice versa.
        self.assertEqual(timecard.__version__, "0.1.0")


if __name__ == "__main__":
    unittest.main()
