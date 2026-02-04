## 1. 核心模型层

- [x] 1.1 在 `src/memory/core/models.py` 中创建 Repository 模型（包含 id, name, description, created_at, updated_at, metadata 字段）
- [x] 1.2 为 Document 模型添加 repository_id 字段（UUID 类型，必需）
- [x] 1.3 为 Chunk 模型添加 repository_id 字段（UUID 类型，必需）
- [x] 1.4 更新 Document 和 Chunk 的 metadata 字段，包含 repository_name 信息
- [x] 1.5 为 Repository 模型添加 name 验证（kebab-case 格式）

## 2. 存储层接口扩展

- [x] 2.1 在 `src/memory/storage/base.py` 的 VectorStore.search() 方法添加可选的 repository_id 参数
- [x] 2.2 在 VectorStore.add_embedding() 和 add_embeddings_batch() 方法中支持 repository_id
- [x] 2.3 在 VectorStore 添加 delete_by_repository() 方法
- [x] 2.4 在 MetadataStore.add_document() 中支持 repository_id
- [x] 2.5 在 MetadataStore.get_document() 和 list_documents() 中添加 repository_id 过滤参数
- [x] 2.6 在 MetadataStore 添加 Repository CRUD 方法（add_repository, get_repository, list_repositories, delete_repository）
- [x] 2.7 在 MetadataStore 添加 get_repository_by_name() 方法

## 3. 存储层实现（内存和 SQLite）

- [x] 3.1 实现内存 VectorStore 的 repository_id 过滤逻辑
- [x] 3.2 实现内存 VectorStore 的按仓库集合隔离（使用 collection_name_{repository_name} 格式）
- [x] 3.3 实现内存 MetadataStore 的 Repository CRUD 操作
- [x] 3.4 实现内存 MetadataStore 的 repository_id 过滤逻辑
- [x] 3.5 为 SQLite MetadataStore 添加 repositories 表的 schema
- [x] 3.6 实现 SQLite MetadataStore 的 Repository CRUD 操作
- [x] 3.7 更新 SQLite 的 documents 和 chunks 表，添加 repository_id 列

## 4. 管道层更新

- [x] 4.1 更新 `src/memory/pipelines/ingestion.py` 的 IngestionPipeline.__init__() 接受 repository_id 参数
- [x] 4.2 更新 IngestionPipeline.ingest_document() 将 repository_id 传递给 Document 创建
- [x] 4.3 更新 IngestionPipeline.ingest_file() 接受 repository_id 参数
- [x] 4.4 更新分块创建逻辑，确保 Chunk 继承 Document 的 repository_id
- [x] 4.5 更新向量存储调用，使用 repository-specific 集合名称
- [x] 4.6 更新 `src/memory/pipelines/query.py` 的 QueryPipeline.__init__() 接受 repository_id 参数
- [x] 4.7 更新 QueryPipeline.search() 将 repository_id 传递给 VectorStore
- [x] 4.8 更新 QueryPipeline.answer() 将 repository_id 传递给搜索和检索逻辑

## 5. 配置层更新

- [x] 5.1 在 `src/memory/config/schema.py` 的 AppConfig 中添加 default_repository 字段（默认值 "default"）
- [x] 5.2 更新配置加载逻辑，支持 MEMORY_DEFAULT_REPOSITORY 环境变量
- [x] 5.3 在配置示例文件中添加 default_repository 配置说明

## 6. 仓库管理逻辑

- [x] 6.1 创建 `src/memory/core/repository.py` 模块
- [x] 6.2 实现 RepositoryManager 类，封装仓库 CRUD 操作
- [x] 6.3 实现 create_repository() 方法（包含名称验证和重复检查）
- [x] 6.4 实现 list_repositories() 方法
- [x] 6.5 实现 get_repository() 和 get_repository_by_name() 方法
- [x] 6.6 实现 delete_repository() 方法（包含级联删除文档、分块、嵌入）
- [x] 6.7 实现 ensure_default_repository() 方法（系统启动时自动创建）

## 7. CLI 接口更新

- [x] 7.1 在 `src/memory/interfaces/cli.py` 的 ingest 命令添加 --repository 选项
- [x] 7.2 在 search 命令添加 --repository 选项
- [x] 7.3 在 ask 命令添加 --repository 选项
- [x] 7.4 创建 `memory repo` 子命令组
- [x] 7.5 实现 `memory repo create <name>` 命令（支持 --description 选项）
- [x] 7.6 实现 `memory repo list` 命令
- [x] 7.7 实现 `memory repo info <name>` 命令
- [x] 7.8 实现 `memory repo delete <name>` 命令（包含确认提示）
- [x] 7.9 更新 CLI 命令的配置加载逻辑，获取 default_repository
- [x] 7.10 在命令执行前调用 ensure_default_repository()

## 8. 数据迁移工具

- [ ] 8.1 创建 `src/memory/migrations/` 模块
- [ ] 8.2 实现 migrate_to_repositories() 函数
- [ ] 8.3 实现现有文档迁移逻辑（添加 repository_id = default_repo_id）
- [ ] 8.4 实现现有分块迁移逻辑（添加 repository_id）
- [ ] 8.5 实现向量集合迁移逻辑（重命名为 collection_default）
- [ ] 8.6 添加 `memory migrate` CLI 命令
- [ ] 8.7 实现迁移前备份功能
- [ ] 8.8 实现迁移回滚功能

## 9. 测试

- [ ] 9.1 为 Repository 模型编写单元测试
- [ ] 9.2 为 RepositoryManager 编写单元测试
- [ ] 9.3 为存储层的 repository_id 过滤编写单元测试
- [ ] 9.4 为管道层的 repository 支持编写集成测试
- [ ] 9.5 为 CLI 仓库管理命令编写测试
- [ ] 9.6 为数据迁移工具编写测试
- [ ] 9.7 编写端到端测试（创建仓库 → 导入文档 → 搜索 → 删除仓库）

## 10. 文档更新

- [x] 10.1 更新 README.md，添加仓库概念说明
- [x] 10.2 更新 CLAUDE.md，添加仓库相关的架构说明
- [x] 10.3 创建仓库使用示例文档
- [x] 10.4 更新配置文档，说明 default_repository 选项
- [x] 10.5 创建数据迁移指南
