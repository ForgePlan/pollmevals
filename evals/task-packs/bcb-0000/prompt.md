<!-- source: BigCodeBench task #BigCodeBench/0 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench) -->
# Prompt for bcb_0000

Calculates the average of the sums of absolute differences between each pair of consecutive numbers for all permutations of a given list. Each permutation is shuffled before calculating the differences. Args: - numbers (list): A list of numbers. Default is numbers from 1 to 10.
The function should output with:
    float: The average of the sums of absolute differences for each shuffled permutation of the list.
You should write self-contained code starting with:
```
import itertools
from random import shuffle
def task_func(numbers=list(range(1, 3))):
```
