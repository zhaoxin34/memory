## Context

当前 Memory 系统已经定义了 `EmbeddingProvider` 和 `VectorStore` 的抽象接口，但缺少具体实现。系统使用 provider pattern 来支持多种嵌入模型和向量数据库，配置通过 TOML 文件驱动。

**当前状态:**
- 抽象接口已定义在 `src/memory/providers/base.py` 和 `src/memory/storage/base.py`
- 已有内存实现（InMemoryVectorStore）用于测试
- CLI 命令框架已就绪，但显示 "not yet fully implemented"
- 配置系统支持 provider 和 store 类型切换

**约束:**
- 必须遵循现有的抽象接口（EmbeddingProvider, VectorStore）
- 必须支持异步操作（async/await）
- 必须支持仓库隔离（repository-based collections）
- 必须通过配置文件选择 provider 类型

## Goals / Non-Goals

**Goals:**
- 实现两个生产可用的 embedding providers（local 和 openai）
- 实现 Chroma vector store 作为持久化存储方案
- 使 CLI 命令能够真正执行文档导入和搜索
- 保持与现有架构的一致性

**Non-Goals:**
- 不实现其他 embedding providers（如 Cohere、Hugging Face API）
- 不实现其他 vector stores（如 Qdrant、Pinecone）
- 不修改现有的抽象接口
- 不实现 LLM provider（留待后续）

## Decisions

### Decision 1: Local Embedding 使用 sentence-transformers

**选择**: 使用 `sentence-transformers` 库实现本地嵌入生成。

**理由**:
- 成熟的库，支持多种预训练模型
- 易于使用，API 简洁
- 支持批量处理，性能良好
- 模型可以本地缓存，无需网络连接

**替代方案**:
- 直接使用 transformers 库：更底层，需要更多代码
- 使用 ONNX Runtime：性能更好但集成复杂度高

**实现**:
```python
from sentence_transformers import SentenceTransformer

class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self, config):
        self.model = SentenceTransformer(config.model_name)

    async def embed_text(self, text: str) -> list[float]:
        # 在线程池中运行以避免阻塞
        return await asyncio.to_thread(self.model.encode, text)
```

### Decision 2: OpenAI Embedding 使用官方 SDK

**选择**: 使用 OpenAI 官方 Python SDK (`openai` 包)。

**理由**:
- 官方支持，API 稳定
- 自动处理重试和速率限制
- 支持异步操作
- 文档完善

**替代方案**:
- 直接使用 HTTP 请求：需要自己处理认证、重试、错误
- 使用第三方封装：增加依赖复杂度

**实现**:
```python
from openai import AsyncOpenAI

class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, config):
        self.client = AsyncOpenAI(api_key=config.api_key)
        self.model = config.model_name

    async def embed_text(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            input=text,
            model=self.model
        )
        return response.data[0].embedding
```

### Decision 3: Chroma 作为默认 Vector Store

**选择**: 使用 ChromaDB 作为持久化向量存储实现。

**理由**:
- 轻量级，易于部署（单文件数据库）
- 支持持久化和内存模式
- Python 原生，无需额外服务
- 支持元数据过滤
- 与现有的仓库隔离架构兼容（支持多个 collections）

**替代方案**:
- Qdrant：需要独立服务，部署复杂
- Pinecone：云服务，需要网络和付费
- FAISS：只支持内存，无持久化

**实现**:
```python
import chromadb

class ChromaVectorStore(VectorStore):
    def __init__(self, config):
        self.client = chromadb.PersistentClient(path=config.persist_directory)
        self.collections = {}  # 缓存 collection 对象

    def _get_collection(self, repository_name: str):
        collection_name = f"{self.config.collection_name}_{repository_name}"
        if collection_name not in self.collections:
            self.collections[collection_name] = self.client.get_or_create_collection(
                name=collection_name
            )
        return self.collections[collection_name]
```

### Decision 4: CLI 初始化策略

**选择**: 在 CLI 命令中根据配置动态初始化 providers 和 stores。

**理由**:
- 灵活性：用户可以通过配置文件切换实现
- 延迟加载：只在需要时加载依赖
- 错误处理：可以在初始化时提供清晰的错误信息

**实现**:
```python
def _create_embedding_provider(config: AppConfig) -> EmbeddingProvider:
    if config.embedding.provider == "local":
        from memory.providers.local import LocalEmbeddingProvider
        return LocalEmbeddingProvider(config.embedding)
    elif config.embedding.provider == "openai":
        from memory.providers.openai import OpenAIEmbeddingProvider
        return OpenAIEmbeddingProvider(config.embedding)
    else:
        raise ValueError(f"Unknown embedding provider: {config.embedding.provider}")
```

### Decision 5: 依赖管理策略

**选择**: 使用 pyproject.toml 的 optional dependencies 分组。

**理由**:
- 用户可以只安装需要的依赖
- 减少默认安装大小
- 符合 Python 最佳实践

**实现**:
```toml
[project.optional-dependencies]
local = ["sentence-transformers>=2.2.0", "torch>=2.0.0"]
openai = ["openai>=1.0.0"]
chroma = ["chromadb>=0.4.0"]
```

用户安装：
```bash
uv sync --extra local --extra chroma  # 本地嵌入 + Chroma
uv sync --extra openai --extra chroma  # OpenAI + Chroma
```

## Risks / Trade-offs

### Risk 1: sentence-transformers 模型下载
**风险**: 首次使用时需要下载大型模型文件（几百 MB），可能失败或耗时。

**缓解**:
- 在文档中说明首次运行需要下载模型
- 提供模型缓存位置配置
- 捕获下载错误并提供清晰的错误信息

### Risk 2: OpenAI API 成本
**风险**: 用户可能不了解 API 调用成本，导致意外费用。

**缓解**:
- 在文档中明确说明 API 成本
- 记录 token 使用量到日志
- 提供批量处理以减少 API 调用次数

### Risk 3: Chroma 数据库迁移
**风险**: Chroma 版本升级可能导致数据格式不兼容。

**缓解**:
- 锁定 Chroma 版本范围
- 在文档中说明数据备份的重要性
- 未来考虑实现数据导出/导入功能

### Risk 4: 异步操作复杂度
**风险**: sentence-transformers 是同步库，需要在异步上下文中使用。

**缓解**:
- 使用 `asyncio.to_thread()` 在线程池中运行同步操作
- 确保不会阻塞事件循环
- 添加适当的超时处理

### Trade-off: 本地 vs 云端嵌入
**Local (sentence-transformers)**:
- ✅ 无 API 成本
- ✅ 隐私保护（数据不离开本地）
- ✅ 无网络依赖
- ❌ 需要本地计算资源
- ❌ 模型质量可能不如 OpenAI

**OpenAI**:
- ✅ 高质量嵌入
- ✅ 无需本地计算资源
- ❌ API 成本
- ❌ 需要网络连接
- ❌ 数据发送到第三方

## Open Questions

1. **模型选择**: 默认使用哪个 sentence-transformers 模型？
   - 建议：`all-MiniLM-L6-v2`（小巧、快速、质量不错）
   - 需要在配置中允许用户自定义

2. **批量大小**: OpenAI API 的批量请求最佳大小是多少？
   - 需要测试不同批量大小的性能
   - 考虑 API 速率限制

3. **错误重试**: 是否需要在 provider 层实现重试逻辑？
   - OpenAI SDK 已有重试机制
   - Local provider 可能需要处理 OOM 错误

4. **性能优化**: 是否需要实现嵌入缓存？
   - 对于相同文本避免重复计算
   - 可以作为未来优化
