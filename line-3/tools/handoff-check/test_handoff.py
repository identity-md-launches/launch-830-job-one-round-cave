"""Regression checks without image fixtures or filesystem writes."""
import copy
from pathlib import Path
import runpy
import unittest


API = runpy.run_path(str(Path(__file__).with_name('handoff.py')))


class HandoffTests(unittest.TestCase):
    def test_in_memory_corruption_and_paths(self):
        self.assertTrue(API['demo']()['ok'])

    def test_metadata_tampering(self):
        name = Path(__file__).resolve().relative_to(API['ROOT']).as_posix()
        original = API['receipt']([name])
        self.assertTrue(API['verify'](original)['ok'])
        for key, value in (('bytes', -1), ('sha256', '0' * 64), ('extra', True)):
            changed = copy.deepcopy(original)
            changed['files'][0][key] = value
            with self.assertRaises(ValueError):
                API['verify'](changed)

    def test_bad_receipts(self):
        for document in ({}, [], {'schema': 'wrong', 'files': []},
                         {'schema': 'handoff-check/v1', 'files': []},
                         {'schema': 'handoff-check/v1', 'files': [{}]}):
            with self.assertRaises(ValueError):
                API['verify'](document)

    def test_duplicate_paths(self):
        name = Path(__file__).resolve().relative_to(API['ROOT']).as_posix()
        with self.assertRaises(ValueError):
            API['receipt']([name, name])


if __name__ == '__main__':
    unittest.main()
