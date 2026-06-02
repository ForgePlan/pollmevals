<!-- source: BigCodeBench task #BigCodeBench/6 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench) -->
# Prompt for bcb_0006

Find the latest log file in a specified directory that matches a given regex pattern. This function searches through all files in the specified directory, filters them based on the provided regex pattern, and returns the path to the most recent log file based on modification time. If no files match the pattern or the directory is empty, the function returns None.
The function should output with:
    str or None: The path to the most recent log file that matches the pattern, or None if no matching files are found.
You should write self-contained code starting with:
```
import os
import re
def task_func(pattern, log_dir='/var/log/'):
```
