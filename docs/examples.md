# Memory 使用示例

本文档提供 Memory 知识库系统的详细使用示例。

## 目录

- [基础使用](#基础使用)
- [仓库管理](#仓库管理)
- [文档导入](#文档导入)
- [语义搜索](#语义搜索)
- [LLM 问答](#llm-问答)
- [配置示例](#配置示例)
- [Python API 使用](#python-api-使用)

## 基础使用

### 查看系统信息

```bash
memory info
```

输出示例：
```
Memory Knowledge Base System
Version: 0.1.0
Config: /Users/username/.memory/config.toml
Data Directory: /Users/username/.memory
Default Repository: default
```

## 仓库管理

### 创建仓库

```bash
# 创建基本仓库
memory repo create my-docs

# 创建带描述的仓库
memory repo create project-a --description "项目 A 的技术文档"

# 创建多个仓库
memory repo create personal --description "个人笔记"
memory repo create work --description "工作文档"
memory repo create research --description "研究资料"
```

### 列出所有仓库

```bash
memory repo list
```

输出示例：
```
Repositories:
  - default (Default repository)
    Documents: 0, Chunks: 0
  - project-a (项目 A 的技术文档)
    Documents: 15, Chunks: 234
  - personal (个人笔记)
    Documents: 42, Chunks: 567
```

### 查看仓库详情

```bash
memory repo info project-a
```

输出示例：
```
Repository: project-a
Description: 项目 A 的技术文档
Created: 2024-01-15 10:30:00
Documents: 15
Chunks: 234
Storage: ~/.memory/chroma/memory_project-a
```

### 删除仓库

```bash
# 删除仓库（会提示确认）
memory repo delete old-project

# 强制删除（不提示）
memory repo delete old-project --force
```

## 文档导入

### 导入单个文件

```bash
# 导入到默认仓库
memory ingest README.md

# 导入到指定仓库
memory ingest docs/api.md --repository project-a
```

### 导入目录

```bash
# 递归导入目录下所有文件
memory ingest ./docs --repository project-a --recursive

# 导入特定类型的文件
memory ingest ./notes --repository personal --recursive --pattern "*.md"
```

### 批量导入

```bash
# 导入多个文件
memory ingest file1.md file2.md file3.md --repository work

# 使用通配符
memory ingest docs/**/*.md --repository project-a
```

### 导入时的配置

```bash
# 使用自定义配置文件
memory ingest docs/ --config ./config.prod.toml

# 使用环境变量覆盖配置
export MEMORY_EMBEDDING__BATCH_SIZE=64
memory ingest large-docs/
```

## 语义搜索

### 基础搜索

```bash
# 在默认仓库中搜索
memory search "如何配置系统"

# 在指定仓库中搜索
memory search "API 使用方法" --repository project-a

# 返回更多结果
memory search "Python 示例" --repository project-a --top-k 10
```

### 搜索输出示例

```bash
memory search "配置文件" --repository project-a --top-k 3
```

输出：
```
Search Results (top 3):

[1] Score: 0.89
Source: docs/configuration.md
Content: 配置文件使用 TOML 格式，支持多种部署场景。主要配置项包括：
- embedding: 嵌入模型配置
- vector_store: 向量存储配置
- metadata_store: 元数据存储配置
...

[2] Score: 0.76
Source: docs/quickstart.md
Content: 创建 config.toml 文件并配置以下选项：
app_name = "memory"
log_level = "INFO"
...

[3] Score: 0.68
Source: docs/deployment.md
Content: 生产环境配置建议使用 ChromaDB 作为向量存储，
SQLite 作为元数据存储...
```

### 跨仓库搜索

```bash
# 搜索所有仓库（需要自定义脚本）
for repo in $(memory repo list --format json | jq -r '.[].name'); do
  echo "=== Repository: $repo ==="
  memory search "关键词" --repository $repo --top-k 3
done
```

## LLM 问答

### 基础问答

```bash
# 在默认仓库中提问
memory ask "系统的主要功能是什么？"

# 在指定仓库中提问
memory ask "如何部署到生产环境？" --repository project-a
```

### 问答输出示例

```bash
memory ask "如何配置 OpenAI 嵌入？" --repository project-a
```

输出：
```
Answer:
要配置 OpenAI 嵌入，需要在 config.toml 中设置以下选项：

[embedding]
provider = "openai"
model_name = "text-embedding-3-small"
api_key = "${OPENAI_API_KEY}"
batch_size = 100

推荐使用 text-embedding-3-small 模型，它提供了良好的性价比。
确保设置 OPENAI_API_KEY 环境变量或在配置文件中直接提供 API 密钥。

Sources:
  [1] docs/configuration.md (score: 0.92)
  [2] docs/providers.md (score: 0.85)
  [3] README.md (score: 0.78)
```

### 高级问答

```bash
# 使用更多上下文
memory ask "详细解释嵌入模型的选择" --repository project-a --top-k 10

# 使用特定的 LLM 模型（通过配置）
export MEMORY_LLM__MODEL_NAME="gpt-4-turbo"
memory ask "总结所有文档的核心内容" --repository project-a
```

## 配置示例

### 本地开发配置

创建 `config.local.toml`：

```toml
app_name = "memory"
log_level = "DEBUG"
data_dir = "./data"
default_repository = "dev"

[embedding]
provider = "local"
model_name = "all-MiniLM-L6-v2"
batch_size = 16

[vector_store]
store_type = "chroma"
collection_name = "memory_dev"

[vector_store.extra_params]
persist_directory = "./data/chroma"

[metadata_store]
store_type = "sqlite"

[metadata_store.extra_params]
connection_string = "sqlite:///./data/memory.db"

[chunking]
chunk_size = 256
chunk_overlap = 50
min_chunk_size = 50
```

使用：
```bash
memory ingest docs/ --config config.local.toml
```

### 生产环境配置

创建 `config.prod.toml`：

```toml
app_name = "memory"
log_level = "INFO"
data_dir = "/var/lib/memory"
default_repository = "production"

[embedding]
provider = "openai"
model_name = "text-embedding-3-small"
api_key = "${OPENAI_API_KEY}"
batch_size = 100

[llm]
provider = "openai"
model_name = "gpt-4"
api_key = "${OPENAI_API_KEY}"

[vector_store]
store_type = "chroma"
collection_name = "memory_prod"

[vector_store.extra_params]
persist_directory = "/var/lib/memory/chroma"

[metadata_store]
store_type = "sqlite"

[metadata_store.extra_params]
connection_string = "sqlite:////var/lib/memory/memory.db"

[chunking]
chunk_size = 512
chunk_overlap = 50
min_chunk_size = 100
```

## Python API 使用

### 基础导入和搜索

```python
import asyncio
from pathlib import Path
from memory.config.loader import load_config
from memory.core.models import Document, DocumentType
from memory.core.repository import RepositoryManager
from memory.pipelines.ingestion import IngestionPipeline
from memory.pipelines.query import QueryPipeline
from memory.providers import create_embedding_provider
from memory.providers.base import ProviderConfig
from memory.storage import create_metadata_store, create_vector_store
from memory.storage.base import StorageConfig

async def main():
    # 加载配置
    config = load_config(Path("config.toml"))

    # 创建存储
    vector_storage_config = StorageConfig(
        storage_type=config.vector_store.store_type,
        collection_name=config.vector_store.collection_name,
        extra_params=config.vector_store.extra_params,
    )

    metadata_storage_config = StorageConfig(
        storage_type=config.metadata_store.store_type,
        collection_name=config.vector_store.collection_name,
        extra_params=config.metadata_store.extra_params,
    )

    metadata_store = create_metadata_store(metadata_storage_config)
    vector_store = create_vector_store(vector_storage_config)

    await metadata_store.initialize()
    await vector_store.initialize()

    # 创建仓库
    repo_manager = RepositoryManager(metadata_store, vector_store)
    repository = await repo_manager.ensure_default_repository(config.default_repository)

    # 创建嵌入提供者
    provider_config = ProviderConfig(
        provider_type=config.embedding.provider,
        model_name=config.embedding.model_name,
        api_key=config.embedding.api_key,
        extra_params=config.embedding.extra_params,
    )

    embedding_provider = create_embedding_provider(provider_config)

    # 导入文档
    pipeline = IngestionPipeline(
        config=config,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        metadata_store=metadata_store,
        repository_id=repository.id,
    )

    content = Path("README.md").read_text(encoding="utf-8")
    document = Document(
        content=content,
        source_path="README.md",
        document_type=DocumentType.TEXT,
        repository_id=repository.id,
    )

    num_chunks = await pipeline.ingest_document(document)
    print(f"Ingested {num_chunks} chunks")

    # 搜索
    query_pipeline = QueryPipeline(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        metadata_store=metadata_store,
        repository_id=repository.id,
    )

    results = await query_pipeline.search("配置系统", top_k=5)
    for i, result in enumerate(results, 1):
        print(f"[{i}] Score: {result.score:.2f}")
        print(f"Content: {result.chunk.content[:100]}...")

    # 清理
    await embedding_provider.close()
    await metadata_store.close()
    await vector_store.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### 批量导入文档

```python
import asyncio
from pathlib import Path
from memory.config.loader import load_config
from memory.pipelines.ingestion import IngestionPipeline
from memory.providers import create_embedding_provider
from memory.providers.base import ProviderConfig
from memory.storage import create_metadata_store, create_vector_store
from memory.storage.base import StorageConfig
from memory.core.repository import RepositoryManager

async def batch_ingest(docs_dir: Path, repository_name: str):
    config = load_config()

    # 初始化存储和提供者
    metadata_store = create_metadata_store(StorageConfig(
        storage_type=config.metadata_store.store_type,
        collection_name=config.vector_store.collection_name,
        extra_params=config.metadata_store.extra_params,
    ))

    vector_store = create_vector_store(StorageConfig(
        storage_type=config.vector_store.store_type,
        collection_name=config.vector_store.collection_name,
        extra_params=config.vector_store.extra_params,
    ))

    await metadata_store.initialize()
    await vector_store.initialize()

    repo_manager = RepositoryManager(metadata_store, vector_store)
    repository = await repo_manager.get_repository_by_name(repository_name)

    embedding_provider = create_embedding_provider(ProviderConfig(
        provider_type=config.embedding.provider,
        model_name=config.embedding.model_name,
        api_key=config.embedding.api_key,
        extra_params=config.embedding.extra_params,
    ))

    pipeline = IngestionPipeline(
        config=config,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        metadata_store=metadata_store,
        repository_id=repository.id,
    )

    # 批量导入
    total_chunks = 0
    for file_path in docs_dir.rglob("*.md"):
        print(f"Ingesting {file_path}...")
        num_chunks = await pipeline.ingest_file(file_path)
        total_chunks += num_chunks
        print(f"  → {num_chunks} chunks")

    print(f"\nTotal: {total_chunks} chunks ingested")

    # 清理
    await embedding_provider.close()
    await metadata_store.close()
    await vector_store.close()

if __name__ == "__main__":
    asyncio.run(batch_ingest(Path("./docs"), "project-a"))
```

### 自定义嵌入提供者

```python
from typing import List
from memory.providers.base import EmbeddingProvider, ProviderError

class CustomEmbeddingProvider(EmbeddingProvider):
    """自定义嵌入提供者示例"""

    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        # 初始化你的模型

    async def embed_text(self, text: str) -> List[float]:
        """嵌入单个文本"""
        try:
            # 实现你的嵌入逻辑
            embedding = self._compute_embedding(text)
            return embedding
        except Exception as e:
            raise ProviderError(f"Embedding failed: {e}")

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入"""
        try:
            embeddings = [self._compute_embedding(text) for text in texts]
            return embeddings
        except Exception as e:
            raise ProviderError(f"Batch embedding failed: {e}")

    def get_dimension(self) -> int:
        """返回嵌入维度"""
        return 768

    def get_max_tokens(self) -> int:
        """返回最大 token 数"""
        return 512

    async def close(self):
        """清理资源"""
        pass

    def _compute_embedding(self, text: str) -> List[float]:
        """实际的嵌入计算逻辑"""
        # 实现你的嵌入算法
        pass
```

## 常见工作流

### 工作流 1: 项目文档管理

```bash
# 1. 创建项目仓库
memory repo create my-project --description "我的项目文档"

# 2. 导入项目文档
memory ingest ./docs --repository my-project --recursive

# 3. 搜索特定主题
memory search "API 认证" --repository my-project

# 4. 提问获取详细答案
memory ask "如何实现用户认证？" --repository my-project
```

### 工作流 2: 个人知识库

```bash
# 1. 创建个人笔记仓库
memory repo create notes --description "个人笔记和学习资料"

# 2. 定期导入新笔记
memory ingest ~/Documents/notes --repository notes --recursive

# 3. 快速查找信息
memory search "Python 装饰器" --repository notes --top-k 3

# 4. 复习和总结
memory ask "总结我学习的 Python 高级特性" --repository notes
```

### 工作流 3: 多项目管理

```bash
# 1. 为每个项目创建仓库
memory repo create project-a
memory repo create project-b
memory repo create project-c

# 2. 分别导入各项目文档
memory ingest ~/projects/a/docs --repository project-a --recursive
memory ingest ~/projects/b/docs --repository project-b --recursive
memory ingest ~/projects/c/docs --repository project-c --recursive

# 3. 在特定项目中搜索
memory search "部署流程" --repository project-a

# 4. 查看所有项目状态
memory repo list
```

## 性能优化建议

### 大规模导入优化

```bash
# 增加批处理大小
export MEMORY_EMBEDDING__BATCH_SIZE=128

# 使用更快的本地模型
export MEMORY_EMBEDDING__MODEL_NAME="all-MiniLM-L6-v2"

# 调整分块大小
export MEMORY_CHUNKING__CHUNK_SIZE=256
export MEMORY_CHUNKING__CHUNK_OVERLAP=25

memory ingest large-dataset/ --repository big-project --recursive
```

### 搜索性能优化

```bash
# 减少返回结果数量
memory search "查询" --repository project --top-k 3

# 使用更小的嵌入维度
# 在 config.toml 中设置
[embedding]
model_name = "all-MiniLM-L6-v2"  # 384 维，比 768 维更快
```

## 故障排除示例

### 调试模式

```bash
# 启用详细日志
export MEMORY_LOG_LEVEL="DEBUG"
memory ingest docs/ --repository project

# 查看日志文件
tail -f ~/.memory/logs/memory.log
```

### 重建索引

```bash
# 删除旧数据
rm -rf ~/.memory/chroma/memory_project-a

# 重新导入
memory ingest docs/ --repository project-a --recursive
```

### 验证配置

```bash
# 测试配置文件
memory info --config config.toml

# 测试嵌入提供者
python -c "
from memory.config.loader import load_config
from memory.providers import create_embedding_provider
from memory.providers.base import ProviderConfig
import asyncio

async def test():
    config = load_config()
    provider = create_embedding_provider(ProviderConfig(
        provider_type=config.embedding.provider,
        model_name=config.embedding.model_name,
    ))
    result = await provider.embed_text('test')
    print(f'Embedding dimension: {len(result)}')
    await provider.close()

asyncio.run(test())
"
```
