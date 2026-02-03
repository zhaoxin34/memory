## Context

当前 Memory 系统采用单一全局命名空间存储所有文档，所有文档、分块和嵌入都存储在同一个集合中。这种设计在多项目或多主题场景下会导致：

1. 搜索结果混杂不同项目的内容
2. 无法按项目管理文档生命周期
3. 无法实现项目级别的访问控制或配额管理

系统当前架构：

- 核心模型：Document, Chunk, Embedding, SearchResult
- 存储层：VectorStore（向量存储）和 MetadataStore（元数据存储）分离
- 管道层：IngestionPipeline 和 QueryPipeline 协调各层操作
- 所有操作都是异步的（async/await）

## Goals / Non-Goals

**Goals:**

- 引入 Repository 作为文档的逻辑隔离单元
- 所有现有功能（导入、搜索、问答）支持仓库范围操作
- 向后兼容：现有数据自动迁移到默认仓库
- 保持当前架构的模块化和可扩展性

**Non-Goals:**

- 不实现仓库级别的权限控制（未来功能）
- 不支持跨仓库搜索（可作为未来增强）
- 不改变现有的 Provider 和 Storage 抽象接口的核心设计
- 不实现仓库间的文档移动或复制（未来功能）

## Decisions

### Decision 1: Repository 作为一等公民模型

**选择**: 在 `core/models.py` 中创建 Repository 作为独立的领域模型，而不是仅作为字符串标识符。

**理由**:

- Repository 有自己的元数据（名称、描述、创建时间、文档数量等）
- 便于未来扩展（如配额、权限、配置等）
- 提供类型安全和验证

**实现**:

```python
class Repository(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., pattern="^[a-z0-9-]+$")  # kebab-case
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Decision 2: Document 和 Chunk 添加 repository_id 外键

**选择**: 在 Document 和 Chunk 模型中添加必需的 `repository_id: UUID` 字段。

**理由**:

- 每个文档必须属于一个仓库（强制隔离）
- Chunk 继承其父 Document 的 repository_id（数据一致性）
- 支持在存储层高效过滤

### Decision 3: 存储层接口扩展而非重写

**选择**: 在现有 VectorStore 和 MetadataStore 接口的方法中添加可选的 `repository_id` 参数。

**理由**:

- 最小化对现有实现的影响
- 向后兼容：repository_id=None 表示查询所有仓库（用于迁移期）
- 符合开闭原则：扩展而非修改

**实现示例**:

```python
async def search(
    self,
    query_vector: list[float],
    top_k: int = 10,
    repository_id: Optional[UUID] = None,  # 新增
    filters: Optional[dict] = None
) -> list[SearchResult]:
```

### Decision 4: 默认仓库策略

**选择**:

- 系统启动时自动创建名为 "default" 的仓库
- 配置文件支持 `default_repository` 设置
- CLI 命令未指定 `--repository` 时使用默认仓库

**理由**:

- 简化用户体验：单仓库用户无需显式管理
- 平滑迁移：现有数据迁移到 "default" 仓库
- 灵活性：高级用户可以更改默认仓库

### Decision 5: CLI 命令设计

**选择**:

- 所有现有命令添加 `--repository <name>` 选项
- 新增 `memory repo` 子命令组管理仓库

**命令结构**:

```bash
# 仓库管理
memory repo create <name> [--description "..."]
memory repo list
memory repo info <name>
memory repo delete <name>

# 现有命令扩展
memory ingest <path> --repository <name>
memory search <query> --repository <name>
memory ask <question> --repository <name>
```

**理由**:

- 符合 CLI 最佳实践（子命令分组）
- 向后兼容：不指定 --repository 使用默认仓库
- 清晰的命令层次结构

### Decision 6: 向量存储的集合策略

**选择**: 每个仓库使用独立的向量存储集合（collection）。

**理由**:

- 物理隔离：不同仓库的向量完全分离
- 性能优化：搜索只在目标集合中进行，避免全局过滤
- 支持不同仓库使用不同的嵌入模型（未来扩展）

**实现**:

- Collection 命名：`{base_collection_name}_{repository_name}`
- 例如：`memory_default`, `memory_project-a`

## Open Questions

1. **跨仓库搜索**: 是否需要支持同时搜索多个仓库？如果需要，API 如何设计？
   - 建议：暂不支持，未来可以添加 `--repositories` 参数接受多个仓库名

2. **仓库重命名**: 是否支持仓库重命名？如果支持，如何处理向量存储集合的重命名？
   - 建议：暂不支持，删除旧仓库并创建新仓库

3. **仓库配额**: 是否需要限制每个仓库的文档数量或存储大小？
   - 建议：暂不实现，作为未来增强功能

4. **仓库导出/导入**: 是否需要支持仓库级别的数据导出和导入？
   - 建议：作为未来功能，当前可以通过备份整个数据目录实现
