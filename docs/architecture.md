# Architecture Documentation

## Overview

Memory is designed as a modular, production-grade knowledge base system. The architecture follows clean architecture principles with clear separation of concerns and stable interfaces between layers.

## Design Principles

1. **Modular Architecture**: Each component has a single responsibility
2. **Explicit Over Implicit**: No magic, all behavior is explicit
3. **Separation of Concerns**: Domain logic separate from infrastructure
4. **Config-Driven Design**: All behavior controlled via configuration
5. **Incremental Extensibility**: Add features without refactoring core logic
6. **Production Readiness**: Logging, error handling, type safety

## System Layers

### 1. Core Layer (`core/`)

**Purpose**: Domain models and business logic

**Components**:
- `models.py`: Core domain entities (Document, Chunk, Embedding, SearchResult)
- `chunking.py`: Text chunking logic

**Why it exists**: Provides stable domain model that other layers depend on

**How to extend**: Add new domain entities or business logic here

### 2. Providers Layer (`providers/`)

**Purpose**: Abstract interfaces for external services

**Components**:
- `base.py`: Abstract base classes for EmbeddingProvider and LLMProvider

**Why it exists**: Allows swapping between different embedding models and LLMs without changing core logic

**How to extend**:
1. Create new provider class inheriting from base
2. Implement all abstract methods
3. Register in config system
4. Add optional dependencies to pyproject.toml

**Example**:
```python
from memory.providers.base import EmbeddingProvider

class MyEmbeddingProvider(EmbeddingProvider):
    async def embed_text(self, text: str) -> list[float]:
        # Implementation
        pass
```

### 3. Storage Layer (`storage/`)

**Purpose**: Abstract interfaces for data persistence

**Components**:
- `base.py`: Abstract base classes for VectorStore and MetadataStore

**Why it exists**: Separates vector storage from metadata storage, allows swapping databases

**How to extend**:
1. Create new store class inheriting from base
2. Implement all abstract methods
3. Register in config system
4. Add optional dependencies to pyproject.toml

### 4. Pipelines Layer (`pipelines/`)

**Purpose**: Orchestrate multi-step operations

**Components**:
- `ingestion.py`: Document ingestion pipeline
- `query.py`: Search and QA pipeline

**Why it exists**: Coordinates between providers and storage, handles complex workflows

**How to extend**: Add new pipeline stages or create new pipelines for different workflows

### 5. Interfaces Layer (`interfaces/`)

**Purpose**: User-facing interfaces

**Components**:
- `cli.py`: Command-line interface

**Why it exists**: Separates user interaction from business logic

**How to extend**: Add new commands or create new interfaces (API, Web UI)

### 6. Config Layer (`config/`)

**Purpose**: Configuration management

**Components**:
- `schema.py`: Pydantic configuration models
- `loader.py`: Configuration loading logic

**Why it exists**: Type-safe configuration with validation

**How to extend**: Add new configuration fields or profiles

### 7. Observability Layer (`observability/`)

**Purpose**: Logging, metrics, and monitoring

**Components**:
- `logging.py`: Structured logging setup

**Why it exists**: Provides consistent logging across the system

**How to extend**: Add metrics collection or tracing

## Data Flow

### Ingestion Flow

```
File → IngestionPipeline → Document → Chunking → Chunks
                                                    ↓
                                            EmbeddingProvider
                                                    ↓
                                              Embeddings
                                                    ↓
                                    ┌───────────────┴───────────────┐
                                    ↓                               ↓
                              VectorStore                    MetadataStore
```

### Query Flow

```
Query → QueryPipeline → EmbeddingProvider → Query Vector
                                                ↓
                                          VectorStore.search()
                                                ↓
                                          SearchResults
                                                ↓
                                          LLMProvider
                                                ↓
                                            Answer
```

## Extension Points

### Adding a New Document Type

1. Add enum value to `DocumentType` in `core/models.py`
2. Update `_detect_document_type()` in `pipelines/ingestion.py`
3. Add document parser if needed

### Adding a New Chunking Strategy

1. Create new chunking function in `core/chunking.py`
2. Add configuration options to `ChunkingConfig`
3. Update `create_chunks()` to use new strategy

### Tree-sitter Markdown Chunking

Memory supports advanced Markdown chunking using tree-sitter for accurate syntax tree parsing.

**Features:**
- Semantic-aware chunking based on syntax tree structure
- Proper handling of tables, nested lists, blockquotes, and code blocks
- Heading context preservation across chunks
- Fallback to regex-based chunking when tree-sitter is unavailable

**Dependencies:**
```bash
uv sync --extra tree-sitter
```

**Configuration:**
```toml
[chunking]
# Target size of each chunk in characters (default: 1000)
chunk_size = 1000
# Overlap between chunks to preserve context (default: 200)
chunk_overlap = 200
# Minimum chunk size, smaller chunks are filtered (default: 100)
min_chunk_size = 100
```

**How it works:**
1. Parse Markdown into tree-sitter syntax tree
2. Extract semantic nodes (headings, paragraphs, tables, lists, code blocks)
3. Merge nodes into target-sized chunks while preserving semantic boundaries
4. Add heading context to maintain document structure

**Fallback order:**
1. Tree-sitter chunking (preferred)
2. Regex-based Markdown chunking (fallback)
3. Fixed-size chunking (last resort)

### Adding Observability

1. Add metrics collection in `observability/`
2. Inject metrics collectors into pipelines
3. Export metrics to monitoring system

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock dependencies
- Focus on business logic

### Integration Tests
- Test component interactions
- Use in-memory implementations
- Test full pipelines

### End-to-End Tests
- Test CLI commands
- Use real providers (with test data)
- Verify complete workflows

## Deployment Profiles

The system supports multiple deployment profiles:

- **local**: Development with local models
- **server**: Self-hosted with persistent storage
- **cloud**: Cloud-hosted with managed services

Configure via `[profiles.<name>]` in config.toml

## Future Enhancements

- Web UI interface
- REST API
- Incremental re-indexing
- Multi-modal embeddings (images, code)
- Advanced ranking algorithms
- Distributed vector search
- Real-time indexing
