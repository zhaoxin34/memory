## ADDED Requirements

### Requirement: Document type filter
仓库创建时支持指定导入的文档类型列表，系统 SHALL 仅导入匹配指定类型的文件。

#### Scenario: 创建仓库时指定单一文档类型
- **WHEN** 用户执行 `memory repo create my-repo --root-path /path --document-types md`
- **THEN** 系统仅导入 `.md` 结尾的文件

#### Scenario: 创建仓库时指定多个文档类型
- **WHEN** 用户执行 `memory repo create my-repo --root-path /path --document-types md,json`
- **THEN** 系统仅导入 `.md` 和 `.json` 结尾的文件

#### Scenario: 创建仓库时未指定文档类型（默认）
- **WHEN** 用户执行 `memory repo create my-repo --root-path /path`
- **THEN** 系统默认仅导入 `.md` 结尾的文件

#### Scenario: Sync 命令使用文档类型过滤
- **WHEN** 执行 `memory sync --repository my-repo`
- **THEN** 系统仅同步仓库配置中指定的文档类型的文件

#### Scenario: 不匹配的文件被忽略
- **WHEN** 仓库配置 document-types 为 `["md"]`，但目录中存在 `.txt` 文件
- **THEN** 系统 SHALL 忽略该 `.txt` 文件，不导入也不同步
