"""Test to isolate UUID generation overhead."""

import time
import uuid
from pydapter import create_model
from pydapter.fields import FieldTemplate
from pydantic import BaseModel

print("Testing UUID generation overhead")
print("=" * 50)

# Test 1: Just UUID generation
iterations = 10000
start = time.perf_counter()
for _ in range(iterations):
    uuid.uuid4()
end = time.perf_counter()
uuid_time = (end - start) / iterations

print(f"\nUUID generation alone: {uuid_time * 1e6:.3f} μs")

# Test 2: Model WITHOUT UUID field
fields_no_uuid = {
    "name": FieldTemplate(str),
    "value": FieldTemplate(float, default=0.0)
}
ModelNoUUID = create_model("ModelNoUUID", fields=fields_no_uuid)

start = time.perf_counter()
for _ in range(iterations):
    ModelNoUUID(name="test", value=1.0)
end = time.perf_counter()
no_uuid_time = (end - start) / iterations

print(f"Model instantiation WITHOUT UUID: {no_uuid_time * 1e6:.3f} μs ({no_uuid_time * 1e9:.0f} ns)")

# Test 3: Model WITH UUID field (like the benchmark)
fields_with_uuid = {
    "id": FieldTemplate(uuid.UUID, default=uuid.uuid4),
    "name": FieldTemplate(str),
    "value": FieldTemplate(float, default=0.0)
}
ModelWithUUID = create_model("ModelWithUUID", fields=fields_with_uuid)

start = time.perf_counter()
for _ in range(iterations):
    ModelWithUUID(name="test", value=1.0)
end = time.perf_counter()
with_uuid_time = (end - start) / iterations

print(f"Model instantiation WITH UUID: {with_uuid_time * 1e6:.3f} μs")

print(f"\nOverhead from UUID generation: {(with_uuid_time - no_uuid_time) * 1e6:.3f} μs")
print(f"That accounts for {((with_uuid_time - no_uuid_time) / with_uuid_time) * 100:.1f}% of the total time!")

# Test the 0.2.3 way (for comparison, if Field is available)
try:
    from pydapter import Field
    fields_old = [
        Field(name="id", annotation=uuid.UUID, default_factory=uuid.uuid4),
        Field(name="name", annotation=str),
        Field(name="value", annotation=float, default=0.0)
    ]
    ModelOldStyle = create_model("ModelOldStyle", fields=fields_old)
    
    start = time.perf_counter()
    for _ in range(iterations):
        ModelOldStyle(name="test", value=1.0)
    end = time.perf_counter()
    old_style_time = (end - start) / iterations
    
    print(f"\nOld style (Field) WITH UUID: {old_style_time * 1e6:.3f} μs")
except ImportError:
    print("\nField not available in this version")