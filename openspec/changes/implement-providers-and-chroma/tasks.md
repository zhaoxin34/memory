## 1. 依赖管理

- [x] 1.1 在 pyproject.toml 中添加 sentence-transformers 到 [project.optional-dependencies.local]
- [x] 1.2 在 pyproject.toml 中添加 torch 到 [project.optional-dependencies.local]
- [x] 1.3 在 pyproject.toml 中添加 openai 到 [project.optional-dependencies.openai]
- [x] 1.4 在 pyproject.toml 中添加 chromadb 到 [project.optional-dependencies.chroma]

## 2. Local Embedding Provider 实现

- [x] 2.1 创建 `src/memory/providers/local.py` 文件
- [x] 2.2 实现 LocalEmbeddingProvider 类，继承 EmbeddingProvider
- [x] 2.3 实现 __init__() 方法，初始化 SentenceTransformer 模型
- [x] 2.4 实现 embed_text() 方法，使用 asyncio.to_thread() 异步生成单个嵌入
- [x] 2.5 实现 embed_batch() 方法，批量生成嵌入
- [x] 2.6 实现 get_dimension() 方法，返回模型的嵌入维度
- [x] 2.7 实现 get_max_tokens() 方法，返回模型的最大 token 长度
- [x] 2.8 添加错误处理（空文本、模型加载失败、OOM 等）
- [x] 2.9 添加日志记录（模型加载、嵌入生成）

## 3. OpenAI Embedding Provider 实现

- [x] 3.1 创建 `src/memory/providers/openai.py` 文件
- [x] 3.2 实现 OpenAIEmbeddingProvider 类，继承 EmbeddingProvider
- [x] 3.3 实现 __init__() 方法，初始化 AsyncOpenAI 客户端
- [x] 3.4 实现 embed_text() 方法，调用 OpenAI embeddings API
- [x] 3.5 实现 embed_batch() 方法，批量调用 API（处理批量大小限制）
- [x] 3.6 实现 get_dimension() 方法，根据模型返回维度
- [x] 3.7 实现 get_max_tokens() 方法，根据模型返回最大 token 长度
- [x] 3.8 添加错误处理（API key 缺失、认证失败、速率限制、网络错误）
- [x] 3.9 添加 token 使用量日志记录
- [x] 3.10 实现 close() 方法，关闭 API 连接

## 4. Chroma Vector Store 实现

- [x] 4.1 创建 `src/memory/storage/chroma.py` 文件
- [x] 4.2 实现 ChromaVectorStore 类，继承 VectorStore
- [x] 4.3 实现 __init__() 方法，初始化 Chroma PersistentClient
- [x] 4.4 实现 initialize() 方法，创建或加载持久化数据库
- [x] 4.5 实现 _get_collection() 辅助方法，获取或创建仓库对应的 collection
- [x] 4.6 实现 add_embedding() 方法，存储单个嵌入到对应的 collection
- [x] 4.7 实现 add_embeddings_batch() 方法，批量存储嵌入
- [x] 4.8 实现 search() 方法，支持 repository_id 过滤的相似度搜索
- [x] 4.9 实现 delete_by_document_id() 方法，删除文档的所有嵌入
- [x] 4.10 实现 delete_by_chunk_id() 方法，删除特定分块的嵌入
- [x] 4.11 实现 delete_by_repository() 方法，删除整个仓库的 collection
- [x] 4.12 实现 count() 方法，统计所有 collections 的嵌入总数
- [x] 4.13 实现 close() 方法，持久化数据并关闭连接
- [x] 4.14 添加错误处理（目录权限、数据库损坏、维度不匹配）

## 5. Provider 工厂函数

- [x] 5.1 在 `src/memory/providers/__init__.py` 中创建 create_embedding_provider() 工厂函数
- [x] 5.2 根据配置类型动态导入并实例化对应的 provider
- [x] 5.3 添加未知 provider 类型的错误处理
- [x] 5.4 添加缺失依赖的友好错误提示（如未安装 sentence-transformers）

## 6. Storage 工厂函数

- [x] 6.1 在 `src/memory/storage/__init__.py` 中创建 create_vector_store() 工厂函数
- [x] 6.2 根据配置类型动态导入并实例化对应的 vector store
- [x] 6.3 添加未知 store 类型的错误处理
- [x] 6.4 添加缺失依赖的友好错误提示（如未安装 chromadb）

## 7. CLI 命令集成

- [x] 7.1 更新 `src/memory/interfaces/cli.py` 的 _ingest_async() 函数
- [x] 7.2 使用工厂函数创建 embedding provider 和 vector store
- [x] 7.3 初始化 IngestionPipeline 并传入 providers 和 stores
- [x] 7.4 实现文件导入逻辑（单文件和递归目录）
- [x] 7.5 添加进度显示和错误处理
- [x] 7.6 更新 _search_async() 函数，初始化 QueryPipeline
- [x] 7.7 实现搜索逻辑，显示搜索结果
- [x] 7.8 更新 _ask_async() 函数，实现问答逻辑
- [x] 7.9 移除 "not yet fully implemented" 提示
- [x] 7.10 添加友好的错误提示（如配置错误、依赖缺失）

## 8. 配置更新

- [x] 8.1 更新 config.toml 示例，添加 local provider 配置示例
- [x] 8.2 更新 config.toml 示例，添加 openai provider 配置示例
- [x] 8.3 更新 config.toml 示例，添加 chroma vector store 配置示例
- [x] 8.4 在配置注释中说明如何安装对应的依赖

## 9. 文档更新

- [x] 9.1 更新 README.md，添加依赖安装说明（uv sync --extra local/openai/chroma）
- [x] 9.2 更新 README.md，添加 provider 和 store 配置说明
- [x] 9.3 更新 CLAUDE.md，添加新实现的 provider 和 store 说明
- [x] 9.4 创建使用示例文档，展示如何使用不同的 provider 组合
- [x] 9.5 添加故障排除指南（模型下载失败、API key 错误等）

## 10. 测试

- [x] 10.1 为 LocalEmbeddingProvider 编写单元测试
- [x] 10.2 为 OpenAIEmbeddingProvider 编写单元测试（使用 mock）
- [x] 10.3 为 ChromaVectorStore 编写单元测试
- [x] 10.4 编写集成测试：local provider + chroma store
- [x] 10.5 编写集成测试：openai provider + chroma store（使用 mock）
- [x] 10.6 编写端到端测试：完整的导入和搜索流程
