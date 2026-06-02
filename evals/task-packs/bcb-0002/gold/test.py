# source: BigCodeBench task #BigCodeBench/2 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench)
import unittest
class TestCases(unittest.TestCase):
    
    def setUp(self):
        # Setting up a common letters array and sorted dictionary for use in all tests
        self.letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
        self.sorted_dict = task_func(self.letters)
    def test_case_1(self):
        # Check if the function returns a dictionary
        self.assertIsInstance(self.sorted_dict, dict, "The function should return a dictionary.")
    def test_case_2(self):
        # Ensure all keys in the sorted dictionary are within the provided letters
        all_letters = all([key in self.letters for key in self.sorted_dict.keys()])
        self.assertTrue(all_letters, "All keys of the dictionary should be letters.")
        
    def test_case_3(self):
        # Ensure all values are lists of integers
        all_lists = all([isinstance(val, list) and all(isinstance(i, int) for i in val) for val in self.sorted_dict.values()])
        self.assertTrue(all_lists, "All values of the dictionary should be lists of integers.")
        
    def test_case_4(self):
        # Check if the dictionary is sorted by the mean values in descending order
        means = [statistics.mean(val) for val in self.sorted_dict.values()]
        self.assertTrue(all(means[i] >= means[i + 1] for i in range(len(means) - 1)), "The dictionary should be sorted in descending order based on the mean of its values.")
    
    def test_case_5(self):
        # Check if the dictionary includes all provided letters as keys
        self.assertEqual(set(self.sorted_dict.keys()), set(self.letters), "The dictionary should have all provided letters as keys.")
