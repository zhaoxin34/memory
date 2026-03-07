## Why

当前知识库导入文档时，无法指定只导入特定文件类型（如仅导入 .md 文件）。用户希望能在创建仓库时指定文档类型过滤规则，简化后续同步操作。

## What Changes

- Repository 新增 `document_types` 字段（可选，支持多类型如 `["md", "json", "txt"]`）
- 默认只导入 md 类型文档
- CLI 命令 `repo create` 新增 `--document-types` 选项
- `sync` 命令根据仓库配置的 document_types 自动过滤文件

## Capabilities

### New Capabilities
- `doc-type-filter`: 支持在仓库创建时指定导入的文档类型，支持多种类型过滤

### Modified Capabilities
- (无)

## Impact

- 修改 Repository 实体
- 修改 CLI repo create 命令
- 修改 sync 命令逻辑
- 现有仓库不受影响（默认 md）
