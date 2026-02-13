## 1. 依赖和环境准备

- [x] 1.1 在 `pyproject.toml` 中添加 `tree-sitter>=0.23` 和 `tree-sitter-markdown>=0.4` 作为可选依赖
- [x] 1.3 创建 `src/memory/core/tree_sitter_chunking.py` 文件

## 2. 语法树解析模块

- [x] 2.1 实现 `parse_markdown_syntax_tree(text: str)` 函数，返回 tree-sitter 语法树
- [x] 2.2 实现 `extract_semantic_nodes(tree)` 函数，遍历语法树提取语义节点
- [x] 2.3 添加表格节点识别（table, table_row, table_cell）
- [x] 2.4 添加列表节点识别（bullet_list, ordered_list, list_item）
- [x] 2.5 添加嵌套结构处理（缩进列表、嵌套引用）

## 3. 智能分块实现

- [x] 3.1 实现 `tree_sitter_chunk_document(document, config)` 主函数
- [x] 3.2 实现 `merge_to_target_size(nodes, target_size, overlap)` 合并逻辑
- [x] 3.3 实现 `get_heading_context(node)` 函数，提取标题上下文（在 `_extract_context_from_chunk` 中实现）
- [x] 3.4 实现大代码块的空白行拆分逻辑
- [x] 3.5 实现表格完整性保持逻辑

## 4. 元数据和回退策略

- [x] 4.1 在 chunk metadata 中添加 `chunk_type` 字段
- [x] 4.2 降级函数已在 chunking.py 中实现（tree-sitter → regex → fixed-size）
- [x] 4.3 添加解析超时处理（5秒）
- [x] 4.4 添加解析失败时的警告日志

## 5. 集成到现有管道

- [x] 5.1 修改 `src/memory/core/chunking.py` 的 `create_chunks()` 函数
- [x] 5.2 添加 tree-sitter 可用性检测（在 tree_sitter_chunk_document 中）
- [x] 5.3 实现无缝回退：tree-sitter → regex-based → fixed-size
- [x] 5.4 更新日志输出，显示使用的分块策略

## 6. 测试

- [x] 6.1 编写表格分块测试用例（在 test_tree_sitter_chunking.py）
- [x] 6.2 编写嵌套列表分块测试用例（在 test_tree_sitter_chunking.py）
- [x] 6.3 编写标题上下文保持测试用例（在 test_tree_sitter_chunking.py）
- [x] 6.4 编写降级回退测试用例（在 test_tree_sitter_chunking.py 中有集成测试）
- [x] 6.5 运行现有测试确保无回归（53 passed, 5 skipped）

## 7. 文档和清理

- [x] 7.1 更新 `docs/architecture.md` 中的分块策略说明
- [x] 7.2 添加 tree-sitter 分块的使用说明（在 architecture.md 中）
- [x] 7.3 保留旧的正则分块代码作为备选降级方案
- [x] 7.4 验证整体功能正常（测试全部通过）
