## Context

当前仓库创建时不支持文档类型过滤，用户无法指定只导入特定类型的文件。所有文件都会被扫描和导入，导致不必要的处理。

## Goals / Non-Goals

**Goals:**
- 在仓库创建时支持指定文档类型过滤
- 默认只导入 `.md` 文件
- sync 命令根据配置的文档类型自动过滤文件

**Non-Goals:**
- 不修改现有的文档类型检测逻辑（.md, .txt, .json 等）
- 不支持正则表达式，使用简单的文件扩展名匹配

## Decisions

### 1. 数据模型
- Repository 新增 `document_types: list[str]` 字段
- 使用 `list[str]` 而非单个字符串，支持多类型如 `["md", "json"]`

### 2. 默认值
- 如果未指定 `document_types`，默认为 `["md"]`

### 3. 文件匹配逻辑
- 使用 `path.suffix` 获取文件扩展名
- 匹配时不区分大小写（`.MD` 等同于 `.md`）

## Risks / Trade-offs

- [风险] 现有仓库没有 document_types 配置 → 兼容处理：默认使用 `["md"]`
- [风险] 用户可能混淆文件扩展名和 MIME 类型 → 文档中明确说明使用扩展名
