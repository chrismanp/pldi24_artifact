"""
Contains helper code required to parse the pbbs csv file which contains
information needed to run the benchmarks.
"""

import csv

# Stores information required to run and test a given benchmark.
class Benchmark(object):
  def __init__(self, benchmark_name, name, binary, check_binary, data_dir, small_inputs,
               standard_inputs):
    self.benchmark_name = benchmark_name      # Name of the benchmark
    self.name = name      # Path of benchmark directory from the pbbs directory.
    self.binary = binary  # Name of binary to run, excluding file type.
    self.check_binary = check_binary # Name of test binary to run.
    self.data_dir = data_dir # Data directory that contains test inputs.
    self.small_inputs = small_inputs  # Small test inputs.
    self.standard_inputs = standard_inputs # Standard test inputs.

# Parses csv file containing benchmark information. Returns a list of benchmark
# objects.
def parse_csv(input_file):
  benchmark_list = []
  file = open(input_file)
  csvreader = csv.reader(file)

  # Skip the row containing the category names.
  next(csvreader)

  for row in csvreader:
    if not row:
      continue

    if row[0].startswith("#"):
      continue

    benchmark_name = row[0]
    name = row[1]
    binary = row[2]
    check_binary = row[3]
    data_dir = row[4]

    small_inputs = row[5].split(",")
    standard_inputs = row[6].split(",")

    benchmark_obj = Benchmark(benchmark_name, name, binary, check_binary, data_dir,
                              small_inputs, standard_inputs)
    benchmark_list.append(benchmark_obj)
  return benchmark_list
