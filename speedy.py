# Copyright 2024 Chelsea Anne McElveen

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.





import argparse
import math
import random
import time
import sys
import csv

def encode(Y, D):
    return 2**D * (Y + D/2)

def decode(X, D):
    return X/(2**D) - D/2

def ithPermutation(n, k, i):
    result = 0
    factor = 1
    for j in range(1, k + 1):
        factor *= j
        element = i // factor % (j + 1)
        result += element * 10 ** (j - 1)  # Assuming base 10
    return result

def reverse_engineer_encoded_value(value, layer_depth, n, k, timings, sizes):
    if layer_depth == 0:
        return ithPermutation(n, k, value)

    start_time = time.perf_counter()

    decoded_value = decode(value, 1)
    original_value = decoded_value - layer_depth/2
    result = reverse_engineer_encoded_value(original_value, layer_depth - 1, n, k, timings, sizes)

    end_time = time.perf_counter()
    timings[layer_depth] = (end_time - start_time)  # nanoseconds
    sizes[layer_depth] = sys.getsizeof(result)

    return result

def load_values_from_csv(csv_file_path):
    with open(csv_file_path, newline='') as csvfile:
        return [int(row[0]) for row in csv.reader(csvfile)]

def main(args):
    n = args.n
    k = args.k
    values_at_D0 = load_values_from_csv(args.csv) if args.csv else args.values

    l = math.ceil(k * math.log2(n))
    timings = {}
    sizes = {}

    smallest_value = min(values_at_D0)

    start_time = time.perf_counter_ns()
    reverse_engineer_encoded_value(smallest_value, l, n, k, timings, sizes)
    end_time = time.perf_counter_ns()

    total_time = (end_time - start_time)

    print(f"{smallest_value}")  # smallest value
    print(f"{total_time:.6f} ns")  # total execution time

    return smallest_value

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process the input parameters.')
    parser.add_argument('-n', type=int, required=True, help='The total number of elements.')
    parser.add_argument('-k', type=int, required=True, help='Number of elements in the permutation.')
    parser.add_argument('-csv', type=str, help='Path to the CSV file with values to use instead of generating them.')
    parser.add_argument('values', nargs='*', type=int, help='List of values if not provided in a CSV file.')
    args = parser.parse_args()

    main(args)
