## 1. 定义输出格式枚举

- [x] 1.1 在 `cli.py` 中添加 `OutputFormat` 枚举

## 2. 创建渲染函数

- [x] 2.1 实现 `render_search_results_json()` 函数
- [x] 2.2 实现 `render_search_results_markdown()` 函数
- [x] 2.3 实现 `render_search_results_text()` 函数

## 3. 修改 CLI 命令

- [x] 3.1 为 `search` 命令添加 `--output` 参数
- [x] 3.2 修改 `_search_async` 支持 output 参数
- [x] 3.3 根据 output 参数选择渲染函数

## 4. 测试验证

- [x] 4.1 测试 JSON 输出格式正确性（单元测试通过）
- [x] 4.2 测试 Markdown 输出格式正确性（单元测试通过）
- [x] 4.3 测试 Text 输出格式（向后兼容，单元测试通过）
- [x] 4.4 Typer 自动验证格式参数
- [x] 4.5 运行现有测试确保无回归（134 passed）
