"""Test to measure timing overhead."""

import time
from pydapter import create_model
from pydapter.fields import FieldTemplate

# Create a simple model
fields = {
    "name": FieldTemplate(str),
    "value": FieldTemplate(float, default=0.0)
}
SimpleModel = create_model("SimpleModel", fields=fields)

print("Comparing timing methods:")
print("=" * 50)

# Method 1: Time the entire loop (what I did)
iterations = 10000
start = time.perf_counter()
for _ in range(iterations):
    SimpleModel(name="test", value=1.0)
end = time.perf_counter()
method1_time = (end - start) / iterations

print(f"\nMethod 1 (time entire loop):")
if method1_time < 1e-6:
    print(f"  Average: {method1_time * 1e9:.1f} ns")
else:
    print(f"  Average: {method1_time * 1e6:.1f} μs")

# Method 2: Time each iteration (what benchmark does)
times = []
for _ in range(min(1000, iterations)):  # Fewer iterations because it's slower
    start = time.perf_counter()
    SimpleModel(name="test", value=1.0)
    end = time.perf_counter()
    times.append(end - start)

method2_time = sum(times) / len(times)

print(f"\nMethod 2 (time each iteration):")
if method2_time < 1e-6:
    print(f"  Average: {method2_time * 1e9:.1f} ns")
else:
    print(f"  Average: {method2_time * 1e6:.1f} μs")

# Method 3: Measure the overhead of perf_counter itself
overhead_times = []
for _ in range(1000):
    start = time.perf_counter()
    end = time.perf_counter()
    overhead_times.append(end - start)

overhead = sum(overhead_times) / len(overhead_times)

print(f"\nTiming overhead (perf_counter calls):")
if overhead < 1e-6:
    print(f"  Average: {overhead * 1e9:.1f} ns")
else:
    print(f"  Average: {overhead * 1e6:.1f} μs")

print(f"\nMethod 2 minus overhead: {(method2_time - overhead) * 1e6:.1f} μs")
print(f"This should be closer to Method 1: {method1_time * 1e6:.1f} μs")