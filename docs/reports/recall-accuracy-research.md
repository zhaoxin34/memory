# 向量检索召回准确率技术调研

## 一、向量检索常见算法

### 1.1 相似度度量算法

#### 余弦相似度 (Cosine Similarity)

**原理**: 计算两个向量夹角的余弦值，范围[-1, 1]

```
cosine(A, B) = (A · B) / (||A|| × ||B||)
```

**优点**:
- 只关注方向，不受向量长度影响
- 计算效率较高
- 在文本嵌入中表现稳定

**缺点**:
- 未考虑向量 magnitude
- 对于归一化向量，与点积等价

**适用场景**: 文本检索、语义匹配、推荐系统

ChromaDB 默认使用余弦相似度，分数范围 0-1。

#### 点积 (Dot Product)

**原理**: 对应元素相乘后求和

```
dot(A, B) = Σ(Ai × Bi)
```

**优点**: 计算最快
**缺点**: 值域无界，难以直观理解

#### 欧氏距离 (Euclidean Distance)

**原理**: 向量差的二范数

```
L2(A, B) = √(Σ(Ai - Bi)²)
```

### 1.2 近似最近邻 (ANN) 算法

| 算法 | 原理 | 优点 | 缺点 | 适用场景 |
|------|------|------|------|----------|
| **HNSW** | 分层图结构 | 高召回、低延迟 | 内存占用大 | 生产环境首选 |
| **IVF** | 倒排索引+聚类 | 内存效率高 | 召回率依赖聚类数 | 大规模数据 |
| **PQ** | 乘积量化压缩 | 内存占用极低 | 精度有损 | 超大规模检索 |

---

## 二、如何设置合理的召回阈值

### 2.1 基于任务类型

| 任务类型 | 推荐阈值 | 说明 |
|----------|----------|------|
| 语义搜索 | 0.6-0.8 | 需要平衡召回和 precision |
| 问答系统 | 0.7-0.85 | 准确性要求高 |
| 推荐系统 | 0.5-0.7 | 注重多样性 |
| 相似文档检测 | 0.75-0.9 | 相似度要求高 |
| 聚类分析 | 0.4-0.6 | 阈值可适当降低 |

### 2.2 动态阈值策略

```python
# 自适应阈值示例
def adaptive_threshold(query, top_k=10):
    # 1. 获取候选结果及其分数
    candidates = vector_store.search(query, top_k=top_k*3)

    # 2. 计算分数分布
    scores = [c.score for c in candidates]
    mean_score = np.mean(scores)
    std_score = np.std(scores)

    # 3. 动态设置阈值（基于分数分布）
    threshold = mean_score - 0.5 * std_score

    # 4. 过滤低分结果
    return [c for c in candidates if c.score >= threshold]
```

---

## 三、如何优化召回准确率

### 3.1 Embedding 模型选择

#### 常用模型推荐

| 模型 | 维度 | 特点 | 适用场景 |
|------|------|------|----------|
| **text-embedding-3-small** | 1536 | OpenAI 最新，性价比高 | 通用场景 |
| **text-embedding-3-large** | 3072 | 精度最高，延迟较高 | 高精度需求 |
| **all-MiniLM-L6-v2** | 384 | 轻量级，本地部署首选 | 低延迟场景 |
| **bge-large-zh-v1.5** | 1024 | 中文最优 | 中文检索 |
| **bge-m3** | 1024 | 多语言支持 | 跨语言场景 |

### 3.2 Rerank（重排序）优化

两阶段检索架构：

```
Query → [粗召回(ANN)] → 候选集 → [精排(Rerank)] → 最终结果
                    (top 100-500)      (top 10-20)
```

常用 Rerank 模型：

| 模型 | 类型 | 效果提升 |
|------|------|----------|
| **bge-reranker-base** | 交叉编码器 | +10-15% |
| **bge-reranker-large** | 交叉编码器 | +15-20% |
| **RankGPT** | LLM重排 | +20-30% |

### 3.3 分块策略优化

| 策略 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 固定分块 | 简单可控 | 可能切断语义 | 结构化文档 |
| 递归分块 | 保留语义 | 实现复杂 | 通用文本 |
| 语义分块 | 语义完整 | 计算开销大 | 重要内容段落 |
| 文档结构分块 | 保留结构 | 依赖文档格式 | Markdown/HTML |

### 3.4 混合检索

```python
# 向量检索 + 关键词检索融合 (RRF)
def hybrid_search(query, alpha=0.7):
    vector_results = vector_store.search(query, top_k=50)
    bm25_results = bm25.search(query, top_k=50)

    scores = {}
    for rank, doc in enumerate(vector_results):
        scores[doc.id] = scores.get(doc.id, 0) + alpha / (rank + 60)
    for rank, doc in enumerate(bm25_results):
        scores[doc.id] = scores.get(doc.id, 0) + (1-alpha) / (rank + 60)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

---

## 四、业界常用评估指标

### 4.1 召回类指标

#### Recall@K

```
Recall@K = | Relevant ∩ Retrieved@K | / | Relevant |
```

衡量找全相关文档的能力。

### 4.2 精确类指标

#### Precision@K

```
Precision@K = | Relevant ∩ Retrieved@K | / K
```

### 4.3 排序类指标

#### Mean Average Precision (mAP)

```
AP = Σ( Precision@i × rel_i ) / |Relevant|
mAP = Σ(AP) / N_queries
```

综合考虑召回率和排序位置，是最全面的指标。

#### nDCG (Normalized Discounted Cumulative Gain)

考虑相关度等级的 DCG 归一化值，适用于有相关度分级的场景。

### 4.4 指标选择建议

| 场景 | 推荐指标 |
|------|----------|
| 通用检索系统 | mAP, nDCG |
| 问答系统 | Recall@1, MRR |
| 推荐系统 | Precision@K, Recall@K |
| 相似度检测 | F1@K |

---

## 五、开源评估工具

### 5.1 BEIR (Benchmarking IR)

- 17+ 标准数据集
- 支持多种检索模型对比

```python
from beir import util
from beir.retrieval import Retrieval

url = "https://public.ukp.informatik.tu-darmstadt.de/reuters21578-xtreme/v1.0/reuters21578.tar.gz"
data_path = util.download_and_unzip(url, "datasets")

retrieval = Retrieval(model, score_function="cos_sim")
results = retrieval.evaluate(qrels, corpus, queries)
```

### 5.2 MTEB (Massive Text Embedding Benchmark)

- 100+ 数据集
- 80+ 嵌入模型对比

```python
import mteb

tasks = mteb.get_tasks(tasks=["MSMARCO"])
evaluation = mteb.MTEB(tasks=tasks)
results = evaluation.run(model)
```

### 5.3 RAG 评估工具

- **LangChain Evaluation**: 评估 RAG 系统
- **RAGAs**: RAG 系统专用评估（faithfulness, answer relevance, context precision/recall）
- **DeepEval**: LLM 应用评估

---

## 六、优化优先级

| 优先级 | 优化方向 | 影响 |
|--------|----------|------|
| 1 | Embedding 模型选择 | 30-50% |
| 2 | Rerank 策略 | 10-25% |
| 3 | 分块策略 | 5-15% |
| 4 | 检索算法调优 | 5-10% |

---

## 七、实践建议

1. **建立评估集**: 人工标注 100-500 条 query-doc 对
2. **A/B 测试**: 对比不同方案的线上效果
3. **持续监控**: 追踪线上 recall@10 等指标
4. **定期重训**: 根据反馈数据更新模型

---

## 八、当前系统状态

### 配置信息

- **Embedding 模型**: `text-embedding-v4` (阿里云百炼)
- **向量库**: ChromaDB (使用余弦相似度)
- **分块策略**: tree-sitter 语义分块

### 分数解读

ChromaDB 余弦相似度分数范围 0-1：
- 0.7-0.8: 高度相关
- 0.5-0.7: 相关
- 0.3-0.5: 弱相关
- < 0.3: 不太相关

### 下一步优化方向

1. 考虑更换为中文优化模型 (bge-large-zh-v1.5)
2. 添加 Rerank 阶段提升精度
3. 建立完整的评估流程 (recall@K, mAP, nDCG)
