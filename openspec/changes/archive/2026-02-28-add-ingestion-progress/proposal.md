## Why

当前批量导入文档时没有显示进度，用户无法了解当前处理状态。当导入大量文档时，用户只能等待而不知道还有多少文档需要处理。添加进度显示可以提升用户体验，让用户了解导入进度。

## What Changes

- 在 CLI 的 `_ingest_async` 函数中添加进度显示
- 使用 Rich 库的 Progress 组件显示进度条
- 显示：总文档数、已完成数、当前处理的文件、耗时估算
- 支持单文件导入时的快速反馈
- **BREAKING**: 无破坏性变更，仅新增功能

## Capabilities

### New Capabilities
- `ingestion-progress`: 在批量导入文档时显示实时进度
- `progress-indicator`: 进度指示器，支持进度条和百分比显示

### Modified Capabilities
- 无（不修改现有功能的行为）

## Impact

- **修改文件**: `src/memory/interfaces/cli.py`
- **依赖**: Rich 库（已存在于项目中）
- **日志**: 新增进度相关的日志事件
- **CLI**: 批量导入时显示进度条，单文件导入保持简洁输出
