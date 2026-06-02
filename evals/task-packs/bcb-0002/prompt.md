<!-- source: BigCodeBench task #BigCodeBench/2 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench) -->
# Prompt for bcb_0002

Create a dictionary in which keys are random letters and values are lists of random integers. The dictionary is then sorted by the mean of the values in descending order, demonstrating the use of the statistics library.
The function should output with:
    dict: The sorted dictionary with letters as keys and lists of integers as values, sorted by their mean values.
You should write self-contained code starting with:
```
import random
import statistics
def task_func(LETTERS):
```
