## Why

当前基于正则表达式的 Markdown 分块无法正确处理表格、嵌套列表等语义结构，导致分块质量差、语义断裂。改用 tree-sitter 可以基于准确的语法树进行分块，保证语义边界的完整性和上下文的连贯性。

## What Changes

- 新增 `tree-sitter-markdown` 依赖
- 创建 `src/memory/core/tree_sitter_chunking.py`，基于语法树的分块实现
- 修改 `src/memory/core/chunking.py`，切换到 tree-sitter 分块策略
- 支持完整的 Markdown 语法：表格、列表（含嵌套）、引用、代码块、标题层级
- 保持与现有配置的兼容性（chunk_size、overlap 参数）
- **BREAKING**: 移除原有的正则表达式分块逻辑

## Capabilities

### New Capabilities
- `tree-sitter-chunker`: 基于 tree-sitter 语法树的 Markdown 智能分块器
- `markdown-semantic-boundary`: 语义边界检测，确保分块不切断句子和逻辑单元

### Modified Capabilities
- `document-chunking`: Markdown 文档分块策略从正则表达式改为 tree-sitter 语法树解析（需更新规格）

## Impact

- **代码文件**: 新增 `src/memory/core/tree_sitter_chunking.py`，修改 `src/memory/core/chunking.py`
- **依赖**: 添加 `tree-sitter>=0.23` 和 `tree-sitter-markdown>=0.4` 作为可选依赖
- **配置**: 保持向后兼容，现有 chunking 配置无需修改
- **CLI**: 分块行为变化，输出日志显示使用 tree-sitter 分块
