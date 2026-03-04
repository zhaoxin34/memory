## Why

当前系统仅使用向量搜索进行召回，依赖 Embedding 模型的语义理解能力。但对于关键词精确匹配、专有名词、技术术语等场景，向量搜索效果有限。通过引入 BM25 多路召回，可以显著提升检索的准确性和召回率。

## What Changes

1. **新增 BM25 嵌入生成**: 使用 ChromaDB 内置的 `ChromaBm25EmbeddingFunction` 生成稀疏向量
2. **支持双 embedding 存储**: 在 ChromaDB collection 中同时存储 dense（向量）和 sparse（BM25）两种 embedding
3. **实现混合搜索**: 查询时同时执行向量搜索和 BM25 搜索，用 RRF 合并结果
4. **配置化支持**: 在配置文件中可调整 BM25 参数（k, b, avg_doc_length）和 RRF 权重

## Capabilities

### New Capabilities
- `bm25-embedding`: BM25 稀疏向量嵌入生成能力
- `hybrid-search`: 混合搜索能力，支持向量 + BM25 多路召回

### Modified Capabilities
- `vector-storage`: 新增支持稀疏向量存储和混合搜索

## Impact

- **依赖**: ChromaDB >= 1.5.2（内置 BM25 支持），新增 `snowballstemmer` 依赖
- **存储**: 每个文档额外存储稀疏向量（约增加 10-20% 存储空间）
- **查询性能**: 混合搜索需要执行两次查询，稍有延迟
- **配置**: 新增 `[vector_store.bm25]` 和 `[vector_store.hybrid_search]` 配置节
- **向后兼容**: 混合搜索默认关闭，现有向量搜索功能不受影响
