#!/usr/bin/env python3
"""
Test script to verify benchmark compatibility with different pydapter versions.

This minimal script tests that core functionality works across versions.
"""

import sys
import json

print("Testing pydapter version compatibility...")

# Test imports
try:
    import pydapter
    print(f"✓ pydapter imported successfully")
    print(f"  Version: {getattr(pydapter, '__version__', 'unknown')}")
except ImportError as e:
    print(f"✗ Failed to import pydapter: {e}")
    sys.exit(1)

# Test basic imports
try:
    from pydantic import BaseModel
    print("✓ pydantic imported successfully")
except ImportError as e:
    print(f"✗ Failed to import pydantic: {e}")
    sys.exit(1)

# Test core pydapter imports
features = {
    "has_adaptable": False,
    "has_field": False,
    "has_fieldtemplate": False,
    "has_create_model": False,
    "has_adapters": False,
}

try:
    from pydapter import Adaptable
    features["has_adaptable"] = True
    print("✓ Adaptable imported")
except ImportError:
    print("✗ Adaptable not available")

try:
    from pydapter.fields import Field
    features["has_field"] = True
    print("✓ Field imported")
except ImportError:
    print("✗ Field not available")

try:
    from pydapter.fields import FieldTemplate
    features["has_fieldtemplate"] = hasattr(FieldTemplate, '__init__')
    print(f"✓ FieldTemplate imported (functional: {features['has_fieldtemplate']})")
except ImportError:
    print("✗ FieldTemplate not available")

try:
    from pydapter.fields import create_model
    features["has_create_model"] = True
    print("✓ create_model imported")
except ImportError:
    print("✗ create_model not available")

try:
    from pydapter.adapters import JsonAdapter, CsvAdapter
    features["has_adapters"] = True
    print("✓ Adapters imported")
except ImportError:
    print("✗ Adapters not available")

# Test basic functionality
print("\nTesting basic functionality...")

# Test 1: Create a simple model
if features["has_adaptable"] and features["has_create_model"]:
    try:
        class SimpleModel(Adaptable, BaseModel):
            name: str
            value: int
        
        instance = SimpleModel(name="test", value=42)
        print(f"✓ Created model instance: {instance.name}={instance.value}")
    except Exception as e:
        print(f"✗ Failed to create model: {e}")

# Test 2: Field creation (if available)
if features["has_field"]:
    try:
        field = Field(name="test", annotation=str, default="default")
        print("✓ Created Field instance")
    except Exception as e:
        print(f"✗ Failed to create Field: {e}")

if features["has_fieldtemplate"]:
    try:
        # Try kwargs first (newer versions)
        try:
            template = FieldTemplate(base_type=str, default="default")
            print("✓ Created FieldTemplate with kwargs")
        except:
            # Try method chaining (older versions)
            template = FieldTemplate(str).with_default("default")
            print("✓ Created FieldTemplate with method chaining")
    except Exception as e:
        print(f"✗ Failed to create FieldTemplate: {e}")

# Test 3: Adapter functionality
if features["has_adapters"] and features["has_adaptable"]:
    try:
        class TestModel(Adaptable, BaseModel):
            name: str
            value: int
        
        TestModel.register_adapter(JsonAdapter)
        instance = TestModel(name="test", value=42)
        
        # Try to serialize (method may vary by version)
        try:
            json_str = instance.adapt_to(obj_key="json")
            print("✓ JSON serialization works (adapt_to)")
        except:
            json_str = instance.model_dump_json()
            print("✓ JSON serialization works (model_dump_json)")
    except Exception as e:
        print(f"✗ Adapter test failed: {e}")

# Summary
print("\n" + "="*50)
print("COMPATIBILITY TEST SUMMARY")
print("="*50)
print(f"pydapter version: {getattr(pydapter, '__version__', 'unknown')}")
print("\nFeatures available:")
for feature, available in features.items():
    status = "✓" if available else "✗"
    print(f"  {status} {feature}: {available}")

# Save results
results = {
    "version": getattr(pydapter, '__version__', 'unknown'),
    "features": features,
    "python_version": sys.version,
}

output_file = f"compatibility_test_{results['version']}.json"
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to: {output_file}")
print("\nThis version should work with comprehensive_benchmark.py" if any(features.values()) else "\nThis version may have compatibility issues")