#!/usr/bin/env python3
"""
Migrate from protocols to traits system.

This script handles the migration from the deprecated protocols folder
to the new traits system.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Mapping from old protocol names to new trait names
PROTOCOL_TO_TRAIT_MAP = {
    # Core protocols
    "IdentifiableMixin": "Identifiable",
    "TemporalMixin": "Temporal", 
    "AuditableMixin": "Auditable",
    "HashableMixin": "Hashable",
    
    # Behavioral protocols
    "OperableMixin": "Operable",
    "ObservableMixin": "Observable",
    "ValidatableMixin": "Validatable",
    "SerializableMixin": "Serializable",
    
    # Advanced protocols
    "ComposableMixin": "Composable",
    "ExtensibleMixin": "Extensible",
    "CacheableMixin": "Cacheable",
    "IndexableMixin": "Indexable",
    
    # Performance protocols
    "LazyMixin": "Lazy",
    "StreamingMixin": "Streaming",
    "PartialMixin": "Partial",
    
    # Security protocols
    "SecuredMixin": "Secured",
    "CapabilityAwareMixin": "CapabilityAware",
    
    # Other protocols that need special handling
    "CryptographicalMixin": "Secured",  # Map to Secured trait
    "EmbeddableMixin": "Serializable",  # Map to Serializable trait
    "InvokableMixin": "Operable",  # Map to Operable trait
    "SoftDeletableMixin": "Temporal",  # Map to Temporal trait
    
    # Protocol types
    "ProtocolType": "Trait",
    "IDENTIFIABLE": "Trait.IDENTIFIABLE",
    "TEMPORAL": "Trait.TEMPORAL",
    "EMBEDDABLE": "Trait.SERIALIZABLE",
    "AUDITABLE": "Trait.AUDITABLE",
}

# Import replacements
IMPORT_REPLACEMENTS = {
    r"from\s+pydapter\.protocols\s+import\s+Event,\s*as_event": 
        "from pydapter.traits.events import Event, as_event",
    
    r"from\s+pydapter\.protocols\s+import\s+([A-Za-z_,\s]+)":
        lambda m: f"from pydapter.traits.protocols import {m.group(1)}",
        
    r"from\s+pydapter\.protocols\.(\w+)\s+import":
        lambda m: f"from pydapter.traits.protocols import",
        
    r"import\s+pydapter\.protocols":
        "import pydapter.traits",
}


class ProtocolMigrator:
    """Handle migration from protocols to traits."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_root = project_root / "src"
        self.files_modified: List[Path] = []
        self.errors: List[Tuple[Path, str]] = []
        
    def find_python_files(self) -> List[Path]:
        """Find all Python files that might need migration."""
        files = []
        for root, _, filenames in os.walk(self.src_root):
            for filename in filenames:
                if filename.endswith('.py'):
                    path = Path(root) / filename
                    # Skip the protocols folder itself and traits folder
                    if 'protocols' not in str(path) and 'traits' not in str(path):
                        files.append(path)
        return files
    
    def migrate_file(self, file_path: Path) -> bool:
        """Migrate a single file. Returns True if modified."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            original_content = content
            
            # Apply import replacements
            for pattern, replacement in IMPORT_REPLACEMENTS.items():
                if callable(replacement):
                    content = re.sub(pattern, replacement, content)
                else:
                    content = re.sub(pattern, replacement, content)
            
            # Replace protocol names with trait names
            for old_name, new_name in PROTOCOL_TO_TRAIT_MAP.items():
                # Word boundary to avoid partial matches
                content = re.sub(rf'\b{old_name}\b', new_name, content)
            
            # Special handling for Event class
            if "Event" in content and "traits.events" not in content:
                # Check if Event is used as a class (not imported from traits)
                if re.search(r'\bEvent\b(?!\s*[,)])', content):
                    # Add import if not present
                    if "from pydapter.traits.events import Event" not in content:
                        # Find the right place to add import
                        import_match = re.search(r'(from pydapter\.\w+ import.*\n)', content)
                        if import_match:
                            insert_pos = import_match.end()
                            content = (
                                content[:insert_pos] + 
                                "from pydapter.traits.events import Event\n" +
                                content[insert_pos:]
                            )
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                self.files_modified.append(file_path)
                return True
                
        except Exception as e:
            self.errors.append((file_path, str(e)))
            
        return False
    
    def create_event_module(self):
        """Create the event module in traits if it doesn't exist."""
        event_path = self.src_root / "pydapter" / "traits" / "events.py"
        
        if not event_path.exists():
            event_content = '''"""
Event trait and utilities.

This module provides the Event class and related functionality,
migrated from the protocols system to the traits system.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from typing import Any

from pydantic import JsonValue

from pydapter.async_core import AsyncAdapter
from pydapter.core import Adapter
from pydapter.fields import (
    DATETIME,
    EMBEDDING,
    EXECUTION,
    ID_FROZEN,
    PARAMS,
    Embedding,
    create_model,
)
from pydapter.fields.template import FieldTemplate
from pydapter.traits.protocols import (
    Identifiable,
    Temporal,
    Serializable,
    Observable,
    Auditable,
)

# Base event fields
BASE_EVENT_FIELDS = {
    "id": ID_FROZEN,
    "created_at": DATETIME,
    "updated_at": DATETIME,
    "embedding": EMBEDDING,
    "execution": EXECUTION,
    "request": PARAMS,
    "content": FieldTemplate(
        base_type=JsonValue,
        description="Content of the event",
        nullable=True,
        default=None,
    ),
    "event_type": FieldTemplate(
        base_type=str,
        description="Type of the event",
        nullable=True,
        default=None,
        validator=lambda x: x or "Event",
    ),
    "sha256": FieldTemplate(
        base_type=str | None,
        description="SHA256 hash of the event content",
        nullable=True,
        default=None,
    ),
}

# Create Event model using traits
Event = create_model(
    "Event",
    fields=BASE_EVENT_FIELDS,
    bases=(Identifiable, Temporal, Serializable, Observable, Auditable),
)


def as_event(
    func: Callable[..., Any] | None = None,
    *,
    event_type: str | None = None,
    capture_result: bool = True,
    capture_args: bool = True,
) -> Callable[..., Any]:
    """
    Decorator to convert function calls into Event objects.
    
    Args:
        func: The function to decorate
        event_type: Type of event to create
        capture_result: Whether to capture the function result
        capture_args: Whether to capture function arguments
        
    Returns:
        Decorated function that creates Event objects
    """
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create event data
            event_data = {
                "event_type": event_type or f.__name__,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            
            if capture_args:
                event_data["request"] = {
                    "args": args,
                    "kwargs": kwargs,
                }
            
            # Execute function
            try:
                result = f(*args, **kwargs)
                
                if capture_result:
                    event_data["content"] = result
                    
                # Create event
                event = Event(**event_data)
                
                # Store event on result if possible
                if hasattr(result, "__event__"):
                    result.__event__ = event
                    
                return result
                
            except Exception as e:
                event_data["content"] = {
                    "error": str(e),
                    "type": type(e).__name__,
                }
                event = Event(**event_data)
                raise
                
        # Handle async functions
        @wraps(f)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Similar to sync wrapper but async
            event_data = {
                "event_type": event_type or f.__name__,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            
            if capture_args:
                event_data["request"] = {
                    "args": args,
                    "kwargs": kwargs,
                }
            
            try:
                result = await f(*args, **kwargs)
                
                if capture_result:
                    event_data["content"] = result
                    
                event = Event(**event_data)
                
                if hasattr(result, "__event__"):
                    result.__event__ = event
                    
                return result
                
            except Exception as e:
                event_data["content"] = {
                    "error": str(e),
                    "type": type(e).__name__,
                }
                event = Event(**event_data)
                raise
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(f):
            return async_wrapper
        else:
            return wrapper
    
    # Handle being called with or without parentheses
    if func is None:
        return decorator
    else:
        return decorator(func)


__all__ = ["Event", "as_event", "BASE_EVENT_FIELDS"]
'''
            with open(event_path, 'w') as f:
                f.write(event_content)
            print(f"Created {event_path}")
    
    def run_migration(self) -> Dict[str, Any]:
        """Run the full migration."""
        print("Starting migration from protocols to traits...")
        
        # Create event module
        self.create_event_module()
        
        # Find and migrate files
        files = self.find_python_files()
        print(f"Found {len(files)} Python files to check")
        
        for file_path in files:
            self.migrate_file(file_path)
        
        # Summary
        print(f"\nMigration complete!")
        print(f"Files modified: {len(self.files_modified)}")
        print(f"Errors: {len(self.errors)}")
        
        if self.files_modified:
            print("\nModified files:")
            for path in self.files_modified:
                print(f"  - {path.relative_to(self.project_root)}")
        
        if self.errors:
            print("\nErrors:")
            for path, error in self.errors:
                print(f"  - {path.relative_to(self.project_root)}: {error}")
        
        return {
            "files_modified": len(self.files_modified),
            "errors": len(self.errors),
            "modified_files": [str(p.relative_to(self.project_root)) for p in self.files_modified],
            "error_details": [(str(p.relative_to(self.project_root)), e) for p, e in self.errors],
        }


def main():
    """Run the migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate from protocols to traits")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory"
    )
    
    args = parser.parse_args()
    
    migrator = ProtocolMigrator(args.project_root)
    
    if args.dry_run:
        print("DRY RUN - No files will be modified")
        # TODO: Implement dry run
    else:
        results = migrator.run_migration()
        
        # Save results
        import json
        with open("migration_results.json", "w") as f:
            json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()