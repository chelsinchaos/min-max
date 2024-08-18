import csv
import random

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
    n = 2  # Set your value for n
    k = 16  # Set your value for k
    main(n, k)