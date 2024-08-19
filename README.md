Copyright 2024 Chelsea Anne McElveen

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


# Polynomial Time Solution for NP-Complete Decision Problems

This project implements a novel approach to solving NP-complete decision problems in polylog time, based on the research paper by Chelsea Anne McElveen.

## Overview

The core idea is to use innovative encoding and decoding functions to represent the solution space of NP-complete decision problems in a way that allows for polynomial time solutions. This approach transforms the traditionally exponential-time search space into a more manageable form.

## Key Concepts

### Permutation Function

The foundation of this approach is based on the permutation function:

P(n, k) = n! / (n-k)!

Where:
- n is the total number of elements
- k is the number of elements being chosen

### Encoding Function

The encoding function maps an index value at a specific layer number to a unique value:

f(X, D) = (X / 2^D) - (D/2)

Where:
- X is the index value at a specific layer number
- D is the layer number

### Decoding Function

The decoding function retrieves the index value and layer number from a given encoded value:

f^(-1)(Y, D) = 2^D * (Y + D/2)

Where:
- Y is the encoded value
- D is the layer number

## Features

- Encode and decode values using the custom algorithm
- Generate the i-th permutation for given n and k values
- Reverse-engineer encoded values through multiple layers
- Solve NP-complete problems like the Traveling Salesman Problem and Knapsack Problem in polynomial time

## Complexity Analysis

- Time Complexity: O(1) for both encoding and decoding functions
- Space Complexity: O(1) for both encoding and decoding functions

This represents a significant improvement over traditional approaches, which often have exponential time and space complexities for NP-complete decision problems.

## Usage

# Set Generation and Reverse Engineering Scripts

This repository contains two Python scripts and a c++ 17 .cpp file for each the min and max versions as well as one optimized with assembly for x86: one for generating a set of permutations and another for reverse engineering encoded values. Both scripts can be run from the command line and allow for customizable input parameters.

# Speedy.py

## Usage

Run the `speedy.py` script from the command line using the following format:

`python speedy.py -n <total_elements> -k <elements_in_permutation> [-csv <csv_file_path>] [values...]`

## Arguments

- **`-n:`** (Required) The total number of elements.  
  **Type:** `int`  
  **Example:** `-n 2`

- **`-k:`** (Required) The number of elements in the permutation.  
  **Type:** `int`  
  **Example:** `-k 16`

- **`-csv:`** (Optional) Path to the CSV file with values to use instead of generating them.  
  **Type:** `str`  
  **Example:** `-csv path/to/file.csv`

- **`values:`** (Optional) List of values to process if not provided in a CSV file.  
  **Type:** `int` (multiple values allowed)  
  **Example:** `1 2 3 4`

## Examples

### Basic Example with CSV File

`python speedy.py -n 2 -k 16 -csv test_set.csv`

This example processes values from the `test_set.csv` file.

## Output

The script processes the input values based on the provided parameters and prints the smallest value along with the total execution time in nanoseconds.

# Speedy_max.cpp, Speedy_min.cpp, Speedy_x86.cpp

## Compilation

### Install a C++ Compiler

Ensure you have a C++ compiler installed. Common options include GCC (for Linux and macOS) or MSVC (for Windows). On Linux or macOS, you can install GCC using a package manager (apt, yum, brew, etc.). On Windows, you can install Visual Studio with the C++ development tools.

### Compile the program

Open your terminal or command prompt.

Navigate to the directory where your program.cpp file is saved.

Use the following command to compile your program: g++ -o program program.cpp

### Run the Executable

After the compilation is successful, run the program by typing the following command: ./program -n <total_elements> -k <elements_in_permutation> -csv <csv_file_path>

## Usage

After compiling the program, you can run the executable from the command line using the following format:

`./program -n <total_elements> -k <elements_in_permutation> -csv <csv_file_path>`

### Arguments

- **`-n:`** (Required) The total number of elements.  
  **Type:** `int`  
  **Example:** `-n 100`

- **`-k:`** (Required) The number of elements in the permutation.  
  **Type:** `int`  
  **Example:** `-k 5`

- **`-csv:`** (Optional) Path to the CSV file containing values to process.  
  **Type:** `string`  
  **Example:** `-csv path/to/values.csv`

### Example

To execute the program with 100 total elements, 5 elements in the permutation, and a CSV file named `data.csv`:

`./program -n 100 -k 5 -csv data.csv`

This command will process the values provided in the `data.csv` file, find the smallest value, reverse-engineer it, and display the result along with the total execution time in nanoseconds.

### Output

The program will output the smallest value from the provided data along with the total execution time measured in nanoseconds.

## Set Generation Script

### Features

- Generates permutations for a given base `n` and exponent `k`.
- Randomizes the order of the generated permutations.
- Saves the randomized set to a CSV file (`test_set.csv`).

### Usage

Run the set generation script from the command line using the following format:


python3 gen.py -n <base_number> -k <exponent>


## Applications

This approach can be applied to various NP-complete decision problems, including:

1. Traveling Salesman Problem (TSP)
2. Knapsack Problem
3. Graph Coloring
4. Hamiltonian Cycle Problem

## Future Work

- Extend the approach to other NP-complete decision problems
- Explore real-world applications in logistics, supply chain optimization, and network design
- Investigate integration with quantum computing
- Develop dedicated hardware to enhance performance

## References

1. Cook, S. A. (1971). The Complexity of Theorem Proving Procedures. Proceedings of the third annual ACM symposium on Theory of computing - STOC ’71.

2. Levin, L. A. (1973). Universal Sequential Search Problems. Problems of Information Transmission, 9(3), 265-266.

3. Karp, R. M. (1972). Reducibility Among Combinatorial Problems. In R. E. Miller and J. W. Thatcher (Editors), Complexity of Computer Computations. Plenum Press.

4. Garey, M. R., & Johnson, D. S. (1979). Computers and Intractability: A Guide to the Theory of NP-Completeness. W. H. Freeman & Co.

5. Arora, S., & Barak, B. (2009). Computational Complexity: A Modern Approach. Cambridge University Press.

6. Sedgewick, R., & Wayne, K. (2011). Algorithms (4th ed.). Addison-Wesley.

7. Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2009). Introduction to Algorithms (3rd ed.). The MIT Press.


## Acknowledgments

I wish to express my profound gratitude to the luminaries in the field of computational complexity theory, whose seminal works have laid the foundational stones for this research. I am immensely grateful to the vibrant and ever-curious community of researchers and scholars for fostering a milieu of rigorous inquiry and the relentless pursuit of knowledge. I also cannot have begun this this without the unrelenting support of my dad, Michael Aden McElveen, my mom, Janise Heitmann McElveen, , my wife Josie James Dionne and my entire family.