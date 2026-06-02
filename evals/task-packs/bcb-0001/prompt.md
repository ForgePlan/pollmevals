<!-- source: BigCodeBench task #BigCodeBench/1 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench) -->
# Prompt for bcb_0001

Generate a random string of the specified length composed of uppercase and lowercase letters, and then count the occurrence of each character in this string.
The function should raise the exception for: ValueError if the length is a negative number
The function should output with:
    dict: A dictionary where each key is a character from the generated string and the value
    is the count of how many times that character appears in the string.
You should write self-contained code starting with:
```
import collections
import random
import string
def task_func(length=100):
```
