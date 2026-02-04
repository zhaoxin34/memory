## Why

当前 Memory 系统的 CLI 命令显示 "not yet fully implemented"，因为缺少具体的 embedding provider 和 vector store 实现。用户无法实际使用 `memory ingest`、`memory search` 和 `memory ask` 命令来导入文档和进行语义搜索。需要实现核心的 provider 和 storage 组件，使系统能够真正工作。

## What Changes

- 实现 Local Embedding Provider（使用 sentence-transformers）
- 实现 OpenAI Embedding Provider（使用 OpenAI API）
- 实现 Chroma Vector Store（持久化向量存储）
- 更新 CLI 命令，初始化并使用这些具体实现
- 添加必要的依赖包（sentence-transformers, openai, chromadb）

## Capabilities

### New Capabilities
- `local-embedding-provider`: 本地嵌入生成能力，使用 sentence-transformers 模型在本地生成文本嵌入
- `openai-embedding-provider`: OpenAI 嵌入生成能力，通过 OpenAI API 生成文本嵌入
- `chroma-vector-store`: Chroma 向量存储能力，持久化存储和检索向量嵌入

### Modified Capabilities
<!-- 无现有能力需要修改 -->

## Impact

**受影响的代码:**
- `src/memory/providers/` - 新增 local.py 和 openai.py
- `src/memory/storage/` - 新增 chroma.py
- `src/memory/interfaces/cli.py` - 更新命令实现，初始化 providers 和 stores
- `pyproject.toml` - 添加新依赖

**依赖变更:**
- 新增：sentence-transformers（本地嵌入）
- 新增：openai（OpenAI API 客户端）
- 新增：chromadb（向量数据库）

**用户影响:**
- 用户可以开始实际使用 `memory ingest`、`memory search` 和 `memory ask` 命令
- 需要根据配置安装相应的可选依赖（`uv sync --extra local` 或 `--extra openai`）
