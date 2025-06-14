# AsyncPulsarMemvidAdapter Tutorial

This directory contains a comprehensive tutorial for the
AsyncPulsarMemvidAdapter, demonstrating enterprise-scale video memory
operations with Apache Pulsar streaming.

## Files

- **`async_pulsar_memvid_tutorial.ipynb`** - Main tutorial notebook
- **`docker-compose.yml`** - Apache Pulsar standalone setup
- **`test_notebook.py`** - Test script to verify tutorial functionality
- **`test_async_pulsar.py`** - Alternative test script for adapter functionality

## Quick Start

1. **Start Pulsar:**

   ```bash
   docker-compose up -d
   ```

2. **Wait for startup (30-60 seconds):**

   ```bash
   docker logs pulsar-standalone
   ```

3. **Verify setup:**

   ```bash
   python test_notebook.py
   ```

4. **Run the tutorial:**
   Open `async_pulsar_memvid_tutorial.ipynb` in Jupyter and execute the cells.

## Tutorial Contents

### 1. Enterprise Setup

- Apache Pulsar integration
- Health checks and connectivity testing
- Dependency validation

### 2. Data Models

- Research paper models with rich metadata
- Search result structures
- Message formats for Pulsar communication

### 3. Async Video Memory Creation

- Synchronous encoding for immediate results
- Asynchronous encoding via Pulsar topics
- File management and temporary storage

### 4. Distributed Search Operations

- Semantic search across video memories
- Multiple query testing
- Single vs. multiple result handling

### 5. Production Patterns

- Background worker architecture
- Message-driven processing
- Horizontal scaling strategies

### 6. Monitoring & Error Handling

- Health monitoring
- Robust error handling patterns
- Production deployment considerations

## Architecture

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   API       │    │   Pulsar    │    │  Workers    │
│  Service    │───▶│   Topics    │───▶│   Pool      │
└─────────────┘    └─────────────┘    └─────────────┘
                                           │
                                           ▼
                                    ┌─────────────┐
                                    │   Video     │
                                    │  Memories   │
                                    └─────────────┘
```

## Features Demonstrated

- ✅ **Scalable Architecture**: Horizontal scaling via Pulsar topics
- ✅ **Async Operations**: Non-blocking video memory creation
- ✅ **Enterprise Streaming**: Apache Pulsar for reliable message delivery
- ✅ **Health Monitoring**: Built-in connectivity and health checks
- ✅ **Error Handling**: Robust error handling with proper exception types
- ✅ **Production Ready**: Background workers and monitoring patterns

## Requirements

- Docker and Docker Compose
- Python 3.10+
- pydapter with memvid-pulsar extras
- Jupyter (for notebook execution)

## Notes

- The tutorial gracefully handles missing dependencies
- Mock mode available when Pulsar is not running
- All temporary files are cleaned up automatically
- ARM64/Apple Silicon compatible (Pulsar 3.2.0+)

## Troubleshooting

If Pulsar fails to start:

1. Check Docker is running
2. Ensure ports 6650 and 8080 are available
3. Wait for health check to pass (up to 2 minutes)
4. Check logs: `docker logs pulsar-standalone`

For import errors:

1. Install memvid dependencies if needed
2. Tutorial works in demo mode without full dependencies
3. All basic pydapter functionality is demonstrated

## Cleanup

Stop Pulsar when done:

```bash
docker-compose down
```
