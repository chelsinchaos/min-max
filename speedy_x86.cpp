#include <iostream>
#include <vector>
#include <cmath>
#include <chrono>
#include <fstream>
#include <algorithm>
#include <sstream>
#include "cxxopts.hpp"

double encode(double Y, int D) {
    double result;
    asm volatile(
        "fldl2e\n\t"        // Load log2(e) to stack
        "fmulp\n\t"         // Multiply ST(1) with ST(0), store result in ST(1)
        "fild %1\n\t"       // Load int D
        "faddp\n\t"         // Add ST(1) to ST(0)
        "fyl2x\n\t"         // Compute ST(1) * log2(ST(0))
        "fld1\n\t"          // Load constant 1
        "fadd\n\t"          // Add ST(1) to ST(0)
        "fscale\n\t"        // Scale by power of 2
        "fstp %0"           // Store result in 'result'
        : "=m"(result)
        : "m"(D), "m"(Y)
    );
    return result;
}

double decode(double X, int D) {
    double result;
    asm volatile(
        "fldl2e\n\t"        // Load log2(e) to stack
        "fild %1\n\t"       // Load int D
        "fmulp\n\t"         // Multiply ST(1) with ST(0), store result in ST(1)
        "fyl2x\n\t"         // Compute ST(1) * log2(ST(0))
        "fld1\n\t"          // Load constant 1
        "fadd\n\t"          // Add ST(1) to ST(0)
        "fscale\n\t"        // Scale by power of 2
        "fld %2\n\t"        // Load double X
        "fdivp\n\t"         // Divide X by the result in ST(0)
        "fild %1\n\t"       // Load int D
        "fsubp\n\t"         // Subtract D/2 from the result
        "fstp %0"           // Store result in 'result'
        : "=m"(result)
        : "m"(D), "m"(X)
    );
    return result;
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
    int n, k;
    std::string csv_file_path;

    cxxopts::Options options("Program", "Description of Program");

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

    n = result["n"].as<int>();
    k = result["k"].as<int>();
    csv_file_path = result["csv"].as<std::string>();

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