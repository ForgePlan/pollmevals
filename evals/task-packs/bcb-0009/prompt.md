<!-- source: BigCodeBench task #BigCodeBench/9 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench) -->
# Prompt for bcb_0009

Create a Pandas DataFrame from a list of pairs and visualize the data using a bar chart. - The title of the barplot should be set to 'Category vs Value'`.
The function should output with:
    tuple:
    DataFrame: A pandas DataFrame with columns 'Category' and 'Value'.
    Axes: A matplotlib Axes displaying a bar chart of categories vs. values.
You should write self-contained code starting with:
```
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
def task_func(list_of_pairs):
```
