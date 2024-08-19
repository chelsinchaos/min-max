// Copyright 2024 Chelsea Anne McElveen

// Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

// The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

// THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.




#include <iostream>
#include <vector>
#include <cmath>
#include <chrono>
#include <fstream>
#include <algorithm>
#include <sstream>
#include "cxxopts.hpp"

double encode(double Y, int D) {
    return pow(2, D) * (Y + D / 2.0);
}

double decode(double X, int D) {
    return X / pow(2, D) - D / 2.0;
}

std::vector<int> ithPermutation(int n, int k, int i) {
    std::vector<int> result;
    int factor = 1;

    for (int j = 1; j <= k; ++j) {
        factor *= j;
        int element = (i / factor) % (j + 1);
        result.push_back(element);
    }

    return result;
}

std::vector<int> reverse_engineer_encoded_value(int value, int layer_depth, int n, int k, std::vector<double>& timings, std::vector<int>& sizes) {
    if (layer_depth == 0) {
        return ithPermutation(n, k, value);
    }

    auto start_time = std::chrono::high_resolution_clock::now();

    double decoded_value = decode(value, 1);
    int original_value = static_cast<int>(decoded_value - layer_depth / 2.0);
    auto result = reverse_engineer_encoded_value(original_value, layer_depth - 1, n, k, timings, sizes);

    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::nano> duration = end_time - start_time;

    timings.push_back(duration.count());
    sizes.push_back(sizeof(result));

    return result;
}

std::vector<int> load_values_from_csv(const std::string& csv_file_path) {
    std::vector<int> values;
    std::ifstream file(csv_file_path);
    std::string line;

    while (std::getline(file, line)) {
        std::stringstream ss(line);
        int value;
        ss >> value;
        values.push_back(value);
    }

    return values;
}

int main(int argc, char* argv[]) {
    cxxopts::Options options("Program", "Description of Program");

    // Define options
    options.add_options()
        ("n", "Total number of elements", cxxopts::value<int>())
        ("k", "Number of elements in the permutation", cxxopts::value<int>())
        ("csv", "Path to the CSV file", cxxopts::value<std::string>())
        ("help", "Print help");

    auto result = options.parse(argc, argv);

    if (result.count("help")) {
        std::cout << options.help() << std::endl;
        return 0;
    }

    int n = result["n"].as<int>();
    int k = result["k"].as<int>();
    std::string csv_file_path = result["csv"].as<std::string>();

    std::vector<int> values = load_values_from_csv(csv_file_path);
    int l = static_cast<int>(std::ceil(k * std::log2(n)));
    std::vector<double> timings;
    std::vector<int> sizes;

    auto start_time = std::chrono::high_resolution_clock::now();
    auto smallest_value = *std::min_element(values.begin(), values.end());
    reverse_engineer_encoded_value(smallest_value, l, n, k, timings, sizes);
    auto end_time = std::chrono::high_resolution_clock::now();

    std::chrono::duration<double, std::nano> total_time = end_time - start_time;

    std::cout << smallest_value << std::endl;
    std::cout << total_time.count() << " ns" << std::endl;

    return 0;
}
