## ADDED Requirements

### Requirement: User can create a repository

系统必须允许用户创建新的仓库，用于组织和隔离文档集合。

#### Scenario: Create repository with valid name

- **WHEN** 用户执行 `memory repo create <name>` 命令，其中 name 是有效的 kebab-case 名称
- **THEN** 系统创建新仓库并返回成功消息
- **AND** 仓库在仓库列表中可见

#### Scenario: Create repository with description

- **WHEN** 用户执行 `memory repo create <name> --description "描述文本"`
- **THEN** 系统创建仓库并保存描述信息
- **AND** 描述信息在仓库详情中可见

#### Scenario: Create repository with invalid name

- **WHEN** 用户尝试创建仓库，但名称包含非法字符（如大写字母、空格、特殊符号）
- **THEN** 系统拒绝创建并返回错误消息
- **AND** 错误消息说明名称必须是 kebab-case 格式

#### Scenario: Create repository with duplicate name

- **WHEN** 用户尝试创建已存在名称的仓库
- **THEN** 系统拒绝创建并返回错误消息
- **AND** 错误消息指出仓库名称已存在

### Requirement: User can list repositories

系统必须允许用户查看所有已创建的仓库列表。

#### Scenario: List all repositories

- **WHEN** 用户执行 `memory repo list` 命令
- **THEN** 系统显示所有仓库的列表
- **AND** 每个仓库显示名称、创建时间和文档数量

#### Scenario: List repositories when none exist

- **WHEN** 用户执行 `memory repo list` 命令但系统中没有仓库
- **THEN** 系统显示空列表消息
- **AND** 提示用户使用 `memory repo create` 创建仓库

### Requirement: User can view repository details

系统必须允许用户查看特定仓库的详细信息。

#### Scenario: View existing repository details

- **WHEN** 用户执行 `memory repo info <name>` 命令，其中 name 是已存在的仓库
- **THEN** 系统显示仓库的详细信息
- **AND** 信息包括名称、描述、创建时间、更新时间、文档数量和分块数量

#### Scenario: View non-existent repository

- **WHEN** 用户尝试查看不存在的仓库详情
- **THEN** 系统返回错误消息
- **AND** 错误消息指出仓库不存在

### Requirement: User can delete a repository

系统必须允许用户删除仓库及其所有关联数据。

#### Scenario: Delete empty repository

- **WHEN** 用户执行 `memory repo delete <name>` 命令删除不包含文档的仓库
- **THEN** 系统删除仓库并返回成功消息
- **AND** 仓库从列表中消失

#### Scenario: Delete repository with documents

- **WHEN** 用户尝试删除包含文档的仓库
- **THEN** 系统提示用户确认删除操作
- **AND** 确认后删除仓库及其所有文档、分块和嵌入

#### Scenario: Delete non-existent repository

- **WHEN** 用户尝试删除不存在的仓库
- **THEN** 系统返回错误消息
- **AND** 错误消息指出仓库不存在

#### Scenario: Delete default repository

- **WHEN** 用户尝试删除名为 "default" 的仓库
- **THEN** 系统拒绝删除并返回错误消息
- **AND** 错误消息说明默认仓库不能被删除

### Requirement: System automatically creates default repository

系统必须在首次启动时自动创建默认仓库。

#### Scenario: First system startup

- **WHEN** 系统首次启动且没有任何仓库
- **THEN** 系统自动创建名为 "default" 的仓库
- **AND** 默认仓库在配置中被标记为默认仓库

#### Scenario: Subsequent system startup

- **WHEN** 系统启动且已存在仓库
- **THEN** 系统不创建新的默认仓库
- **AND** 使用配置中指定的默认仓库
