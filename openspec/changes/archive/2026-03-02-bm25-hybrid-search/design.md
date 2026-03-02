## Context

当前系统使用 ChromaDB + Embedding 向量搜索进行文档召回。ChromaDB 已升级到 1.5.2，原生支持 BM25 稀疏向量和 RRF（Reciprocal Rank Fusion）混合搜索。

本设计基于 proposal 中定义的能力：BM25 嵌入生成 + 混合搜索。

## Goals / Non-Goals

**Goals:**
1. 实现 BM25 稀疏向量生成，作为向量搜索的补充
2. 支持向量搜索 + BM25 混合召回，用 RRF 合并结果
3. 配置化 BM25 参数（k, b, avg_doc_length）和 RRF 权重
4. 保持向后兼容，不影响现有向量搜索功能

**Non-Goals:**
1. 不替换现有向量搜索，仅作为增强
2. 不支持其他稀疏向量算法（如 SPLADE）
3. 不迁移已有数据（新建 collection 或增量添加）

## Decisions

### D1: BM25 实现位置

**决策**: BM25 稀疏向量生成不作为独立 Provider，而是集成到 `ChromaVectorStore` 内部。

**理由**:
- BM25 依赖 ChromaDB 内置的 `ChromaBm25EmbeddingFunction`
- 与独立 EmbeddingProvider（OpenAI/本地模型）性质不同
- 避免增加不必要的抽象层

```python
# 存储结构
{
    "id": "chunk_id",
    "embedding": [0.1, 0.2, ...],  # dense 向量
    "metadatas": {
        "sparse_embedding": {...},  # BM25 稀疏向量存 metadata
        "document_id": "...",
        ...
    }
}
```

### D2: 混合搜索 RRF 权重

**决策**: 默认向量搜索权重 0.7，BM25 权重 0.3，可配置。

**理由**: 向量搜索语义理解更强，BM25 关键词匹配更精确。7:3 比例是常见实践，可根据实际效果调整。

### D3: BM25 分词器

**决策**: 使用 ChromaDB 内置 BM25，默认参数（k=1.2, b=0.75）。

**理由**: ChromaDB BM25 内置英文分词器，对中文效果有限。对于中文文档，考虑后续支持 jieba 分词。

### D4: 向后兼容

**决策**: 通过配置控制是否启用 BM25 和混合搜索。

**理由**: 现有系统稳定运行，新增功能可逐步灰度开启。

## Risks / Trade-offs

**[Risk]** 存储空间增加
→ **Mitigation**: BM25 稀疏向量通常比 dense 向量小，预计增加 10-20% 存储空间。

**[Risk]** 查询延迟增加
→ **Mitigation**: 混合搜索需要执行两次查询（向量 + BM25），预计增加 20-50ms 延迟。可通过异步并行查询优化。

**[Risk]** 中文分词效果差
→ **Mitigation**: 当前 ChromaDB BM25 使用英文分词器，对中文支持有限。后续可考虑 jieba 分词器。

**[Risk]** 已有数据迁移
→ **Mitigation**: 增量添加新文档的 BM25 embedding，已有文档保持向量搜索不变。

**[Risk]** 其他 VectorStore 不支持混合搜索
→ **Mitigation**: 在 `VectorStore` 基类中定义可选的 `hybrid_search()` 方法，抛出 `NotImplementedError`。只有 ChromaVectorStore 实现完整功能。

**[Risk]** ChromaDB 版本依赖
→ **Mitigation**: 在 `proposal.md` 中明确 ChromaDB >= 1.5.2 版本要求。

## Migration Plan

1. **Phase 1**: 添加配置模型（BM25Config, HybridSearchConfig）
2. **Phase 2**: 在 VectorStore 基类添加可选的 `hybrid_search()` 接口
3. **Phase 3**: 在 ChromaVectorStore 中实现 BM25 嵌入和混合搜索
4. **Phase 4**: 修改 pipelines 支持混合搜索模式
5. **Phase 5**: 测试验证

## Open Questions

1. **Q1**: BM25 参数（k, b）是否需要暴露给用户配置？
   - 建议：先使用默认值，后续根据效果调整

2. **Q2**: 是否需要为已有文档批量生成 BM25 embedding？
   - 建议：暂不处理增量，保持现状

3. **Q3**: 如何评估混合搜索效果？
   - 建议：使用现有评估框架，对比开启/关闭混合搜索的召回率
