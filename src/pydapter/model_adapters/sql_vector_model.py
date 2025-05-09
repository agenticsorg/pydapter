# sql_vector_model.py
"""
This module is deprecated. Use pg_vector_model.py instead.
"""

import warnings

from .pg_vector_model import PGVectorModelAdapter

warnings.warn(
    "SQLVectorModelAdapter is deprecated and will be removed in a future version. "
    "Use PGVectorModelAdapter instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export PGVectorModelAdapter as SQLVectorModelAdapter for backward compatibility
SQLVectorModelAdapter = PGVectorModelAdapter
