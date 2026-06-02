<!-- source: BigCodeBench task #BigCodeBench/7 (license: Apache-2.0, retrieved 2026-06-03, url: https://huggingface.co/datasets/bigcode/bigcodebench) -->
# Prompt for bcb_0007

Find the best-selling product from a given CSV file with sales data. This function parses a CSV file assumed to have a header followed by rows containing two columns: 'product' and 'quantity'. It computes the total sales per product and determines the product with the highest cumulative sales. The CSV file must include at least these two columns, where 'product' is the name of the product as a string and 'quantity' is the number of units sold as an integer. Args: csv_file_path (str): The file path to the CSV file containing sales data.
The function should output with:
    str: The name of the top-selling product based on the total quantity sold.
You should write self-contained code starting with:
```
import csv
import collections
import operator
def task_func(csv_file_path):
```
