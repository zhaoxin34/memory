## Context

当前 `memory search` 命令的输出直接在 CLI 中打印硬编码格式，不便于程序化使用。二次开发者需要解析终端输出获取数据，这既脆弱也不可靠。

## Goals / Non-Goals

**Goals:**
- 添加 `--output` 参数支持多种格式
- CLI 渲染逻辑与数据结构分离
- 便于测试和程序调用

**Non-Goals:**
- 不修改 VectorStore 或 QueryPipeline 的内部逻辑
- 不添加新的搜索功能
- 不修改 `ask` 命令的 LLM 生成逻辑

## Decisions

### D1: 输出格式枚举

```python
from enum import Enum

class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
```

### D2: JSON 输出结构

```json
{
  "query": "搜索关键词",
  "total_results": 10,
  "results": [
    {
      "score": 0.95,
      "document_id": "uuid",
      "document_title": "文档标题",
      "chunk_index": 0,
      "content": "片段内容",
      "source_path": "/path/to/file"
    }
  ]
}
```

### D3: Markdown 输出格式

```markdown
## Search Results

| # | Score | Document | Content |
|---|-------|----------|---------|
| 1 | 0.95 | doc.md | ... |

### Sources
1. [doc.md](/path/to/file)
```

### D4: Typer Choice 参数

使用 Typer 的 `choice` 参数验证输入：

```python
from typer import Choice

output: OutputFormat = Choice(
    ["text", "json", "markdown"],
    case_sensitive=False,
)
```

## Risks / Trade-offs

| 风险 | 影响 | 缓解 |
|-----|------|-----|
| JSON 字段变更 | 二次开发兼容 | 使用版本号前缀 `v1.` |
| 特殊字符转义 | JSON 输出错误 | 使用 `json.dumps` 正确转义 |
| 大文本溢出 | Markdown 表格截断 | 截断并标注 `[...]` |

## Migration Plan

1. 添加 `OutputFormat` 枚举
2. 修改 CLI 的 `_search_async` 函数接受 `output` 参数
3. 创建渲染函数：`render_json()`, `render_markdown()`, `render_text()`
4. 测试三种输出格式
