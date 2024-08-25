import argparse
import math
import random
import csv
import time

def encode(Y, D):
    return 2**D * (Y + D/2)

def decode(X, D):
    return X/(2**D) - D/2

def ithPermutation(n, k, i):
    elements = list(range(n))
    perm = []
    for _ in range(k):
        if not elements:
            break
        index = i % len(elements)
        perm.append(elements.pop(index))
        if not elements:  # Protect against zero division.
            break
        i //= len(elements)
    return ''.join(map(str, perm))

def reverse_engineer_encoded_value(value, layer_depth, n, k):
    if layer_depth == 0:
        return ithPermutation(n, k, value)

    smallest_value = ((((k * math.log2(n) - layer_depth) + 1) / (2**(((k * math.log2(n) - layer_depth) + 1) - 1)))/2) - (((k * math.log2(n) - layer_depth) + 1) / 2)

    if smallest_value < value:
        value -= smallest_value

    return reverse_engineer_encoded_value(int(smallest_value), layer_depth - 1, n, k)

def read_values_from_csv(csv_file):
    values = []
    with open(csv_file, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            values.extend([int(val) for val in row])
    return values

def main(args):
    n = args.n
    k = args.k
    generate_random_values = True if args.p == "T" else False

    l = int(k * math.log2(n))

    if args.csv:
        values_at_D0 = read_values_from_csv(args.csv)
    elif generate_random_values:
        values_at_D0 = [random.randint(1, 100) for _ in range(n**k)]
    else:
        values_at_D0 = args.values

    encoded_value_at_max_D = sum(values_at_D0)
    
    # High-resolution nanosecond timing
    start_time = time.perf_counter_ns()
    smallest_value = reverse_engineer_encoded_value(encoded_value_at_max_D, l, n, k)
    end_time = time.perf_counter_ns()

    time_taken_ns = end_time - start_time

    print(f"The smallest value at depth 0 is: {smallest_value}")
    print(f"Time taken to calculate smallest value: {time_taken_ns} nanoseconds")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process the input parameters.')
    parser.add_argument('-n', type=int, required=True, help='The total number of elements.')
    parser.add_argument('-k', type=int, required=True, help='Number of elements in the permutation.')
    parser.add_argument('-p', choices=['T', 'F'], required=True, help='Generate random values or use provided values.')
    parser.add_argument('-csv', type=str, help='Path to a CSV file containing input values.')

    args = parser.parse_args()
    main(args)
