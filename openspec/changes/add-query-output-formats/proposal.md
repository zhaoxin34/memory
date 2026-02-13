## Why

当前 `memory search` 命令的输出格式是硬编码的纯文本，二次开发需要解析 CLI 输出，不够灵活。添加 JSON 和 Markdown 输出格式支持，便于程序化处理和文档集成。

## What Changes

- 重构 CLI 的搜索逻辑，返回结构化数据
- 为 `search` 命令添加 `--output` 参数，支持 `json`、`markdown`、`text` 三种格式
- 为 `ask` 命令也添加 `--output` 参数（JSON 格式用于获取来源信息）
- **BREAKING**: `--output text` 为默认格式，保持向后兼容

## Capabilities

### New Capabilities
- `query-output-format`: 支持多种输出格式（json, markdown, text）的查询能力

### Modified Capabilities
- 无（现有 search/ask 行为不变，仅添加输出格式选择）

## Impact

- **修改文件**: `src/memory/interfaces/cli.py`
- **CLI 参数**: 新增 `--output` 参数（默认值: text）
- **日志**: 输出格式变化不影响日志
