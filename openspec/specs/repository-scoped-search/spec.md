## ADDED Requirements

### Requirement: User can search within a specific repository

系统必须允许用户在指定仓库范围内执行语义搜索。

#### Scenario: Search with repository specified

- **WHEN** 用户执行 `memory search "<query>" --repository <name>` 命令
- **THEN** 系统仅在指定仓库的文档中搜索
- **AND** 搜索结果只包含该仓库的文档分块

#### Scenario: Search without repository specified

- **WHEN** 用户执行 `memory search "<query>"` 命令但未指定 --repository 参数
- **THEN** 系统在配置中的默认仓库中搜索
- **AND** 搜索结果只包含默认仓库的文档分块

#### Scenario: Search in non-existent repository

- **WHEN** 用户尝试在不存在的仓库中搜索
- **THEN** 系统返回错误消息
- **AND** 错误消息指出指定的仓库不存在

#### Scenario: Search in empty repository

- **WHEN** 用户在不包含任何文档的仓库中搜索
- **THEN** 系统返回空结果
- **AND** 提示用户该仓库中没有文档

### Requirement: User can ask questions within a specific repository

系统必须允许用户在指定仓库范围内执行基于 LLM 的问答。

#### Scenario: Ask question with repository specified

- **WHEN** 用户执行 `memory ask "<question>" --repository <name>` 命令
- **THEN** 系统仅从指定仓库检索相关文档分块
- **AND** LLM 生成的答案仅基于该仓库的内容

#### Scenario: Ask question without repository specified

- **WHEN** 用户执行 `memory ask "<question>"` 命令但未指定 --repository 参数
- **THEN** 系统从配置中的默认仓库检索内容
- **AND** LLM 生成的答案仅基于默认仓库的内容

#### Scenario: Ask question in non-existent repository

- **WHEN** 用户尝试在不存在的仓库中提问
- **THEN** 系统返回错误消息
- **AND** 错误消息指出指定的仓库不存在

### Requirement: Search results include repository information

系统必须在搜索结果中显示文档所属的仓库信息。

#### Scenario: Display repository in search results

- **WHEN** 用户执行搜索或问答命令
- **THEN** 每个结果显示其所属的仓库名称
- **AND** 用户可以确认结果来自正确的仓库

### Requirement: Vector search is scoped to repository collection

系统必须确保向量搜索仅在目标仓库的向量集合中执行。

#### Scenario: Query vector collection for repository

- **WHEN** 系统执行语义搜索
- **THEN** 向量搜索仅在格式为 `{base_collection}_{repository_name}` 的集合中执行
- **AND** 不会检索其他仓库的向量数据
