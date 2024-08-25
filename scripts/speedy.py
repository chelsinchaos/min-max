import argparse
import math
import random
import time
import sys
from functools import lru_cache
import csv

@lru_cache(maxsize=9192)
def encode(Y, D):
    return 2**D * (Y + D/2)

@lru_cache(maxsize=9192)
def decode(X, D):
    return X/(2**D) - D/2

@lru_cache(maxsize=9192)
def ithPermutation(n, k, i):
    elements = list(range(n))
    perm = []
    for _ in range(k):
        if not elements:
            break
        index = int(i % len(elements))
        perm.append(elements[index])
        elements.remove(elements[index])
        if not elements:
            break
        i //= len(elements)
    return sum(perm)

def reverse_engineer_encoded_value(value, layer_depth, n, k, timings, sizes):
    if layer_depth == 0:
        return ithPermutation(n, k, value)

    start_time = time.perf_counter()

    # Decoding the value for the current layer
    decoded_value = decode(value, 1)
    
    # Since you're trying to reverse engineer the smallest value, 
    # you need to extract the original value which would have been encoded.
    # Given the encode function: 2**D * (Y + D/2), you need to subtract D/2 from the decoded value.
    original_value = decoded_value - layer_depth/2

    result = reverse_engineer_encoded_value(original_value, layer_depth - 1, n, k, timings, sizes)

    end_time = time.perf_counter()
    timings[layer_depth] = (end_time - start_time) * 1e6
    sizes[layer_depth] = sys.getsizeof(result)

    return result

def save_to_csv(values):
    with open('original_permutations.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Index", "Value"])
        for index, value in enumerate(values):
            writer.writerow([index, value])

def main(args):
    n = args.n
    k = args.k
    generate_random_values = True if args.p == "T" else False
    save_to_csv_flag = True if args.s == "T" else False

    l = math.ceil(k * math.log2(n))  # Changed here
    values_at_D0 = random.sample(range(1, n**k + 1), n**k) if generate_random_values else args.values

    # Save the generated values to a CSV only if the flag is set to True
    if generate_random_values and save_to_csv_flag:
        save_to_csv(values_at_D0)

    timings = {}
    sizes = {}

    start_time = time.perf_counter()
    smallest_value = reverse_engineer_encoded_value(sum(values_at_D0), l, n, k, timings, sizes)
    end_time = time.perf_counter()

    index_of_value = values_at_D0.index(smallest_value)
    total_time = (end_time - start_time) * 1e6
    total_size = sys.getsizeof(values_at_D0) + sum(sizes.values())

    print(f"The smallest value at depth 0 is: {smallest_value}")
    print(f"Index of smallest value in original set: {index_of_value}")
    print(f"Number of steps/layers: {l}")
    print(f"Total processing time: {total_time:.6f} microseconds")
    print(f"Total memory used: {total_size} bytes")
    for depth, timing in timings.items():
        print(f"Time taken for layer {depth}: {timing:.6f} microseconds")
        print(f"Memory used for layer {depth}: {sizes[depth]} bytes")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process the input parameters.')
    parser.add_argument('-n', type=int, required=True, help='The total number of elements.')
    parser.add_argument('-k', type=int, required=True, help='Number of elements in the permutation.')
    parser.add_argument('-p', choices=['T', 'F'], required=True, help='Generate random values or use provided values.')
    parser.add_argument('-s', choices=['T', 'F'], default='F', help='Save generated values to CSV. Default is False.')

    args = parser.parse_args()
    main(args)