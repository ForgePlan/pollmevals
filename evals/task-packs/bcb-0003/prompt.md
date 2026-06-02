<!-- source: BigCodeBench task #BigCodeBench/3 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench) -->
# Prompt for bcb_0003

Create a dictionary where keys are specified letters and values are lists of random integers. Then calculate the mean of these integers for each key and return a dictionary of these means.
The function should output with:
    dict: A dictionary where each key is a letter from the input list and the value is the mean of
    a randomly generated list of integers (with each list having 1 to 10 integers ranging from 0 to 100).
You should write self-contained code starting with:
```
import random
import numpy as np
def task_func(LETTERS):
```
