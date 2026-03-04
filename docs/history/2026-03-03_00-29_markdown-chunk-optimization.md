# Markdown 分块优化

## 2026-03-03 00:29

### Feat: 标题链叠加

修改 `markdown_chunking.py` 中的 `smart_merge_chunks` 函数，使用 `heading_stack` 维护从一级标题到当前内容的完整标题链。每个 chunk 前叠加完整标题链，解决检索时丢失标题上下文的问题。添加基于 `(level, content)` 的去重逻辑，避免相同标题重复出现。

**相关文件**:
- `src/memory/core/markdown_chunking.py`

---

### Feat: 文件名作为一级标题

在 `chunking.py` 的 `create_chunks` 函数中，如果文档有 title 且内容不以 `# ` 开头，则在内容前添加文件名作为 H1 标题。修改 `cli.py` 始终为 markdown 文件添加文件名作为一级标题。优先使用 regex 版本的 chunking（`chunk_markdown_document`）而不是 tree-sitter 版本，以更好支持标题上下文。

**相关文件**:
- `src/memory/core/chunking.py`
- `src/memory/cli.py`

---

### Refactor: 代码简化

提取 `save_current_chunk()` 辅助函数减少重复代码，`min_chunk_size` 作为参数传递而非 hardcoded。提取 `detect_chunk_type()` 函数。

**相关文件**:
- `src/memory/core/markdown_chunking.py`

---

### Test: 测试更新

更新测试用例以适应新的 chunk 行为，添加测试用例验证标题链叠加功能。

**相关文件**:
- `tests/unit/test_markdown_chunking.py`
