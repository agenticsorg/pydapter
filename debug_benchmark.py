"""Debug version of benchmark to understand timing differences."""

import time
import statistics
import gc
import uuid
from pydapter import create_model, Adaptable
from pydapter.fields import FieldTemplate
from pydantic import BaseModel

# Create model
fields = {
    "id": FieldTemplate(uuid.UUID, default=uuid.uuid4),
    "name": FieldTemplate(str),
    "value": FieldTemplate(float, default=0.0)
}
SimpleModel = create_model("SimpleModel", fields=fields)

def instantiate_simple():
    return SimpleModel(name="test", value=1.0)

# Method 1: Benchmark style (time each call)
print("Method 1: Benchmark style (timing each call)")
print("-" * 50)

# Warmup
for _ in range(10):
    instantiate_simple()

gc.collect()

times = []
for i in range(1000):
    start = time.perf_counter()
    instantiate_simple()
    end = time.perf_counter()
    times.append(end - start)
    
    if i < 5:
        print(f"  Call {i}: {(end - start) * 1e6:.3f} μs")

median_time = statistics.median(times)
mean_time = statistics.mean(times)

print(f"\nStats for 1000 calls:")
print(f"  Median: {median_time * 1e6:.3f} μs")
print(f"  Mean: {mean_time * 1e6:.3f} μs")
print(f"  Min: {min(times) * 1e6:.3f} μs")
print(f"  Max: {max(times) * 1e6:.3f} μs")

# Method 2: Time a batch
print("\n\nMethod 2: Time a batch of calls")
print("-" * 50)

gc.collect()

start = time.perf_counter()
for _ in range(1000):
    instantiate_simple()
end = time.perf_counter()

batch_time = (end - start) / 1000
print(f"  Average per call: {batch_time * 1e6:.3f} μs")

# Compare with basic Pydantic
class BasicModel(BaseModel):
    id: uuid.UUID = None
    name: str
    value: float = 0.0

print("\n\nFor comparison - Basic Pydantic model:")
print("-" * 50)

def instantiate_basic():
    return BasicModel(id=uuid.uuid4(), name="test", value=1.0)

# Time batch
start = time.perf_counter()
for _ in range(1000):
    instantiate_basic()
end = time.perf_counter()

basic_time = (end - start) / 1000
print(f"  Average per call: {basic_time * 1e6:.3f} μs")

print(f"\n\nSummary:")
print(f"  Pydapter (individual timing): {mean_time * 1e6:.3f} μs")
print(f"  Pydapter (batch timing): {batch_time * 1e6:.3f} μs")
print(f"  Basic Pydantic: {basic_time * 1e6:.3f} μs")
print(f"  Timing overhead estimate: {(mean_time - batch_time) * 1e6:.3f} μs")