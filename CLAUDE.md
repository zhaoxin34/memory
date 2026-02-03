# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Memory 是一个生产级的个人知识库系统，支持语义搜索和基于 LLM 的问答功能。项目使用 Python 3.11+ 和 uv 作为包管理器。

详细功能特性和快速开始指南请参见 [README.md](README.md)。

## Key Commands

### Development Setup
```bash
# 安装依赖
uv sync

# 安装可选依赖（根据需要选择）
uv sync --extra openai --extra chroma --extra local
```

### Testing
```bash
# 运行所有测试
uv run pytest

# 运行单个测试文件
uv run pytest tests/unit/test_models.py

# 运行特定测试
uv run pytest tests/unit/test_models.py::test_document_creation

# 带覆盖率报告
uv run pytest --cov=src --cov-report=term-missing
```

### Code Quality
```bash
# 类型检查
uv run mypy src/

# 代码检查
uv run ruff check src/

# 代码格式化
uv run black src/
```

### Running the CLI

CLI 使用方法请参见 [README.md#基本使用](README.md#基本使用)。

## Architecture Overview

架构图和项目结构请参见 [README.md#架构](README.md#架构)。

### 关键设计原则

1. **Provider Pattern**: 所有外部服务（嵌入、LLM、向量数据库）都通过抽象接口访问
2. **存储分离**: VectorStore（向量存储）和 MetadataStore（元数据存储）分离
3. **配置驱动**: 所有行为通过 TOML 配置文件控制，支持多环境配置（local, server, cloud）
4. **类型安全**: 全面使用类型提示，Pydantic 模型验证所有数据结构

### 数据流

**导入流程**:
```
File → IngestionPipeline → Document → Chunking → Chunks
                                                    ↓
                                            EmbeddingProvider
                                                    ↓
                                    VectorStore + MetadataStore
```

**查询流程**:
```
Query → QueryPipeline → EmbeddingProvider → Query Vector
                                                ↓
                                          VectorStore.search()
                                                ↓
                                          LLMProvider → Answer
```

详细架构文档请参见 [docs/architecture.md](docs/architecture.md)。

## Key Components

### Core Layer (`src/memory/core/`)
- `models.py`: 核心领域模型（Document, Chunk, Embedding, SearchResult）
  - Document: 源文档，包含完整内容和元数据
  - Chunk: 文档分块，用于嵌入和检索
  - Embedding: 向量表示，包含向量和模型信息
  - SearchResult: 检索结果，包含分块、分数和文档引用
- `chunking.py`: 文本分块逻辑，支持可配置的块大小和重叠

### Providers Layer (`src/memory/providers/`)
- `base.py`: EmbeddingProvider 和 LLMProvider 抽象基类
- 实现新 provider 时必须继承这些基类并实现所有抽象方法：
  - EmbeddingProvider: `embed_text()`, `embed_batch()`, `get_dimension()`, `get_max_tokens()`
  - LLMProvider: `generate()`, `count_tokens()`

### Storage Layer (`src/memory/storage/`)
- `base.py`: VectorStore 和 MetadataStore 抽象基类
- VectorStore 负责：向量存储、相似度搜索、批量操作、索引管理
- MetadataStore 负责：文档和分块的 CRUD 操作、分页查询

### Pipelines Layer (`src/memory/pipelines/`)
- `ingestion.py`: 文档导入管道
  - 协调文档存储、分块、嵌入生成和向量存储
  - 支持批量处理以提高效率
- `query.py`: 查询管道
  - 语义搜索：生成查询向量 → 向量搜索 → 返回结果
  - LLM 问答：检索相关分块 → 构建上下文 → LLM 生成答案

### Config Layer (`src/memory/config/`)
- `schema.py`: Pydantic 配置模型，支持环境变量覆盖（MEMORY_* 前缀）
- `loader.py`: 配置加载逻辑，支持 TOML 文件和多环境配置

### Observability Layer (`src/memory/observability/`)
- `logging.py`: 结构化日志配置（使用 structlog）

## Extension Points

扩展系统的基本步骤请参见 [README.md#扩展系统](README.md#扩展系统)。

### 添加新的文档类型
1. 在 `core/models.py` 的 `DocumentType` 枚举中添加新类型
2. 在 `pipelines/ingestion.py` 的 `_detect_document_type()` 中添加检测逻辑
3. 如需特殊解析，在 `core/` 中添加文档加载器

### 添加新的分块策略
1. 在 `core/chunking.py` 创建新的分块函数
2. 在 `config/schema.py` 的 `ChunkingConfig` 中添加配置选项
3. 在 `core/chunking.py` 的 `create_chunks()` 中集成新策略

## Configuration

配置示例和说明请参见 [README.md#配置](README.md#配置)。

### 配置加载优先级
1. 环境变量（MEMORY_* 前缀）
2. 配置文件（TOML）
3. 默认值

### 配置文件搜索路径（按优先级）
1. `./config.toml`
2. `~/.memory/config.toml`
3. `/etc/memory/config.toml`

### 环境变量支持
- 配置文件中可使用 `${VAR_NAME}` 引用环境变量
- 所有配置项都可通过 `MEMORY_` 前缀的环境变量覆盖
- 嵌套配置使用双下划线：`MEMORY_EMBEDDING__PROVIDER=openai`

## Important Notes

### 异步编程
- 所有 I/O 操作（provider 调用、storage 操作）使用 async/await
- Pipeline 方法都是异步的，需要使用 `asyncio.run()` 或 `await` 调用

### 批处理
- 嵌入生成支持批处理（通过 `embedding.batch_size` 配置）
- VectorStore 提供批量添加方法 `add_embeddings_batch()`

### 错误处理
- Provider 实现必须捕获底层错误并抛出 `ProviderError`
- Storage 实现必须捕获底层错误并抛出 `StorageError`
- Pipeline 会捕获并记录错误，但不会静默失败

### 日志记录
- 使用结构化日志（structlog），便于分析和过滤
- 日志级别通过配置控制
- 关键操作（导入、查询）都有开始和完成日志

### 类型安全
- 所有数据模型使用 Pydantic 验证
- 启用 mypy strict 模式
- 所有函数都有类型提示

## Testing Strategy

- **Unit Tests**: 测试单个组件，mock 依赖
- **Integration Tests**: 测试组件交互，使用内存实现
- **End-to-End Tests**: 测试完整流程，使用真实 provider（测试数据）

测试文件位置：
- `tests/unit/`: 单元测试
- `tests/integration/`: 集成测试
