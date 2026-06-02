# source: BigCodeBench task #BigCodeBench/5 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench)
import unittest
from unittest.mock import patch
import math
import random
class TestCases(unittest.TestCase):
    def setUp(self):
        self.LETTERS = [chr(i) for i in range(97, 123)]
        random.seed(42)
    def test_default_letters(self):
        # Test the function with the default set of letters
        sd_dict = task_func()
        self.assertEqual(set(self.LETTERS), set(sd_dict.keys()))
        for val in sd_dict.values():
            self.assertGreaterEqual(val, 0)
    def test_custom_letters(self):
        # Test the function with a custom set of letters
        custom_letters = ['x', 'y', 'z']
        sd_dict = task_func(custom_letters)
        self.assertEqual(set(custom_letters), set(sd_dict.keys()))
        for val in sd_dict.values():
            self.assertGreaterEqual(val, 0)
    
    @patch('random.randint')
    def test_uniform_values(self, mocked_randint):
         # Test with uniform values to check standard deviation is zero
        mocked_randint.side_effect = [3, 50, 50, 50, 3, 50, 50, 50]  # Two iterations: size 3, values all 50
        letters = ['a', 'b']
        sd_dict = task_func(letters)
        self.assertTrue(all(math.isclose(val, 0, abs_tol=1e-5) for val in sd_dict.values()))
    
    def test_empty_letters(self):
        # Test with an empty list of letters
        sd_dict = task_func([])
        self.assertEqual(sd_dict, {})
    @patch('random.randint')
    def test_known_values(self, mocked_randint):
        # Test with known values to check correct standard deviation calculation
        mocked_randint.side_effect = [2, 10, 1]  # List size of 2, with values 10 and 1
        letters = ['a']
        sd_dict = task_func(letters)
        values = [10, 1]
        mean = sum(values) / len(values)
        sum_of_squares = sum((x - mean) ** 2 for x in values)
        expected_sd = math.sqrt(sum_of_squares / len(values))
        self.assertAlmostEqual(list(sd_dict.values())[0], expected_sd)
