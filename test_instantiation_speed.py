"""Quick test to verify model instantiation performance."""

import time
from pydapter import create_model, Adaptable
from pydapter.fields import FieldTemplate
from pydantic import BaseModel

# Create a simple model
fields = {
    "name": FieldTemplate(str),
    "value": FieldTemplate(float, default=0.0)
}
SimpleModel = create_model("SimpleModel", fields=fields)

# Test instantiation performance
def test_instantiation(iterations=10000):
    start = time.perf_counter()
    for _ in range(iterations):
        SimpleModel(name="test", value=1.0)
    end = time.perf_counter()
    
    total_time = end - start
    avg_time = total_time / iterations
    
    # Convert to appropriate unit
    if avg_time < 1e-6:
        print(f"Average instantiation time: {avg_time * 1e9:.1f} ns")
    elif avg_time < 1e-3:
        print(f"Average instantiation time: {avg_time * 1e6:.1f} μs")
    else:
        print(f"Average instantiation time: {avg_time * 1e3:.1f} ms")
    
    print(f"Total time for {iterations} iterations: {total_time:.3f} seconds")

# Also test a basic Pydantic model for comparison
class BasicModel(BaseModel):
    name: str
    value: float = 0.0

def test_basic_instantiation(iterations=10000):
    start = time.perf_counter()
    for _ in range(iterations):
        BasicModel(name="test", value=1.0)
    end = time.perf_counter()
    
    total_time = end - start
    avg_time = total_time / iterations
    
    if avg_time < 1e-6:
        print(f"Basic Pydantic model: {avg_time * 1e9:.1f} ns")
    elif avg_time < 1e-3:
        print(f"Basic Pydantic model: {avg_time * 1e6:.1f} μs")
    else:
        print(f"Basic Pydantic model: {avg_time * 1e3:.1f} ms")

print("Testing model instantiation performance...")
print("=" * 50)
print("\nPydapter model (created with create_model):")
test_instantiation()

print("\nBasic Pydantic model (for comparison):")
test_basic_instantiation()

# Check if traits system is active
try:
    from pydapter.traits import Trait
    print("\nTraits system is available in this version")
except ImportError:
    print("\nTraits system is NOT available in this version")