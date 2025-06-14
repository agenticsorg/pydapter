#!/usr/bin/env python3
"""
Benchmark different versions of pydapter to compare performance.

This script creates isolated environments for each version and runs standardized benchmarks.
"""

import subprocess
import sys
import tempfile
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import argparse
import venv

# Versions to compare
VERSIONS = ["0.2.0", "0.2.1", "0.2.2", "0.2.3", "0.3.0", "0.3.1", "0.3.2"]
CURRENT_VERSION = "current"  # Will use the local development version

# Benchmark code that works across versions
BENCHMARK_CODE = '''
import time
import uuid
import json
from typing import Dict, List, Any
import statistics

# Try to import from different locations (for compatibility)
try:
    from pydantic import BaseModel
    from pydapter import Adaptable
    from pydapter.fields import Field, FieldTemplate, create_model
    from pydapter.adapters import JsonAdapter
except ImportError:
    # Older versions might have different import paths
    from pydantic import BaseModel
    from pydapter.core import Adaptable
    from pydapter.fields import Field, create_model
    from pydapter.adapters import JsonAdapter
    FieldTemplate = None  # Not available in older versions

def benchmark_field_creation():
    """Benchmark field creation"""
    times = []
    
    for _ in range(1000):
        start = time.perf_counter()
        
        # Try new FieldTemplate if available, fallback to Field
        if FieldTemplate is not None and hasattr(FieldTemplate, '__init__'):
            try:
                # Try kwargs approach first (0.3.3+)
                field = FieldTemplate(
                    base_type=str,
                    description="Test field",
                    default="default"
                )
            except TypeError:
                # Fallback to older initialization
                field = FieldTemplate(str).with_description("Test field").with_default("default")
        else:
            # Use legacy Field
            field = Field(
                name="test_field",
                annotation=str,
                description="Test field",
                default="default"
            )
        
        end = time.perf_counter()
        times.append((end - start) * 1000)  # ms
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0
    }

def benchmark_model_creation():
    """Benchmark model creation"""
    times = []
    
    for _ in range(500):
        start = time.perf_counter()
        
        # Create fields based on what's available
        if FieldTemplate is not None and hasattr(FieldTemplate, '__init__'):
            try:
                # Try new approach (0.3.3+)
                fields = {
                    "id": FieldTemplate(uuid.UUID, default=uuid.uuid4),
                    "name": FieldTemplate(str),
                    "value": FieldTemplate(float, default=0.0)
                }
            except TypeError:
                # Try older FieldTemplate approach
                try:
                    fields = {
                        "id": FieldTemplate(uuid.UUID).with_default(uuid.uuid4),
                        "name": FieldTemplate(str),
                        "value": FieldTemplate(float).with_default(0.0)
                    }
                except:
                    # Fallback to Field
                    fields = [
                        Field(name="id", annotation=uuid.UUID, default_factory=uuid.uuid4),
                        Field(name="name", annotation=str),
                        Field(name="value", annotation=float, default=0.0)
                    ]
        else:
            # Use legacy Field
            fields = [
                Field(name="id", annotation=uuid.UUID, default_factory=uuid.uuid4),
                Field(name="name", annotation=str),
                Field(name="value", annotation=float, default=0.0)
            ]
        
        Model = create_model("TestModel", fields=fields)
        
        end = time.perf_counter()
        times.append((end - start) * 1000)  # ms
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0
    }

def benchmark_serialization():
    """Benchmark JSON serialization"""
    # Create a model
    class TestModel(Adaptable, BaseModel):
        id: uuid.UUID
        name: str
        value: float
        tags: List[str]
        metadata: Dict[str, Any]
    
    # Register adapter
    TestModel.register_adapter(JsonAdapter)
    
    # Create test instances
    instances = [
        TestModel(
            id=uuid.uuid4(),
            name=f"Item {i}",
            value=i * 1.5,
            tags=[f"tag{j}" for j in range(5)],
            metadata={"index": i, "category": f"cat{i % 3}"}
        )
        for i in range(100)
    ]
    
    times = []
    
    for _ in range(100):
        start = time.perf_counter()
        
        # Serialize
        json_data = json.dumps([inst.model_dump() for inst in instances])
        
        end = time.perf_counter()
        times.append((end - start) * 1000)  # ms
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0
    }

def benchmark_deserialization():
    """Benchmark JSON deserialization"""
    # Create a model
    class TestModel(Adaptable, BaseModel):
        id: uuid.UUID
        name: str
        value: float
        tags: List[str]
        metadata: Dict[str, Any]
    
    # Create test data
    test_data = [
        {
            "id": str(uuid.uuid4()),
            "name": f"Item {i}",
            "value": i * 1.5,
            "tags": [f"tag{j}" for j in range(5)],
            "metadata": {"index": i, "category": f"cat{i % 3}"}
        }
        for i in range(100)
    ]
    
    json_data = json.dumps(test_data)
    
    times = []
    
    for _ in range(100):
        start = time.perf_counter()
        
        # Deserialize
        data = json.loads(json_data)
        instances = [TestModel.model_validate(item) for item in data]
        
        end = time.perf_counter()
        times.append((end - start) * 1000)  # ms
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0
    }

# Run all benchmarks
results = {
    "field_creation": benchmark_field_creation(),
    "model_creation": benchmark_model_creation(),
    "serialization": benchmark_serialization(),
    "deserialization": benchmark_deserialization()
}

print(json.dumps(results))
'''


class VersionBenchmarker:
    def __init__(self, versions: List[str], verbose: bool = False):
        self.versions = versions
        self.verbose = verbose
        self.results: Dict[str, Dict[str, Any]] = {}
        
    def log(self, message: str):
        """Log message if verbose mode is on"""
        if self.verbose:
            print(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    def create_venv(self, path: Path) -> None:
        """Create a virtual environment"""
        self.log(f"Creating virtual environment at {path}")
        venv.create(path, with_pip=True)
        
    def get_pip_cmd(self, venv_path: Path) -> List[str]:
        """Get pip command for the virtual environment"""
        if sys.platform == "win32":
            return [str(venv_path / "Scripts" / "python.exe"), "-m", "pip"]
        else:
            return [str(venv_path / "bin" / "python"), "-m", "pip"]
    
    def get_python_cmd(self, venv_path: Path) -> List[str]:
        """Get python command for the virtual environment"""
        if sys.platform == "win32":
            return [str(venv_path / "Scripts" / "python.exe")]
        else:
            return [str(venv_path / "bin" / "python")]
    
    def install_version(self, venv_path: Path, version: str) -> bool:
        """Install a specific version of pydapter"""
        pip_cmd = self.get_pip_cmd(venv_path)
        
        try:
            # Upgrade pip first
            self.log("Upgrading pip...")
            subprocess.run(pip_cmd + ["install", "--upgrade", "pip"], 
                         capture_output=True, check=True)
            
            if version == CURRENT_VERSION:
                # Install from current directory
                self.log("Installing current development version...")
                subprocess.run(pip_cmd + ["install", "-e", "."], 
                             capture_output=True, check=True, cwd=Path.cwd())
            else:
                # Install specific version from PyPI
                self.log(f"Installing pydapter=={version}...")
                subprocess.run(pip_cmd + ["install", f"pydapter=={version}"], 
                             capture_output=True, check=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to install version {version}: {e}")
            if self.verbose:
                print(f"STDOUT: {e.stdout.decode()}")
                print(f"STDERR: {e.stderr.decode()}")
            return False
    
    def run_benchmark(self, venv_path: Path, version: str) -> Dict[str, Any]:
        """Run benchmark in the virtual environment"""
        python_cmd = self.get_python_cmd(venv_path)
        script_path = None
        
        try:
            self.log(f"Running benchmarks for version {version}...")
            
            # Write benchmark script to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(BENCHMARK_CODE)
                script_path = f.name
            
            # Run benchmark
            result = subprocess.run(
                python_cmd + [script_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse results
            results = json.loads(result.stdout)
            
            return results
            
        except subprocess.CalledProcessError as e:
            self.log(f"Benchmark failed for version {version}: {e}")
            if self.verbose:
                print(f"STDOUT: {e.stdout}")
                print(f"STDERR: {e.stderr}")
            return {}
        except json.JSONDecodeError as e:
            self.log(f"Failed to parse benchmark results for version {version}: {e}")
            return {}
        finally:
            # Clean up script file if it exists
            if script_path and Path(script_path).exists():
                try:
                    Path(script_path).unlink()
                except:
                    pass
    
    def benchmark_version(self, version: str) -> Dict[str, Any]:
        """Benchmark a single version"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            venv_path = Path(tmp_dir) / "venv"
            
            # Create virtual environment
            self.create_venv(venv_path)
            
            # Install version
            if not self.install_version(venv_path, version):
                return {"error": f"Failed to install version {version}"}
            
            # Run benchmark
            results = self.run_benchmark(venv_path, version)
            
            if not results:
                return {"error": f"Failed to run benchmarks for version {version}"}
            
            return results
    
    def run_all_benchmarks(self):
        """Run benchmarks for all versions"""
        print(f"Benchmarking {len(self.versions)} versions of pydapter...")
        print("This may take several minutes...\n")
        
        for version in self.versions:
            print(f"Benchmarking version {version}...")
            self.results[version] = self.benchmark_version(version)
            
            # Print summary
            if "error" in self.results[version]:
                print(f"  ❌ {self.results[version]['error']}")
            else:
                field_time = self.results[version].get("field_creation", {}).get("mean", "N/A")
                model_time = self.results[version].get("model_creation", {}).get("mean", "N/A")
                print(f"  ✓ Field creation: {field_time:.3f} ms")
                print(f"  ✓ Model creation: {model_time:.3f} ms")
            print()
    
    def generate_report(self) -> str:
        """Generate a markdown report of the results"""
        report = ["# Pydapter Version Performance Comparison\n"]
        report.append(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Summary table
        report.append("## Summary\n")
        report.append("| Version | Field Creation (ms) | Model Creation (ms) | Serialization (ms) | Deserialization (ms) |")
        report.append("|---------|-------------------|-------------------|------------------|---------------------|")
        
        for version in self.versions:
            if "error" in self.results.get(version, {}):
                report.append(f"| {version} | Error | Error | Error | Error |")
            else:
                result = self.results.get(version, {})
                field = result.get("field_creation", {}).get("mean", "N/A")
                model = result.get("model_creation", {}).get("mean", "N/A")
                ser = result.get("serialization", {}).get("mean", "N/A")
                deser = result.get("deserialization", {}).get("mean", "N/A")
                
                field_str = f"{field:.3f}" if isinstance(field, (int, float)) else field
                model_str = f"{model:.3f}" if isinstance(model, (int, float)) else model
                ser_str = f"{ser:.3f}" if isinstance(ser, (int, float)) else ser
                deser_str = f"{deser:.3f}" if isinstance(deser, (int, float)) else deser
                
                report.append(f"| {version} | {field_str} | {model_str} | {ser_str} | {deser_str} |")
        
        # Performance improvements
        report.append("\n## Performance Improvements\n")
        
        # Calculate improvements if we have valid data
        valid_versions = [v for v in self.versions if "error" not in self.results.get(v, {})]
        if len(valid_versions) >= 2:
            first = valid_versions[0]
            last = valid_versions[-1]
            
            first_result = self.results[first]
            last_result = self.results[last]
            
            for metric in ["field_creation", "model_creation", "serialization", "deserialization"]:
                first_time = first_result.get(metric, {}).get("mean")
                last_time = last_result.get(metric, {}).get("mean")
                
                if first_time and last_time and isinstance(first_time, (int, float)) and isinstance(last_time, (int, float)):
                    improvement = ((first_time - last_time) / first_time) * 100
                    if improvement > 0:
                        report.append(f"- **{metric.replace('_', ' ').title()}**: {improvement:.1f}% faster")
                    else:
                        report.append(f"- **{metric.replace('_', ' ').title()}**: {abs(improvement):.1f}% slower")
        
        # Raw results
        report.append("\n## Raw Results\n")
        report.append("```json")
        report.append(json.dumps(self.results, indent=2))
        report.append("```")
        
        return "\n".join(report)
    
    def save_results(self, output_path: Path):
        """Save results to JSON and markdown files"""
        # Save JSON
        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to {json_path}")
        
        # Save markdown report
        md_path = output_path.with_suffix('.md')
        with open(md_path, 'w') as f:
            f.write(self.generate_report())
        print(f"Report saved to {md_path}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark different versions of pydapter")
    parser.add_argument(
        "--versions", 
        nargs="+", 
        default=VERSIONS + [CURRENT_VERSION],
        help="Versions to benchmark"
    )
    parser.add_argument(
        "--output", 
        type=Path, 
        default=Path("benchmark_results"),
        help="Output path for results (without extension)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Create benchmarker
    benchmarker = VersionBenchmarker(args.versions, verbose=args.verbose)
    
    # Run benchmarks
    benchmarker.run_all_benchmarks()
    
    # Save results
    benchmarker.save_results(args.output)
    
    # Print summary
    print("\n" + "="*60)
    print("BENCHMARK COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()