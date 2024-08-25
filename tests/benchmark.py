import pandas as pd
import time

def find_min_value_in_single_column_csv(file_path):
    # Load the CSV file
    df = pd.read_csv(file_path)
    
    # Start the high-resolution timer
    start_time = time.perf_counter_ns()
    
    # Find the minimum value in the first (and only) column
    min_value = df.iloc[:, 0].min()
    
    # Find the index of the minimum value
    min_index = df[df.iloc[:, 0] == min_value].index[0]
    
    # End the timer
    end_time = time.perf_counter_ns()
    duration_ns = end_time - start_time

    return min_index, min_value, duration_ns

if __name__ == "__main__":
    # Replace with your actual file path
    file_path = 'original_permutations.csv'
    
    min_index, min_value, duration_ns = find_min_value_in_single_column_csv(file_path)
    print(f"The smallest value is {min_value} at index {min_index}.")
    print(f"Time taken: {duration_ns} nanoseconds.")