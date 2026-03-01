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

### Git Hooks

项目使用自定义 git hooks 目录 (`hooks/`)：
- `pre-commit`: 在提交前运行 pytest 和 ruff check，任何失败都会阻止提交
- 通过 `git config core.hooksPath hooks` 启用

## Architecture Overview

架构图和项目结构请参见 [README.md#架构](README.md#架构)。

### 关键设计原则

1. **Provider Pattern**: 所有外部服务（嵌入、LLM、向量数据库）都通过抽象接口访问
2. **存储分离**: VectorStore（向量存储）和 MetadataStore（元数据存储）分离
3. **仓库隔离**: Repository 作为文档的逻辑隔离单元，每个仓库使用独立的向量集合
4. **配置驱动**: 所有行为通过 TOML 配置文件控制，支持多环境配置（local, server, cloud）
5. **类型安全**: 全面使用类型提示，Pydantic 模型验证所有数据结构

### 数据流

**导入流程**:
```
File → IngestionPipeline(repository_id) → Document(repository_id) → Chunking → Chunks(repository_id)
                                                                                      ↓
                                                                              EmbeddingProvider
                                                                                      ↓
                                                              VectorStore(collection_{repo_name}) + MetadataStore
```

**查询流程**:
```
Query → QueryPipeline(repository_id) → EmbeddingProvider → Query Vector
                                                                ↓
                                                    VectorStore.search(repository_id)
                                                                ↓
                                                          LLMProvider → Answer
```

**仓库隔离机制**:
- 每个 Document 和 Chunk 都有 `repository_id` 字段
- VectorStore 为每个仓库创建独立的集合：`{collection_name}_{repository_name}`
- 搜索时可以指定 `repository_id` 进行范围过滤
- 删除仓库时会级联删除所有相关的文档、分块和嵌入

详细架构文档请参见 [docs/architecture.md](docs/architecture.md)。

## Key Components

### Entities Layer (`src/memory/entities/`)
- 纯领域模型，所有层共用
- `document.py`: Document, DocumentType
- `chunk.py`: Chunk
- `repository.py`: Repository
- `embedding.py`: Embedding
- `search_result.py`: SearchResult

### Service Layer (`src/memory/service/`)
- 业务逻辑编排层
- `repository.py`: RepositoryManager - 仓库生命周期管理
  - `create_repository()`: 创建仓库（包含名称验证和重复检查）
  - `get_repository()`, `get_repository_by_name()`: 检索仓库
  - `list_repositories()`: 列出所有仓库
  - `delete_repository()`: 删除仓库（级联删除文档、分块、嵌入）
  - `ensure_default_repository()`: 确保默认仓库存在
- `stores.py`: initialize_stores() - 存储初始化辅助函数

### Core Layer (`src/memory/core/`)
- `models.py`: 核心领域模型（Repository, Document, Chunk, Embedding, SearchResult）
  - Repository: 仓库模型，用于组织和隔离文档集合（kebab-case 命名）
  - Document: 源文档，包含完整内容和元数据，必须属于一个仓库
  - Chunk: 文档分块，用于嵌入和检索，继承父文档的 repository_id
  - Embedding: 向量表示，包含向量和模型信息
  - SearchResult: 检索结果，包含分块、分数和文档引用
- `chunking.py`: 文本分块逻辑，支持可配置的块大小和重叠
- `repository.py`: RepositoryManager 类，封装仓库 CRUD 操作
  - `create_repository()`: 创建仓库（包含名称验证和重复检查）
  - `get_repository()`, `get_repository_by_name()`: 检索仓库
  - `list_repositories()`: 列出所有仓库
  - `delete_repository()`: 删除仓库（级联删除文档、分块、嵌入）
  - `ensure_default_repository()`: 确保默认仓库存在

### Providers Layer (`src/memory/providers/`)
- `base.py`: EmbeddingProvider 和 LLMProvider 抽象基类
- `local.py`: LocalEmbeddingProvider - 本地嵌入模型实现
  - 使用 sentence-transformers 库
  - 支持多种预训练模型（all-MiniLM-L6-v2, all-mpnet-base-v2 等）
  - 异步支持通过 `asyncio.to_thread()`
  - 自动模型下载和缓存
  - 支持 HuggingFace 镜像（通过 HF_ENDPOINT 环境变量）
- `openai.py`: OpenAIEmbeddingProvider - OpenAI 嵌入实现
  - 使用官方 OpenAI SDK
  - 支持 text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002
  - 批处理支持（MAX_BATCH_SIZE = 2048）
  - Token 使用量日志记录
  - 完整的错误处理（认证、速率限制、网络错误）
- `__init__.py`: 工厂函数 `create_embedding_provider()`
  - 根据配置动态创建 provider 实例
  - 自动检查依赖是否安装
  - 友好的错误提示
- 实现新 provider 时必须继承这些基类并实现所有抽象方法：
  - EmbeddingProvider: `embed_text()`, `embed_batch()`, `get_dimension()`, `get_max_tokens()`
  - LLMProvider: `generate()`, `count_tokens()`

### Storage Layer (`src/memory/storage/`)
- `base.py`: VectorStore 和 MetadataStore 抽象基类
- `chroma.py`: ChromaVectorStore - ChromaDB 向量存储实现
  - 持久化存储到磁盘（通过 persist_directory 配置）
  - 仓库隔离：每个仓库使用独立集合 `{collection_name}_{repository_name}`
  - 集合名称清理（确保符合 Chroma 命名规范）
  - 完整的 CRUD 操作：add_embedding, add_embeddings_batch, search, delete_by_document_id, delete_by_chunk_id, delete_by_repository, count
  - 相似度搜索支持仓库过滤和元数据过滤
  - 上下文管理器支持（自动资源清理）
- `memory.py`: 内存实现（用于测试和开发）
  - InMemoryVectorStore: 使用 `{collection_name}_{repository_name}` 格式隔离集合
  - InMemoryMetadataStore: 使用字典存储所有数据
- `sqlite.py`: SQLite 实现（用于生产环境）
  - 包含 repositories, documents, chunks 表
  - 使用外键和 CASCADE DELETE 保证数据一致性
- `__init__.py`: 工厂函数 `create_vector_store()` 和 `create_metadata_store()`
  - 根据配置动态创建 store 实例
  - 自动检查依赖是否安装
  - 友好的错误提示
- VectorStore 负责：向量存储、相似度搜索、批量操作、索引管理、按仓库隔离
  - `search()` 方法支持可选的 `repository_id` 参数进行范围过滤
  - `delete_by_repository()` 方法删除指定仓库的所有嵌入
- MetadataStore 负责：文档、分块和仓库的 CRUD 操作、分页查询
  - Repository CRUD: `add_repository()`, `get_repository()`, `get_repository_by_name()`, `list_repositories()`, `delete_repository()`
  - `list_documents()` 支持可选的 `repository_id` 参数进行过滤

### 数据库迁移策略
- **向后兼容性**: 添加新字段时使用`ALTER TABLE ADD COLUMN`，并检查字段是否已存在
- **NULL值处理**: 新字段默认为NULL，在业务逻辑中优雅处理NULL值
- **迁移时机**: 在应用启动时执行迁移，确保数据库结构与应用代码同步

### Pipelines Layer (`src/memory/pipelines/`)
- `ingestion.py`: 文档导入管道
  - 协调文档存储、分块、嵌入生成和向量存储
  - 支持批量处理以提高效率
  - `__init__()` 接受可选的 `repository_id` 参数
  - `ingest_file()` 接受可选的 `repository_id` 参数（覆盖管道默认值）
  - 创建的 Document 和 Chunk 都会包含 repository_id
  - **MD5智能覆盖**: 基于内容MD5值的智能检测，实现内容变化时自动覆盖，内容未变化时跳过处理
  - **回滚机制**: 失败时自动回滚到原始文档状态，确保数据一致性
- `query.py`: 查询管道
  - 语义搜索：生成查询向量 → 向量搜索 → 返回结果
  - LLM 问答：检索相关分块 → 构建上下文 → LLM 生成答案
  - `__init__()` 接受可选的 `repository_id` 参数
  - `search()` 和 `answer()` 方法支持可选的 `repository_id` 参数（覆盖管道默认值）

### Config Layer (`src/memory/config/`)
- `schema.py`: Pydantic 配置模型，支持环境变量覆盖（MEMORY_* 前缀）
  - AppConfig 包含 `default_repository` 字段（默认值 "default"）
  - 可通过 `MEMORY_DEFAULT_REPOSITORY` 环境变量覆盖
- `loader.py`: 配置加载逻辑，支持 TOML 文件和多环境配置

## Extension Points

扩展系统的基本步骤请参见 [README.md#扩展系统](README.md#扩展系统)。

### 添加新的文档类型
1. 在 `entities/document.py` 的 `DocumentType` 枚举中添加新类型
2. 在 `pipelines/ingestion.py` 中添加检测逻辑
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

### 用户体验设计
- **友好提示信息**: 为不同操作场景提供清晰的状态反馈（"Ingested"、"Updated"、"Skipped"、"Re-imported"）
- **时区感知显示**: 所有时间戳按用户本地时区显示，提升可读性
- **进度反馈**: 长时间操作提供进度指示和状态更新
- **错误处理**: 优雅处理异常情况，提供有意义的错误信息和恢复建议

### 类型安全
- 所有数据模型使用 Pydantic 验证
- 启用 mypy strict 模式
- 所有函数都有类型提示

### 时间处理最佳实践
- **SQLite TEXT类型时间排序**: 使用ISO 8601格式（如"2026-02-05T22:48:25"）在SQLite中完美支持时间排序，字典序=时间序
- **时区转换**: 在CLI显示层进行UTC到本地时区的转换，避免在数据库层面处理时区复杂性
- **存储格式**: 数据库存储UTC时间的ISO 8601字符串，显示时转换为本地时区

## Testing Strategy

- **Unit Tests**: 测试单个组件，mock 依赖
- **Integration Tests**: 测试组件交互，使用内存实现
- **End-to-End Tests**: 测试完整流程，使用真实 provider（测试数据）

测试文件位置：
- `tests/unit/`: 单元测试
- `tests/integration/`: 集成测试
