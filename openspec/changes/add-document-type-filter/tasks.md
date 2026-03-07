## 1. 数据模型修改

- [x] 1.1 修改 Repository 实体，增加 `document_types: list[str]` 字段
- [x] 1.2 更新 SQLite 数据库迁移，添加 document_types 列

## 2. CLI 命令修改

- [x] 2.1 修改 `repo create` 命令，增加 `--document-types` 选项
- [x] 2.2 修改 `repo list` 命令，显示文档类型列

## 3. Sync 逻辑修改

- [x] 3.1 修改 sync 命令，根据仓库的 document_types 过滤文件

## 4. 测试与文档

- [x] 4.1 更新单元测试
- [x] 4.2 更新 README.md 文档
- [x] 4.3 更新 CLAUDE.md 文档
- [x] 4.4 更新.claude/skills/my-memory 的skills
