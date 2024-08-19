import csv
import random
import argparse

def generate_permutations(n, k):
    return list(range(1, n**k + 1))

def save_to_csv(values, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for value in values:
            writer.writerow([value])

def main(n, k):
    # Generate all permutations
    values = generate_permutations(n, k)

    # Shuffle the values to randomize the order
    random.shuffle(values)

    # Save to CSV
    save_to_csv(values, 'test_set.csv')
    print(f"File saved with {len(values)} values in 'test_set.csv'")

if __name__ == "__main__":
    # Setup argument parser
    parser = argparse.ArgumentParser(description='Generate a set of permutations and save them to a CSV file.')
    parser.add_argument('-n', type=int, required=True, help='The base number n')
    parser.add_argument('-k', type=int, required=True, help='The exponent k')

    # Parse arguments
    args = parser.parse_args()

    # Call main function with provided arguments
    main(args.n, args.k)
