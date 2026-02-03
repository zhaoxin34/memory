## ADDED Requirements

### Requirement: User can ingest documents into a specific repository

系统必须允许用户在导入文档时指定目标仓库。

#### Scenario: Ingest document with repository specified

- **WHEN** 用户执行 `memory ingest <path> --repository <name>` 命令
- **THEN** 系统将文档导入到指定的仓库
- **AND** 文档的 repository_id 字段设置为指定仓库的 ID

#### Scenario: Ingest document without repository specified

- **WHEN** 用户执行 `memory ingest <path>` 命令但未指定 --repository 参数
- **THEN** 系统将文档导入到配置中的默认仓库
- **AND** 文档的 repository_id 字段设置为默认仓库的 ID

#### Scenario: Ingest document to non-existent repository

- **WHEN** 用户尝试将文档导入到不存在的仓库
- **THEN** 系统拒绝导入并返回错误消息
- **AND** 错误消息指出指定的仓库不存在

#### Scenario: Ingest multiple documents recursively

- **WHEN** 用户执行 `memory ingest <directory> --repository <name> --recursive`
- **THEN** 系统递归导入目录中的所有文档到指定仓库
- **AND** 所有文档的 repository_id 字段设置为指定仓库的 ID

### Requirement: Document chunks inherit repository association

系统必须确保文档分块继承其父文档的仓库关联。

#### Scenario: Chunk creation during ingestion

- **WHEN** 系统对文档进行分块处理
- **THEN** 每个分块的 repository_id 字段设置为其父文档的 repository_id
- **AND** 分块与文档保持相同的仓库关联

### Requirement: Embeddings are stored in repository-specific collections

系统必须将嵌入向量存储在仓库特定的向量集合中。

#### Scenario: Store embeddings for repository documents

- **WHEN** 系统为文档分块生成嵌入向量
- **THEN** 嵌入向量存储在格式为 `{base_collection}_{repository_name}` 的集合中
- **AND** 不同仓库的嵌入向量物理隔离

#### Scenario: Create vector collection for new repository

- **WHEN** 首次向新仓库导入文档
- **THEN** 系统自动创建该仓库对应的向量集合
- **AND** 集合名称遵循 `{base_collection}_{repository_name}` 格式

### Requirement: Ingestion progress shows repository information

系统必须在导入过程中显示目标仓库信息。

#### Scenario: Display repository during ingestion

- **WHEN** 用户导入文档时
- **THEN** 系统在进度信息中显示目标仓库名称
- **AND** 用户可以确认文档正在导入到正确的仓库
