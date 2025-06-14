#!/usr/bin/env python3
"""
Comprehensive Pydapter Benchmark Script

This script benchmarks various high-level functionalities of pydapter.
Run this on different versions and collect the results.

Version Compatibility:
- 0.2.x: Field class, basic adapters
- 0.3.0-0.3.2: FieldTemplate with method chaining
- 0.3.3+: FieldTemplate with kwargs, traits system

The script automatically detects available features and runs appropriate benchmarks
to ensure fair comparison across versions.

Usage:
    python comprehensive_benchmark.py [--output results.json] [--iterations 5000]
"""

import time
import uuid
import json
import gc
import sys
import argparse
import statistics
from typing import Dict, List, Any, Callable
from datetime import datetime, timezone
from pathlib import Path

# Try to get version info
try:
    import pydapter
    PYDAPTER_VERSION = getattr(pydapter, '__version__', 'unknown')
except:
    PYDAPTER_VERSION = 'unknown'

# Import pydapter components
try:
    from pydantic import BaseModel, __version__ as PYDANTIC_VERSION
    from pydapter import Adaptable
    from pydapter.fields import Field, FieldTemplate, create_model
    from pydapter.adapters import JsonAdapter, CsvAdapter, TomlAdapter
    
    # Check what's available
    HAS_FIELD = True
    HAS_FIELDTEMPLATE = hasattr(FieldTemplate, '__init__')
    
    # Try to import pre-built templates
    try:
        from pydapter.fields import (
            ID_FROZEN, ID_MUTABLE, DATETIME, 
            JSON_TEMPLATE, EMBEDDING, METADATA_TEMPLATE
        )
        HAS_TEMPLATES = True
    except ImportError:
        HAS_TEMPLATES = False
    
    # Try to import traits
    try:
        from pydapter.traits import (
            Trait, TraitRegistry, TraitComposer,
            compose, implement, as_trait, get_global_registry
        )
        from pydapter.traits.protocols import (
            Identifiable, Temporal, Serializable,
            Observable, Auditable
        )
        HAS_TRAITS = True
    except ImportError:
        HAS_TRAITS = False
        
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def format_time(value: float, unit: str) -> str:
    """Format time value with appropriate precision based on unit."""
    if unit == "ns":
        if value < 10:
            return f"{value:.1f}"
        else:
            return f"{value:.0f}"
    elif unit == "μs":
        if value < 10:
            return f"{value:.2f}"
        elif value < 100:
            return f"{value:.1f}"
        else:
            return f"{value:.0f}"
    else:  # ms
        if value < 10:
            return f"{value:.3f}"
        elif value < 100:
            return f"{value:.2f}"
        else:
            return f"{value:.1f}"


class BenchmarkRunner:
    """Run comprehensive benchmarks on pydapter"""
    
    def __init__(self, iterations: int = 1000):
        self.iterations = iterations
        
        # Detect actual version from package
        try:
            import pydapter
            actual_version = getattr(pydapter, '__version__', PYDAPTER_VERSION)
        except:
            actual_version = PYDAPTER_VERSION
            
        self.results = {
            "metadata": {
                "pydapter_version": actual_version,
                "pydantic_version": PYDANTIC_VERSION,
                "python_version": sys.version,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "iterations": iterations,
                "features": {
                    "has_field": HAS_FIELD,
                    "has_fieldtemplate": HAS_FIELDTEMPLATE,
                    "has_templates": HAS_TEMPLATES,
                    "has_traits": HAS_TRAITS
                },
                "benchmark_version": "2.0"  # Version of this benchmark script
            },
            "benchmarks": {}
        }
    
    def benchmark(self, func: Callable, name: str, iterations: int = None) -> Dict[str, float]:
        """Run a benchmark and collect statistics"""
        iterations = iterations or self.iterations
        
        # Warmup
        for _ in range(min(10, iterations // 10)):
            func()
        
        # Force GC
        gc.collect()
        
        # Run benchmark
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append(end - start)  # Keep in seconds for now
        
        # Determine appropriate unit based on median time
        median_time = statistics.median(times)
        if median_time < 1e-6:  # Less than 1 microsecond
            multiplier = 1e9  # Convert to nanoseconds
            unit = "ns"
        elif median_time < 1e-3:  # Less than 1 millisecond
            multiplier = 1e6  # Convert to microseconds
            unit = "μs"
        else:  # 1 millisecond or more
            multiplier = 1e3  # Convert to milliseconds
            unit = "ms"
        
        # Convert all times to the appropriate unit
        times = [t * multiplier for t in times]
        
        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "p95": sorted(times)[int(len(times) * 0.95)],
            "p99": sorted(times)[int(len(times) * 0.99)],
            "unit": unit
        }
    
    def run_field_benchmarks(self):
        """Benchmark field creation and manipulation"""
        print("Running field benchmarks...")
        
        # 1. Basic field creation
        if HAS_FIELD:
            def create_field_legacy():
                return Field(
                    name="test_field",
                    annotation=str,
                    default="default",
                    description="Test field"
                )
            
            self.results["benchmarks"]["field_creation_legacy"] = self.benchmark(
                create_field_legacy, "Field Creation (Legacy)"
            )
        
        if HAS_FIELDTEMPLATE:
            # Try different FieldTemplate creation patterns
            
            # Method chaining (older versions)
            try:
                def create_field_chaining():
                    return (
                        FieldTemplate(str)
                        .with_description("Test field")
                        .with_default("default")
                    )
                
                self.results["benchmarks"]["field_creation_chaining"] = self.benchmark(
                    create_field_chaining, "Field Creation (Chaining)"
                )
            except:
                pass
            
            # Kwargs pattern (newer versions)
            try:
                def create_field_kwargs():
                    return FieldTemplate(
                        base_type=str,
                        description="Test field",
                        default="default"
                    )
                
                self.results["benchmarks"]["field_creation_kwargs"] = self.benchmark(
                    create_field_kwargs, "Field Creation (Kwargs)"
                )
            except:
                pass
        
        # 2. Complex field creation
        if HAS_FIELDTEMPLATE:
            try:
                def create_complex_field():
                    return FieldTemplate(
                        base_type=str,
                        nullable=True,
                        listable=True,
                        description="Complex field",
                        title="Complex",
                        frozen=True,
                        default=[]
                    )
                
                self.results["benchmarks"]["field_creation_complex"] = self.benchmark(
                    create_complex_field, "Complex Field Creation", iterations=500
                )
            except:
                # Try method chaining for older versions
                try:
                    def create_complex_field_chain():
                        return (
                            FieldTemplate(str)
                            .as_nullable()
                            .as_listable()
                            .with_description("Complex field")
                            .with_title("Complex")
                            .with_frozen(True)
                            .with_default([])
                        )
                    
                    self.results["benchmarks"]["field_creation_complex"] = self.benchmark(
                        create_complex_field_chain, "Complex Field Creation", iterations=500
                    )
                except:
                    pass
    
    def run_model_benchmarks(self):
        """Benchmark model creation and instantiation"""
        print("Running model benchmarks...")
        
        # 1. Simple model creation
        def create_simple_model():
            if HAS_FIELDTEMPLATE:
                try:
                    # Try kwargs approach first
                    fields = {
                        "id": FieldTemplate(uuid.UUID, default=uuid.uuid4),
                        "name": FieldTemplate(str),
                        "value": FieldTemplate(float, default=0.0)
                    }
                except:
                    # Fallback to method chaining
                    fields = {
                        "id": FieldTemplate(uuid.UUID).with_default(uuid.uuid4),
                        "name": FieldTemplate(str),
                        "value": FieldTemplate(float).with_default(0.0)
                    }
            else:
                fields = [
                    Field(name="id", annotation=uuid.UUID, default_factory=uuid.uuid4),
                    Field(name="name", annotation=str),
                    Field(name="value", annotation=float, default=0.0)
                ]
            
            return create_model("SimpleModel", fields=fields)
        
        self.results["benchmarks"]["model_creation_simple"] = self.benchmark(
            create_simple_model, "Simple Model Creation", iterations=500
        )
        
        # 2. Complex model creation
        def create_complex_model():
            class ComplexModel(Adaptable, BaseModel):
                id: uuid.UUID
                name: str
                value: float
                tags: List[str]
                metadata: Dict[str, Any]
                created_at: datetime
                optional_field: str | None = None
            
            return ComplexModel
        
        self.results["benchmarks"]["model_creation_complex"] = self.benchmark(
            create_complex_model, "Complex Model Creation", iterations=500
        )
        
        # 3. Model instantiation
        SimpleModel = create_simple_model()
        ComplexModel = create_complex_model()
        
        def instantiate_simple():
            return SimpleModel(name="test", value=1.0)
        
        def instantiate_complex():
            return ComplexModel(
                id=uuid.uuid4(),
                name="test",
                value=1.0,
                tags=["tag1", "tag2"],
                metadata={"key": "value"},
                created_at=datetime.now(timezone.utc)
            )
        
        self.results["benchmarks"]["model_instantiation_simple"] = self.benchmark(
            instantiate_simple, "Simple Model Instantiation"
        )
        
        self.results["benchmarks"]["model_instantiation_complex"] = self.benchmark(
            instantiate_complex, "Complex Model Instantiation"
        )
        
        # 4. Model with pre-built templates (if available)
        if HAS_TEMPLATES:
            def create_template_model():
                fields = {
                    "id": ID_FROZEN,
                    "created_at": DATETIME,
                    "metadata": JSON_TEMPLATE,
                    "embedding": EMBEDDING
                }
                return create_model("TemplateModel", fields=fields)
            
            self.results["benchmarks"]["model_creation_templates"] = self.benchmark(
                create_template_model, "Model Creation (Pre-built Templates)", iterations=500
            )
    
    def run_adapter_benchmarks(self):
        """Benchmark adapter operations"""
        print("Running adapter benchmarks...")
        
        # Create test models
        class TestModel(Adaptable, BaseModel):
            id: uuid.UUID
            name: str
            value: float
            tags: List[str]
            metadata: Dict[str, Any]
        
        class SimpleModel(Adaptable, BaseModel):
            id: str
            name: str
            value: float
        
        # Register adapters
        TestModel.register_adapter(JsonAdapter)
        TestModel.register_adapter(TomlAdapter)
        SimpleModel.register_adapter(CsvAdapter)
        
        # Create test data
        test_instance = TestModel(
            id=uuid.uuid4(),
            name="Test Item",
            value=42.0,
            tags=["tag1", "tag2", "tag3"],
            metadata={"key": "value", "count": 10}
        )
        
        test_instances = [
            TestModel(
                id=uuid.uuid4(),
                name=f"Item {i}",
                value=i * 1.5,
                tags=[f"tag{j}" for j in range(5)],
                metadata={"index": i, "category": f"cat{i % 3}"}
            )
            for i in range(100)
        ]
        
        simple_instance = SimpleModel(
            id=str(uuid.uuid4()),
            name="Simple Item",
            value=42.0
        )
        
        simple_instances = [
            SimpleModel(
                id=str(uuid.uuid4()),
                name=f"Item {i}",
                value=i * 1.5
            )
            for i in range(100)
        ]
        
        # 1. JSON serialization
        def json_serialize_single():
            # Use model_dump_json to handle UUID/datetime serialization
            return test_instance.model_dump_json()
        
        def json_serialize_many():
            # Manually serialize to handle complex types
            return json.dumps([inst.model_dump(mode='json') for inst in test_instances])
        
        self.results["benchmarks"]["json_serialize_single"] = self.benchmark(
            json_serialize_single, "JSON Serialize (Single)"
        )
        
        self.results["benchmarks"]["json_serialize_many"] = self.benchmark(
            json_serialize_many, "JSON Serialize (100 items)", iterations=100
        )
        
        # 2. JSON deserialization
        json_single = test_instance.model_dump_json()
        json_many = json.dumps([inst.model_dump(mode='json') for inst in test_instances])
        
        def json_deserialize_single():
            return TestModel.model_validate_json(json_single)
        
        def json_deserialize_many():
            data = json.loads(json_many)
            return [TestModel.model_validate(item) for item in data]
        
        self.results["benchmarks"]["json_deserialize_single"] = self.benchmark(
            json_deserialize_single, "JSON Deserialize (Single)"
        )
        
        self.results["benchmarks"]["json_deserialize_many"] = self.benchmark(
            json_deserialize_many, "JSON Deserialize (100 items)", iterations=100
        )
        
        # 3. CSV operations
        def csv_serialize_many():
            return CsvAdapter.to_obj(simple_instances, many=True)
        
        csv_data = CsvAdapter.to_obj(simple_instances, many=True)
        
        def csv_deserialize_many():
            return SimpleModel.adapt_from(csv_data, obj_key="csv", many=True)
        
        self.results["benchmarks"]["csv_serialize_many"] = self.benchmark(
            csv_serialize_many, "CSV Serialize (100 items)", iterations=100
        )
        
        self.results["benchmarks"]["csv_deserialize_many"] = self.benchmark(
            csv_deserialize_many, "CSV Deserialize (100 items)", iterations=100
        )
        
        # 4. TOML operations
        import toml
        
        def toml_serialize_single():
            # Convert to dict first to handle complex types
            return toml.dumps(test_instance.model_dump(mode='json'))
        
        toml_data = toml.dumps(test_instance.model_dump(mode='json'))
        
        def toml_deserialize_single():
            data = toml.loads(toml_data)
            return TestModel.model_validate(data)
        
        self.results["benchmarks"]["toml_serialize_single"] = self.benchmark(
            toml_serialize_single, "TOML Serialize (Single)", iterations=500
        )
        
        self.results["benchmarks"]["toml_deserialize_single"] = self.benchmark(
            toml_deserialize_single, "TOML Deserialize (Single)", iterations=500
        )
    
    def run_validation_benchmarks(self):
        """Benchmark validation operations"""
        print("Running validation benchmarks...")
        
        # Create models with validators
        if HAS_FIELDTEMPLATE:
            try:
                # Try to create validator
                def validate_positive(x):
                    return x > 0
                
                def validate_email(x):
                    return "@" in x and "." in x
                
                fields = {
                    "age": FieldTemplate(int, validator=validate_positive),
                    "email": FieldTemplate(str, validator=validate_email),
                    "score": FieldTemplate(float, validator=validate_positive)
                }
                
                ValidatedModel = create_model("ValidatedModel", fields=fields)
                
                def validate_valid():
                    return ValidatedModel(age=25, email="test@example.com", score=95.5)
                
                self.results["benchmarks"]["validation_valid"] = self.benchmark(
                    validate_valid, "Validation (Valid Data)"
                )
                
                def validate_invalid():
                    try:
                        ValidatedModel(age=-5, email="invalid", score=-10)
                    except:
                        pass
                
                self.results["benchmarks"]["validation_invalid"] = self.benchmark(
                    validate_invalid, "Validation (Invalid Data)"
                )
            except:
                pass
    
    def run_memory_benchmarks(self):
        """Estimate memory usage patterns"""
        print("Running memory benchmarks...")
        
        # This is a synthetic benchmark to test object creation overhead
        def create_many_fields():
            fields = []
            for i in range(100):
                if HAS_FIELDTEMPLATE:
                    try:
                        field = FieldTemplate(
                            base_type=str,
                            description=f"Field {i}",
                            default=f"default_{i}"
                        )
                    except:
                        field = FieldTemplate(str).with_description(f"Field {i}")
                else:
                    field = Field(
                        name=f"field_{i}",
                        annotation=str,
                        description=f"Field {i}"
                    )
                fields.append(field)
            return fields
        
        self.results["benchmarks"]["memory_many_fields"] = self.benchmark(
            create_many_fields, "Create 100 Fields", iterations=100
        )
        
        # Test model creation with many fields
        def create_large_model():
            fields = {}
            for i in range(50):
                if HAS_FIELDTEMPLATE:
                    try:
                        fields[f"field_{i}"] = FieldTemplate(str, default=f"value_{i}")
                    except:
                        fields[f"field_{i}"] = FieldTemplate(str).with_default(f"value_{i}")
                else:
                    # For legacy, we'd need a different approach
                    pass
            
            if fields:
                return create_model("LargeModel", fields=fields)
        
        if HAS_FIELDTEMPLATE:
            self.results["benchmarks"]["memory_large_model"] = self.benchmark(
                create_large_model, "Create Model with 50 Fields", iterations=50
            )
    
    def run_trait_benchmarks_simple(self):
        """Benchmark basic trait operations without full compliance"""
        if not HAS_TRAITS:
            print("Skipping trait benchmarks (traits not available)")
            return
            
        print("Running trait benchmarks (simplified)...")
        
        # 1. Basic trait import and enum access
        def access_trait_enum():
            return [
                Trait.IDENTIFIABLE,
                Trait.TEMPORAL,
                Trait.SERIALIZABLE,
                Trait.OBSERVABLE,
                Trait.AUDITABLE
            ]
        
        self.results["benchmarks"]["trait_enum_access"] = self.benchmark(
            access_trait_enum, "Trait Enum Access"
        )
        
        # 2. Registry instance creation
        def create_registry():
            return TraitRegistry()
        
        self.results["benchmarks"]["trait_registry_creation"] = self.benchmark(
            create_registry, "Registry Creation", iterations=500
        )
        
        # 3. Trait composition function
        def compose_traits():
            return compose(
                Trait.IDENTIFIABLE,
                Trait.TEMPORAL,
                Trait.SERIALIZABLE
            )
        
        self.results["benchmarks"]["trait_composition"] = self.benchmark(
            compose_traits, "Trait Composition", iterations=500
        )
        
        # 4. Simple class with trait-like attributes
        def create_trait_like_class():
            class TraitLikeClass:
                id = "test_id"
                created_at = datetime.now(timezone.utc)
                updated_at = datetime.now(timezone.utc)
                
                def to_dict(self):
                    return {
                        "id": self.id,
                        "created_at": self.created_at.isoformat(),
                        "updated_at": self.updated_at.isoformat()
                    }
            
            return TraitLikeClass()
        
        self.results["benchmarks"]["trait_like_class"] = self.benchmark(
            create_trait_like_class, "Trait-like Class Creation", iterations=500
        )
        
        print("  Note: Full trait compliance benchmarks skipped (requires complete trait implementation)")
    
    def run_trait_benchmarks(self):
        """Benchmark trait system operations"""
        if not HAS_TRAITS:
            print("Skipping trait benchmarks (traits not available)")
            return
            
        print("Running trait benchmarks...")
        
        # 1. Trait registration (manual)
        def register_trait():
            class TestClass:
                # Add required attributes for IDENTIFIABLE
                @property
                def id(self):
                    return "test_id"
                    
            registry = get_global_registry()
            registry.register_trait(TestClass, Trait.IDENTIFIABLE)
            return TestClass
        
        self.results["benchmarks"]["trait_registration"] = self.benchmark(
            register_trait, "Trait Registration", iterations=500
        )
        
        # 2. Trait checking with proper implementation
        class ProperIdentifiableClass:
            def __init__(self):
                self._id = "test_id"
            
            @property
            def id(self):
                return self._id
        
        # Register the trait
        registry = get_global_registry()
        registry.register_trait(ProperIdentifiableClass, Trait.IDENTIFIABLE)
        instance = ProperIdentifiableClass()
        
        def check_trait_isinstance():
            return isinstance(instance, Identifiable)
        
        self.results["benchmarks"]["trait_isinstance_check"] = self.benchmark(
            check_trait_isinstance, "Trait isinstance Check"
        )
        
        # 3. Trait composition
        def compose_traits():
            return compose(
                Trait.IDENTIFIABLE,
                Trait.TEMPORAL,
                Trait.SERIALIZABLE
            )
        
        self.results["benchmarks"]["trait_composition"] = self.benchmark(
            compose_traits, "Trait Composition", iterations=500
        )
        
        # 4. Create model with traits (skip if not available)
        try:
            from pydapter.traits.composer import generate_model
            
            def create_trait_model():
                return generate_model(
                    "TraitModel",
                    traits=[Trait.IDENTIFIABLE, Trait.TEMPORAL],
                    fields={
                        "name": FieldTemplate(str),
                        "value": FieldTemplate(float)
                    }
                )
            
            self.results["benchmarks"]["trait_model_creation"] = self.benchmark(
                create_trait_model, "Trait Model Creation", iterations=100
            )
        except ImportError:
            print("  Skipping trait model creation (composer not available)")
        
        # 5. Simple trait class creation
        def create_trait_class():
            class SimpleTraitClass:
                @property
                def id(self):
                    return "simple_id"
                
                def to_dict(self):
                    return {"id": self.id}
            
            # Register multiple traits
            registry = get_global_registry()
            registry.register_trait(SimpleTraitClass, Trait.IDENTIFIABLE)
            registry.register_trait(SimpleTraitClass, Trait.SERIALIZABLE)
            
            return SimpleTraitClass
        
        self.results["benchmarks"]["trait_class_creation"] = self.benchmark(
            create_trait_class, "Trait Class Creation", iterations=500
        )
    
    def run_all_benchmarks(self):
        """Run all benchmark suites"""
        print(f"\nRunning Pydapter Benchmarks")
        print(f"Version: {PYDAPTER_VERSION}")
        print(f"Iterations: {self.iterations}")
        print("="*60)
        
        self.run_field_benchmarks()
        self.run_model_benchmarks()
        self.run_adapter_benchmarks()
        self.run_validation_benchmarks()
        self.run_memory_benchmarks()
        
        if HAS_TRAITS:
            self.run_trait_benchmarks_simple()
        
        print("\nBenchmarks completed!")
        
        return self.results
    
    def save_results(self, output_path: Path):
        """Save results to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: {output_path}")
    
    def print_summary(self):
        """Print a summary of results"""
        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)
        
        # Group benchmarks by category for better readability
        categories = {
            "Field Operations": ["field_creation_legacy", "field_creation_chaining", 
                               "field_creation_kwargs", "field_creation_complex"],
            "Model Operations": ["model_creation_simple", "model_creation_complex",
                               "model_creation_templates", "model_instantiation_simple",
                               "model_instantiation_complex"],
            "Serialization": ["json_serialize_single", "json_serialize_many",
                            "json_deserialize_single", "json_deserialize_many",
                            "csv_serialize_many", "csv_deserialize_many",
                            "toml_serialize_single", "toml_deserialize_single"],
            "Validation": ["validation_valid", "validation_invalid"],
            "Memory": ["memory_many_fields", "memory_large_model"],
            "Traits": ["trait_enum_access", "trait_registry_creation",
                      "trait_composition", "trait_like_class"],
        }
        
        # Print by category
        for category, benchmarks in categories.items():
            category_has_results = False
            for bench in benchmarks:
                if bench in self.results["benchmarks"]:
                    category_has_results = True
                    break
            
            if category_has_results:
                print(f"\n{category}:")
                print("-" * len(category))
                
                for bench in benchmarks:
                    if bench in self.results["benchmarks"]:
                        metrics = self.results["benchmarks"][bench]
                        unit = metrics.get('unit', 'ms')
                        
                        # Format the name nicely
                        display_name = bench.replace('_', ' ').title()
                        if len(display_name) > 30:
                            display_name = display_name[:27] + "..."
                        
                        # Print compact format
                        mean_str = format_time(metrics['mean'], unit)
                        median_str = format_time(metrics['median'], unit)
                        stdev_str = format_time(metrics['stdev'], unit)
                        
                        print(f"  {display_name:<30} {mean_str:>8} {unit} "
                              f"(±{stdev_str} {unit}, median: {median_str} {unit})")


def main():
    parser = argparse.ArgumentParser(description="Run comprehensive pydapter benchmarks")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(f"pydapter_benchmark_{PYDAPTER_VERSION}.json"),
        help="Output file path"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5000,
        help="Number of iterations for each benchmark (default: 5000)"
    )
    
    args = parser.parse_args()
    
    # Run benchmarks
    runner = BenchmarkRunner(iterations=args.iterations)
    results = runner.run_all_benchmarks()
    
    # Save results
    runner.save_results(args.output)
    
    # Print summary
    runner.print_summary()


if __name__ == "__main__":
    main()