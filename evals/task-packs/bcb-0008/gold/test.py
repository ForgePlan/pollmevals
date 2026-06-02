# source: BigCodeBench task #BigCodeBench/8 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench)
import unittest
from collections import Counter
class TestCases(unittest.TestCase):
    def test_case_1(self):
        """Single tuple with small integers as strings"""
        T1 = (('1', '2', '3'),)
        result = task_func(T1)
        self.assertIsInstance(result, Counter)
        self.assertEqual(sum(result.values()), 6)
    def test_case_2(self):
        """Multiple tuples with small integers as strings"""
        T1 = (('1', '2'), ('3', '4'))
        result = task_func(T1)
        self.assertIsInstance(result, Counter)
        self.assertEqual(sum(result.values()), 10)
        
    def test_case_3(self):
        """Single tuple with larger integers as strings"""
        T1 = (('10', '20', '30'),)
        result = task_func(T1)
        self.assertIsInstance(result, Counter)
        self.assertEqual(sum(result.values()), 60)
    def test_case_4(self):
        """Multiple tuples with mixed small and large integers as strings"""
        T1 = (('1', '10'), ('100', '1000'))
        result = task_func(T1)
        self.assertIsInstance(result, Counter)
        self.assertEqual(sum(result.values()), 1111)
    def test_case_5(self):
        """Single tuple with repeating integers as strings"""
        T1 = (('1', '1', '1'),)
        result = task_func(T1)
        self.assertIsInstance(result, Counter)
        self.assertEqual(sum(result.values()), 3)
    def test_empty_input(self):
        """Empty tuple as input"""
        T1 = ()
        result = task_func(T1)
        self.assertIsInstance(result, Counter)
        self.assertEqual(sum(result.values()), 0)
    def test_range_limit(self):
        """Check if random numbers respect the RANGE parameter"""
        T1 = (('10',),)
        RANGE = 20
        result = task_func(T1, RANGE)
        self.assertTrue(all(0 <= num <= RANGE for num in result.keys()))
