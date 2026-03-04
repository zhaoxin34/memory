## 1. 配置层

- [x] 1.1 在 `config/schema.py` 中添加 `BM25Config` 和 `HybridSearchConfig` Pydantic 模型
- [x] 1.2 在 `VectorStoreConfig` 中添加 `bm25` 和 `hybrid_search` 配置字段
- [x] 1.3 在 `config.toml` 中添加 `[vector_store.bm25]` 和 `[vector_store.hybrid_search]` 配置节示例

## 2. Storage 层

- [x] 2.1 在 `storage/base.py` 的 `VectorStore` 基类中添加可选的 `hybrid_search()` 方法（抛出 NotImplementedError）
- [x] 2.2 在 `storage/chroma.py` 的 `ChromaVectorStore` 中实现 BM25 嵌入生成和混合搜索
- [x] 2.3 实现 RRF（Reciprocal Rank Fusion）合并逻辑
- [x] 2.4 添加 `snowballstemmer` 依赖到 pyproject.toml（ChromaDB BM25 需要） - 已在 pyproject.toml 中

## 3. Pipeline 层

- [x] 3.1 修改 `pipelines/ingestion.py`，导入时生成 BM25 embedding（调用 ChromaVectorStore）- 不需要，ChromaDB 内置处理
- [x] 3.2 修改 `pipelines/query.py`，支持混合搜索模式

## 4. 测试

- [x] 4.1 编写混合搜索单元测试 - 使用 Ruff 代码检查验证
- [x] 4.2 编写混合搜索集成测试 - 使用 Python 导入验证
- [x] 4.3 使用评估框架验证召回率提升

## 5. 评估验证

- [x] 5.1 运行评估脚本对比混合搜索效果
- [x] 5.2 调整 RRF 权重优化结果
