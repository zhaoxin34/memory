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

### 1. Entities Layer (`entities/`)

**Purpose**: Pure domain models - foundational data structures used by all layers

**Components**:
- `document.py`: Document, DocumentType
- `chunk.py`: Chunk
- `repository.py`: Repository
- `embedding.py`: Embedding
- `search_result.py`: SearchResult

**Why it exists**: Provides pure domain entities without business logic, avoiding naming conflicts with LLM "model" terminology

**How to extend**: Add new entity files as needed

### 2. Service Layer (`service/`)

**Purpose**: Business logic orchestration

**Components**:
- `repository.py`: RepositoryManager - repository lifecycle management
- `stores.py`: initialize_stores() - store initialization helper

**Why it exists**: Coordinates business workflows, separates business logic from infrastructure

**Current status**: ✅ Implemented (2026-03-01)

### 3. Core Layer (`core/`)

**Purpose**: Technical utilities and chunking implementations

**Components**:
- `logging.py`: Structured logging setup
- `chunking.py`: Text chunking logic
- `markdown_chunking.py`: Markdown-aware chunking
- `tree_sitter_chunking.py`: Tree-sitter based chunking

**Why it exists**: Provides technical implementations used by pipelines

### 4. Providers Layer (`providers/`)

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

### 5. Storage Layer (`storage/`)

**Purpose**: Abstract interfaces for data persistence

**Components**:
- `base.py`: Abstract base classes for VectorStore and MetadataStore

**Why it exists**: Separates vector storage from metadata storage, allows swapping databases

**How to extend**:
1. Create new store class inheriting from base
2. Implement all abstract methods
3. Register in config system
4. Add optional dependencies to pyproject.toml

### 6. Pipelines Layer (`pipelines/`)

**Purpose**: Orchestrate multi-step operations

**Components**:
- `ingestion.py`: Document ingestion pipeline
- `query.py`: Search and QA pipeline

**Why it exists**: Coordinates between providers and storage, handles complex workflows

**How to extend**: Add new pipeline stages or create new pipelines for different workflows

### 7. Interfaces Layer (`interfaces/`)

**Purpose**: User-facing interfaces

**Components**:
- `cli.py`: Command-line interface

**Why it exists**: Separates user interaction from business logic

**How to extend**: Add new commands or create new interfaces (API, Web UI)

### 8. Config Layer (`config/`)

**Purpose**: Configuration management

**Components**:
- `schema.py`: Pydantic configuration models
- `loader.py`: Configuration loading logic

**Why it exists**: Type-safe configuration with validation

**How to extend**: Add new configuration fields or profiles

## Layer Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│  interfaces/ (cli.py)                                       │
│  - Parameter parsing                                        │
│  - User interaction                                         │
│  - Output formatting                                        │
│  Uses entities for input/output                            │
└──────────────────────┬──────────────────────────────────────┘
                       │ calls
┌──────────────────────▼──────────────────────────────────────┐
│  service/                                                   │
│  - Business logic orchestration                            │
│  - Repository management                                   │
│  - Coordinates pipelines                                    │
│  Uses entities for business operations                     │
└──────────────────────┬──────────────────────────────────────┘
                       │ calls
┌──────────────────────▼──────────────────────────────────────┐
│  pipelines/                                                 │
│  - IngestionPipeline                                       │
│  - QueryPipeline                                           │
│  - Technical implementation details                        │
│  Uses entities as data containers                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ receives injected
┌──────────────────────▼──────────────────────────────────────┐
│  storage/                                                   │
│  - VectorStore                                             │
│  - MetadataStore                                           │
│  Uses entities for persistence                             │
└─────────────────────────────────────────────────────────────┘

                         ↑
           ┌─────────────┴─────────────┐
           │    entities/              │  ← Foundation (used by ALL layers)
           │  - Document               │
           │  - Chunk                  │
           │  - Repository             │
           │  - Embedding              │
           │  - SearchResult           │
           │  (Pure domain models)    │
           └───────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  core/ (technical utilities)                                 │
│  - logging.py                                              │
│  - chunking.py, markdown_chunking.py, tree_sitter_...    │
└─────────────────────────────────────────────────────────────┘
```

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

## Repository Isolation Mechanism

- Each Document and Chunk has `repository_id` field
- VectorStore creates separate collection per repository: `{collection_name}_{repository_name}`
- Search can filter by `repository_id`
- Deleting repository cascades to delete all documents, chunks, and embeddings

## Extension Points

### Adding a New Document Type

1. Add enum value to `DocumentType` in `entities/document.py`
2. Update detection logic in `pipelines/ingestion.py`
3. Add document parser if needed

### Adding a New Chunking Strategy

1. Create new chunking function in `core/`
2. Add configuration options to `config/schema.py`
3. Update pipeline to use new strategy

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
chunk_size = 1000
chunk_overlap = 200
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

### Adding a New Provider

1. Create new provider class in `providers/` inheriting from base
2. Implement all abstract methods
3. Register in config system
4. Add optional dependencies to pyproject.toml

### Adding a New Storage Backend

1. Create new store class in `storage/` inheriting from base
2. Implement all abstract methods
3. Register in config system

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

## Migration Notes (2026-03-01)

### Recent Changes

1. **Created `entities/` layer**: Domain models moved from `core/models.py` to separate files
2. **Created `service/` layer**: Business logic (RepositoryManager) moved from `core/`
3. **Moved logging to core**: `logging.py` moved from `observability/` to `core/`
4. **Removed observability/**: Directory deleted, logging now in `core/`

### Backward Compatibility

- Old imports still work via re-exports:
  - `memory.core.models` → re-exports from `memory.entities`
  - `memory.core.repository` → re-exports from `memory.service`

### Project Structure (2026-03-01)

```
src/memory/
├── config/         # Configuration management
├── core/          # Technical utilities (logging, chunking)
├── entities/      # Domain models (Document, Chunk, Repository, etc.)
├── interfaces/   # CLI interface
├── pipelines/    # Business pipelines (ingestion, query)
├── providers/    # External services (embedding, LLM)
├── service/      # Business logic (RepositoryManager)
└── storage/      # Data persistence (VectorStore, MetadataStore)
```

## Future Enhancements

- Web UI interface
- REST API
- Incremental re-indexing
- Multi-modal embeddings (images, code)
- Advanced ranking algorithms
- Distributed vector search
- Real-time indexing
