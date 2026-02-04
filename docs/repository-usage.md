# 仓库使用指南

本文档介绍如何使用 Memory 系统的仓库功能来组织和隔离不同项目或主题的文档。

## 什么是仓库？

仓库（Repository）是 Memory 系统中用于组织和隔离文档集合的逻辑单元。每个仓库：

- 有唯一的名称（kebab-case 格式，如 `my-project`）
- 包含独立的文档、分块和嵌入
- 使用独立的向量集合进行存储
- 可以独立搜索和查询
- 可以整体删除（包括所有相关数据）

## 为什么使用仓库？

使用仓库可以：

1. **项目隔离**: 不同项目的文档不会混在一起
2. **主题分类**: 按主题组织知识（如工作、学习、个人）
3. **精确搜索**: 在特定范围内搜索，避免无关结果
4. **批量管理**: 可以一次性删除整个项目的所有数据
5. **性能优化**: 搜索只在目标仓库的向量集合中进行

## 基本操作

### 1. 创建仓库

```bash
# 创建一个新仓库
memory repo create my-project

# 创建带描述的仓库
memory repo create work-docs --description "工作相关文档"
```

仓库名称规则：
- 只能包含小写字母、数字和连字符
- 必须是 kebab-case 格式（如 `my-project-2024`）
- 不能为空

### 2. 查看仓库

```bash
# 列出所有仓库
memory repo list

# 查看特定仓库的信息
memory repo info my-project
```

### 3. 导入文档到仓库

```bash
# 导入单个文件
memory ingest document.md --repository my-project

# 递归导入目录
memory ingest /path/to/docs --repository my-project --recursive

# 使用默认仓库（不指定 --repository）
memory ingest document.md
```

### 4. 在仓库中搜索

```bash
# 在特定仓库中搜索
memory search "查询内容" --repository my-project

# 在默认仓库中搜索
memory search "查询内容"

# 指定返回结果数量
memory search "查询内容" --repository my-project --top-k 5
```

### 5. 在仓库中提问

```bash
# 在特定仓库中提问
memory ask "这个项目的主要功能是什么？" --repository my-project

# 在默认仓库中提问
memory ask "文档的主要内容是什么？"
```

### 6. 删除仓库

```bash
# 删除仓库（会提示确认）
memory repo delete my-project

# 强制删除（跳过确认）
memory repo delete my-project --force
```

**警告**: 删除仓库会永久删除该仓库中的所有文档、分块和嵌入，此操作不可恢复！

## 默认仓库

系统会自动创建一个名为 `default` 的默认仓库。当你不指定 `--repository` 选项时，所有操作都会使用默认仓库。

### 配置默认仓库

在 `config.toml` 中设置：

```toml
default_repository = "my-main-repo"
```

或使用环境变量：

```bash
export MEMORY_DEFAULT_REPOSITORY="my-main-repo"
```

## 使用场景示例

### 场景 1: 多项目管理

```bash
# 创建不同项目的仓库
memory repo create project-alpha --description "Alpha 项目文档"
memory repo create project-beta --description "Beta 项目文档"

# 导入各自的文档
memory ingest /projects/alpha/docs --repository project-alpha --recursive
memory ingest /projects/beta/docs --repository project-beta --recursive

# 在特定项目中搜索
memory search "API 接口" --repository project-alpha
memory search "数据库设计" --repository project-beta
```

### 场景 2: 知识分类

```bash
# 按主题创建仓库
memory repo create work --description "工作相关"
memory repo create study --description "学习笔记"
memory repo create personal --description "个人文档"

# 导入不同类型的文档
memory ingest ~/Documents/work --repository work --recursive
memory ingest ~/Documents/study --repository study --recursive
memory ingest ~/Documents/personal --repository personal --recursive

# 在特定领域搜索
memory ask "如何优化数据库查询？" --repository work
memory ask "Python 装饰器的原理是什么？" --repository study
```

### 场景 3: 临时项目

```bash
# 创建临时项目仓库
memory repo create temp-research --description "临时研究项目"

# 导入文档并工作
memory ingest research-papers/ --repository temp-research --recursive
memory search "相关研究" --repository temp-research

# 项目结束后清理
memory repo delete temp-research --force
```

## 最佳实践

1. **命名规范**: 使用有意义的仓库名称，如 `project-name` 而不是 `repo1`
2. **添加描述**: 创建仓库时添加描述，方便日后识别
3. **定期清理**: 删除不再需要的仓库，释放存储空间
4. **默认仓库**: 为常用仓库设置为默认，减少命令行参数
5. **备份重要数据**: 删除仓库前确保已备份重要文档

## 技术细节

### 向量集合命名

每个仓库在向量存储中使用独立的集合，命名格式为：

```
{collection_name}_{repository_name}
```

例如，仓库 `my-project` 的向量集合名称为 `memory_my-project`。

### 数据隔离

- **物理隔离**: 不同仓库的向量存储在不同的集合中
- **逻辑隔离**: 文档和分块通过 `repository_id` 字段关联
- **级联删除**: 删除仓库时，会自动删除所有相关的文档、分块和嵌入

### 性能考虑

- 搜索只在目标仓库的向量集合中进行，速度更快
- 仓库数量不影响单个仓库的搜索性能
- 建议根据实际需求合理划分仓库，避免过度细分

## 故障排除

### 问题：无法创建仓库

**原因**: 仓库名称不符合 kebab-case 格式

**解决**: 使用小写字母、数字和连字符，如 `my-project-2024`

### 问题：导入文档时提示 repository_id 缺失

**原因**: 未指定仓库且默认仓库不存在

**解决**:
1. 指定 `--repository` 选项
2. 或在配置文件中设置 `default_repository`
3. 或创建名为 `default` 的仓库

### 问题：搜索结果为空

**原因**: 可能在错误的仓库中搜索

**解决**:
1. 使用 `memory repo list` 查看所有仓库
2. 确认文档导入到了正确的仓库
3. 使用正确的 `--repository` 参数

## 相关文档

- [README.md](../README.md) - 系统概述和快速开始
- [CLAUDE.md](../CLAUDE.md) - 架构和开发指南
- [config.toml](../config.toml) - 配置示例
