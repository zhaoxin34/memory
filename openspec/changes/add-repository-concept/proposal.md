## Why

当前知识库系统将所有文档存储在单一的全局空间中，无法区分不同项目或主题的文档。用户需要能够创建多个独立的仓库（repositories），每个仓库管理自己的文档集合，使得导入、搜索和问答功能可以在特定仓库范围内操作，避免不同项目的文档相互干扰。

## What Changes

- 引入 Repository 领域模型，作为文档的逻辑容器
- 为所有文档和分块添加 repository_id 关联
- CLI 命令支持 `--repository` 参数来指定操作的仓库
- 向量存储和元数据存储支持按仓库过滤
- 配置系统支持默认仓库设置
- 提供仓库管理功能（创建、列表、删除、切换）

## Capabilities

### New Capabilities
- `repository-management`: 仓库的创建、列表、删除、查看详情等管理功能
- `repository-scoped-ingestion`: 文档导入时指定目标仓库，文档和分块关联到特定仓库
- `repository-scoped-search`: 搜索和问答功能支持在指定仓库范围内执行

### Modified Capabilities
<!-- 当前系统还没有现有的 specs，所以这里为空 -->

## Impact

### 核心模型层
- `src/memory/core/models.py`: 新增 Repository 模型，Document 和 Chunk 模型添加 repository_id 字段

### 存储层
- `src/memory/storage/base.py`: VectorStore 和 MetadataStore 接口添加 repository 过滤参数
- 所有存储实现需要支持按 repository_id 过滤查询

### 管道层
- `src/memory/pipelines/ingestion.py`: 导入管道接受 repository_id 参数
- `src/memory/pipelines/query.py`: 查询管道接受 repository_id 参数并传递给存储层

### 配置层
- `src/memory/config/schema.py`: 添加默认仓库配置选项

### 接口层
- `src/memory/interfaces/cli.py`: 所有命令添加 `--repository` 选项
- 新增仓库管理命令：`memory repo create/list/delete/info`

### 数据库迁移
- 需要为现有数据添加默认仓库（如 "default"）
- 向量数据库和元数据数据库的 schema 需要更新
