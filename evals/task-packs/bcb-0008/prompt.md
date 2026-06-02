<!-- source: BigCodeBench task #BigCodeBench/8 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench) -->
# Prompt for bcb_0008

Convert elements in 'T1' to integers and create a list of random integers where the number of integers is determined by the sum of the integers in `T1`. Random integers are generated between 0 and `RANGE` (default is 100). Count the occurrences of each number in the generated list using a Counter.
The function should output with:
    Counter: A Counter object representing the count of each number appearing in the list of generated random integers.
You should write self-contained code starting with:
```
from collections import Counter
import itertools
from random import randint
def task_func(T1, RANGE=100):
```
