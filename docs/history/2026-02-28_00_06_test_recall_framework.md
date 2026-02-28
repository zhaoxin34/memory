# 测试框架 - 向量检索召回准确性验证

## 变更类型

test

## 变更描述

创建了测试框架来验证向量检索系统的召回准确性。

## 详细变更

1. **创建测试文档目录** `test_docs/`，包含 8 个不同主题的 Markdown 文档：
   - `python-async-programming.md` - Python 异步编程
   - `python-type-hints.md` - Python 类型提示
   - `javascript-es6-features.md` - JavaScript ES6 新特性
   - `cooking-hongshaorou.md` - 红烧肉烹饪
   - `fitness-strength-training.md` - 力量训练
   - `reading-notes-design-patterns.md` - 设计模式笔记
   - `travel-japan-guide.md` - 日本旅行攻略
   - `finance-stock-basics.md` - 股票投资基础

2. **创建集成测试文件** `tests/integration/test_recall.py`：
   - 7 个参数化测试用例验证不同主题的召回准确性
   - 1 个主题区分测试验证跨主题检索能力
   - 支持 pytest 和独立脚本两种运行方式

3. **创建测试仓库** `test-recall` 并导入所有测试文档

4. **测试结果**：所有 8 个测试用例均通过，验证了向量检索系统在不同主题间的区分能力良好

## 相关文件

- `test_docs/` - 测试文档目录
- `tests/integration/test_recall.py` - 集成测试文件

## 作者

zhaoxin
