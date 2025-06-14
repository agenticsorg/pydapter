# Pydapter Performance Analysis Report

Generated from 5 benchmark runs

## Versions Analyzed

- **0.2.3**: Python 3.10.15, Pydantic 2.10.6
- **0.3.0**: Python 3.10.15, Pydantic 2.10.6
- **0.3.1**: Python 3.10.15, Pydantic 2.10.6
- **0.3.2**: Python 3.10.15, Pydantic 2.10.6
- **0.3.3**: Python 3.10.15, Pydantic 2.11.5

## Key Performance Metrics

| Version | Field Creation | Model Creation | JSON Serialize | JSON Deserialize |
|---------|---------------|----------------|----------------|------------------|
| 0.2.3 | 683.745 ms | 303.496 ms | 228.562 ms | 226.925 ms | |
| 0.3.0 | 1596.997 ms | 315.638 ms | 244.448 ms | 234.067 ms | |
| 0.3.1 | 882.720 ms | 321.729 ms | 229.568 ms | 236.566 ms | |
| 0.3.2 | 701.138 ms | 304.438 ms | 267.310 ms | 234.063 ms | |
| 0.3.3 | 914.846 ms | 260.545 ms | 249.547 ms | 226.012 ms | |