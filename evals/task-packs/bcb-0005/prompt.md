<!-- source: BigCodeBench task #BigCodeBench/5 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench) -->
# Prompt for bcb_0005

Create a dictionary where keys are letters from a predefined list LETTERS and values are lists of random integers. Then, calculates the population standard deviation for each list of integers and returns a dictionary of these values. The random integers for each key are generated within the range 0 to 100, and each list contains between 1 to 10 integers.
The function should output with:
    dict: A dictionary where each key corresponds to a letter from the input list and each value is the
    population standard deviation of a list of random integers associated with that key.
You should write self-contained code starting with:
```
import random
import math
def task_func(LETTERS=[chr(i) for i in range(97, 123)]):
```
